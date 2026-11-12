# Evaluation kernel for nervo-kaggle, rendered by scripts/render_kernel.py.
# Runs on Kaggle (4x L4, internet off): installs the official wheelhouse,
# writes our submission folder, serves the model with vLLM and runs the
# official Evaluator (phase 1 agent + phase 2 hidden-test verification)
# on a fixed sample of the public tasks.
import asyncio
import base64
import concurrent.futures
import glob
import importlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

SUBMISSION_PAYLOAD_B64 = "__SUBMISSION_PAYLOAD_B64__"
N_TASKS = int("__N_TASKS__")
BANCO = "__BANCO__" == "1"


def preparar_banco():
    """Validation bench: copy tasks.jsonl and snapshots/ to /kaggle/working/banco (unzips if Kaggle left them zipped)."""
    import shutil, zipfile
    srcs = [Path(p).parent for p in glob.glob('/kaggle/input/**/tasks.jsonl', recursive=True) if 'banco' in p]
    assert srcs, 'dataset nervo-banco-nuevo (validation bench) not found in /kaggle/input'
    src, dst = srcs[0], Path('/kaggle/working/banco')
    (dst / 'snapshots').mkdir(parents=True, exist_ok=True)
    shutil.copy(src / 'tasks.jsonl', dst / 'tasks.jsonl')
    for z in list(src.rglob('*.zip')):
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if m.endswith('.tgz'):
                    (dst / 'snapshots' / Path(m).name).write_bytes(zf.read(m))
    for t in src.rglob('*.tgz'):
        shutil.copy(t, dst / 'snapshots' / t.name)
    print('bench:', src, '->', dst, len(list((dst / 'snapshots').glob('*.tgz'))), 'snapshots')
    return dst
RUN_LABEL = "__RUN_LABEL__"
ORACLE = "__ORACLE__" == "1"
TASK_IDS = [x for x in "__TASK_IDS__".split(",") if x]
DIAG = "__DIAG__" == "1"
LAB_PROBES_B64 = "__LAB_PROBES_B64__"
BATERIA_B64 = "__BATERIA_B64__"
MOTOR_B64 = "__MOTOR_B64__"
_tiene = lambda v: bool(v) and not v.startswith("__")
LAB = _tiene(LAB_PROBES_B64) or _tiene(BATERIA_B64)

os.environ.update({
    'TRANSFORMERS_NO_TF': '1', 'TRANSFORMERS_NO_FLAX': '1', 'TRANSFORMERS_OFFLINE': '1',
    'VLLM_NO_USAGE_STATS': '1', 'VLLM_WORKER_MULTIPROC_METHOD': 'spawn',
    'VLLM_ENGINE_READY_TIMEOUT_S': '1200', 'VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS': '1',
    'NCCL_DEBUG': 'WARN', 'LITELLM_LOCAL_MODEL_COST_MAP': 'True', 'LITELLM_TELEMETRY': 'False',
    'LITELLM_LOG': 'WARNING', 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True',
    'OTEL_SDK_DISABLED': 'true', 'OTEL_PYTHON_DISABLED': 'true',
})
os.environ.setdefault('OPENAI_API_KEY', 'EMPTY')
os.environ.setdefault('LOCAL_API_KEY', 'EMPTY')

# NERVO_API_BASE: local mode to test THIS kernel without a GPU against local/shim_vllm.py
API_BASE = os.environ.get('NERVO_API_BASE', '')
WORKING_DIR = Path(os.environ.get('NERVO_WORKDIR', '/kaggle/working'))
WORKING_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = WORKING_DIR / 'nervo_results.json'
state = {'label': RUN_LABEL, 'stage': 'start', 'tasks': [], 'error': None}


def save_state() -> None:
    RESULTS_PATH.write_text(json.dumps(state, indent=2, default=str))


def log(msg: str) -> None:
    print(f'[nervo] {msg}', flush=True)


def quiet_loggers() -> None:
    for name in ('LiteLLM', 'LiteLLM Router', 'LiteLLM Proxy', 'litellm', 'httpx', 'httpcore',
                 'openai', 'urllib3', 'opentelemetry', 'opentelemetry.context'):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        if 'litellm' in name.lower():
            lg.propagate = False
            lg.handlers.clear()


def install_wheelhouse() -> None:
    wheelhouse = Path('/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse')
    if not wheelhouse.exists():
        cands = [Path(p) for p in glob.glob('/kaggle/input/**/gemma-4-developer-agent-wheelhouse', recursive=True)]
        wheelhouse = cands[0] if cands else wheelhouse
    for pattern in ('/usr/local/lib/python*/dist-packages/*cutlass*.pth',
                    '/usr/local/lib/python*/site-packages/*cutlass*.pth'):
        for pth in glob.glob(pattern):
            try:
                os.unlink(pth)
            except OSError:
                pass
    tmp = Path('/tmp/wheelhouse')
    tmp.mkdir(parents=True, exist_ok=True)
    for w in wheelhouse.glob('*.whl'):
        if 'cutlass' in w.name.lower():
            continue
        name = w.name.replace('cu128', '+cu128') if ('cu128' in w.name and '+' not in w.name) else w.name
        target = tmp / name
        if not target.exists():
            try:
                os.symlink(w, target)
            except OSError:
                shutil.copyfile(w, target)
    wheels = sorted(str(w) for w in tmp.glob('*.whl'))
    log(f'installing {len(wheels)} wheels from {wheelhouse}')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall', *wheels], check=True)
    importlib.invalidate_caches()


def load_bundle() -> dict:
    """{variant_name: {path: content}}. Also accepts the old format (a single variant)."""
    data = json.loads(base64.b64decode(SUBMISSION_PAYLOAD_B64).decode('utf-8'))
    if data and all(isinstance(v, str) for v in data.values()):
        data = {'submission': data}
    return data


def write_submission(name: str, files: dict) -> Path:
    agent_dir = WORKING_DIR / 'subs' / name
    shutil.rmtree(agent_dir, ignore_errors=True)
    for rel, content in files.items():
        p = agent_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
    log(f'submission {name} written: {sorted(files)}')
    return agent_dir


def pick_tasks(tasks, n):
    """Fixed, repo-balanced sample so runs of different versions are comparable."""
    if TASK_IDS:
        by_id = {t.instance_id: t for t in tasks}
        return [by_id[i] for i in TASK_IDS if i in by_id]
    by_repo = {}
    for t in sorted(tasks, key=lambda t: t.instance_id):
        by_repo.setdefault(t.repo, []).append(t)
    picked, i = [], 0
    while len(picked) < min(n, len(tasks)):
        for repo in sorted(by_repo):
            lst = by_repo[repo]
            if i < len(lst) and len(picked) < n:
                # spread picks across the repo's list instead of taking the first ones
                idx = (i * 7) % len(lst)
                cand = lst[idx]
                if cand not in picked:
                    picked.append(cand)
        i += 1
        if i > 200:
            break
    return picked


def run_sync(fn, *args, **kwargs):
    def runner():
        return asyncio.run(fn(*args, **kwargs))
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(runner).result()
    return runner()


def dump_obj(o, limit=6000):
    """Serialize the whole Evaluator result (to see the pytest output)."""
    try:
        d = o.model_dump() if hasattr(o, 'model_dump') else dict(vars(o))
    except Exception:
        d = {k: getattr(o, k) for k in dir(o) if not k.startswith('_') and not callable(getattr(o, k, None))}
    out = {}
    for k, v in d.items():
        v = v if isinstance(v, (int, float, bool, type(None))) else str(v)
        out[k] = v[-limit:] if isinstance(v, str) else v
    return out


def oracle_verify(task, evaluator, patch=None):
    """Score the task's OFFICIAL patch with the harness verification.
    If it does not come out resolved, the local evaluation is broken, not the agent."""
    import inspect
    from swegemma.evaluate import verify_task
    from swegemma.deduplication import resolve_task_snapshot_paths

    async def call():
        t = evaluator._hydrate_task_from_secret(task)
        sp, bsp, pp = resolve_task_snapshot_paths(evaluator.config.snapshots_dir, t.instance_id, t.repo)
        kw = {'agent_patch': t.patch if patch is None else patch}
        params = inspect.signature(verify_task).parameters
        if 'base_snapshot_path' in params:
            kw.update(base_snapshot_path=bsp, patch_path=pp)
        if 'start_time' in params:
            kw['start_time'] = time.perf_counter()
        return await verify_task(evaluator.docker, evaluator.config, t, sp, **kw)
    return dump_obj(run_sync(call))


def patch_sandbox_src_layout() -> None:
    """In Docker the repository is installed editable; in Kaggle's subprocess sandbox that fails
    (no ensurepip) and repositories with a src/ layout (requests, httpx) import the system
    version. A .pth file in the sandbox venv puts /workspace/src first, like the editable
    install of the official evaluation."""
    from swegemma.sandbox import subprocess as sbx
    patched = []
    for name in dir(sbx):
        cls = getattr(sbx, name)
        if not (isinstance(cls, type) and hasattr(cls, 'start') and hasattr(cls, 'sandboxes')):
            continue

        def add_pth(self, sid):
            try:
                paths = self.sandboxes[sid]
                ws = paths.get('workspace') or next(v for v in paths.values() if Path(v).name == 'workspace')
                src = str(Path(ws) / 'src')
                line = f"import sys, os; p={src!r}; os.path.isdir(p) and p not in sys.path and sys.path.insert(0, p)\n"
                for sp in Path(paths['venv']).glob('lib/python*/site-packages'):
                    (sp / 'zz_nervo_src.pth').write_text(line)
            except Exception as e:
                log(f'patch_sandbox: could not write the .pth: {type(e).__name__}: {e}')

        orig_start = cls.start

        def start(self, *a, _orig=orig_start, **k):
            sid = _orig(self, *a, **k)
            add_pth(self, sid)
            return sid
        cls.start = start
        if hasattr(cls, 'start_async'):
            orig_async = cls.start_async

            async def start_async(self, *a, _orig=orig_async, **k):
                sid = await _orig(self, *a, **k)
                add_pth(self, sid)
                return sid
            cls.start_async = start_async
        patched.append(name)
    log(f'patch_sandbox_src_layout applied to {patched}')

def diagnose() -> None:
    """No GPU: dump how the sandbox prepares the Python environment and how verification runs."""
    import inspect
    out = {}
    out['python'] = sys.executable
    r = subprocess.run([sys.executable, '-m', 'ensurepip', '--version'], capture_output=True, text=True)
    out['ensurepip'] = (r.returncode, r.stdout[-500:], r.stderr[-1500:])
    r = subprocess.run(['bash', '-lc', 'ls /usr/share/python-wheels 2>&1; ls /usr/lib/python3*/ensurepip/_bundled 2>&1; which pip pip3 virtualenv uv 2>&1; python3 -c "import pip,sys;print(pip.__version__,pip.__file__)"'],
                       capture_output=True, text=True)
    out['env'] = r.stdout[-2000:] + r.stderr[-500:]
    for modname in ('swegemma.sandbox.subprocess', 'swegemma.container_setup', 'swegemma.harness.container_setup',
                    'swegemma.evaluate'):
        try:
            mod = importlib.import_module(modname)
            src = inspect.getsource(mod)
            keep = [l for l in src.splitlines() if re.search(r'venv|ensurepip|pip|site.packages|PYTHONPATH|editable|def |snapshot', l)]
            out[modname] = '\n'.join(keep)[:12000]
        except Exception as e:
            out[modname] = f'ERR {type(e).__name__}: {e}'
    try:
        from swegemma.evaluate import Evaluator
        out['evaluate_task_src'] = inspect.getsource(Evaluator.evaluate_task)[:8000]
    except Exception as e:
        out['evaluate_task_src'] = f'ERR {e}'
    state['diag'] = out
    save_state()
    log('DIAG done')

def lab_call(base, model_id, probe):
    """One raw single call to the vLLM server (OpenAI API). Returns the response as is."""
    import urllib.request
    body = {'model': model_id, 'messages': probe['messages'],
            'temperature': probe.get('temperature', 0.2), 'top_p': 0.95,
            'max_tokens': probe.get('max_tokens', 2048)}
    if probe.get('tools'):
        body['tools'] = probe['tools']
        body['tool_choice'] = probe.get('tool_choice', 'auto')
    body.update(probe.get('extra', {}))
    if 'chat_template_kwargs' in probe:
        body['chat_template_kwargs'] = probe['chat_template_kwargs']
    req = urllib.request.Request(f'{base}/v1/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer EMPTY'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.loads(r.read())
    msg = out['choices'][0]['message']
    return {'seconds': round(time.time() - t0, 2), 'finish_reason': out['choices'][0].get('finish_reason'),
            'content': msg.get('content'), 'reasoning': msg.get('reasoning_content') or msg.get('reasoning'),
            'tool_calls': [{'name': c['function']['name'], 'arguments': c['function']['arguments']}
                           for c in (msg.get('tool_calls') or [])],
            'usage': out.get('usage')}


def run_lab(base='http://127.0.0.1:8000'):
    import urllib.request
    probes = json.loads(base64.b64decode(LAB_PROBES_B64).decode('utf-8')) if _tiene(LAB_PROBES_B64) else []
    with urllib.request.urlopen(f'{base}/v1/models', timeout=60) as r:
        model_id = json.loads(r.read())['data'][0]['id']
    log(f'LAB: served model = {model_id}, {len(probes)} probes')
    state['lab'] = {'model_id': model_id, 'results': []}
    for probe in probes:
        for rep in range(probe.get('repeat', 1)):
            try:
                res = lab_call(base, model_id, probe)
            except Exception as e:
                res = {'error': f'{type(e).__name__}: {e}'}
            res.update(id=probe['id'], rep=rep)
            state['lab']['results'].append(res)
            log(f"LAB {probe['id']}#{rep}: tool_calls={[c['name'] for c in res.get('tool_calls', [])]} "
                f"content={str(res.get('content'))[:120]!r} err={res.get('error')}")
            save_state()

CAPTURA = {}


def capturar_llamadas_harness(evaluator, task):
    """Run ONE task with the official harness and capture the exact parameters ADK uses to call
    the model (LiteLLMClient.acompletion), so the lab calls the model exactly as the competition does."""
    import copy
    import google.adk.models.lite_llm as ll
    orig = ll.LiteLLMClient.acompletion

    async def espia(self, *a, **kw):
        if not CAPTURA:
            limpio = {k: v for k, v in kw.items() if k not in ('messages', 'tools')}
            CAPTURA['kwargs'] = copy.deepcopy(limpio)
            CAPTURA['tools'] = copy.deepcopy(kw.get('tools'))
            CAPTURA['example_messages'] = [
                {k: (str(v)[:800] if k == 'content' else v) for k, v in m.items()} if isinstance(m, dict) else str(m)[:800]
                for m in (kw.get('messages') or [])[:3]]
        return await orig(self, *a, **kw)
    ll.LiteLLMClient.acompletion = espia
    try:
        r = run_sync(lambda: evaluator.evaluate_task(task))
        CAPTURA['task'] = task.instance_id
        CAPTURA['resolved'] = getattr(r, 'resolved', None)
        CAPTURA['patch_chars'] = len(getattr(r, 'agent_patch', '') or '')
    finally:
        ll.LiteLLMClient.acompletion = orig
    log(f"CAPTURE kwargs={ {k: v for k, v in CAPTURA.get('kwargs', {}).items() if k not in ('api_key',)} } resolved={CAPTURA.get('resolved')}")
    return CAPTURA


def hacer_modelo_replay(motor):
    """Lab model that calls through litellm with the SAME kwargs the harness used."""
    import litellm

    class ModeloReplay(motor.Modelo):
        def chat(self, messages, tools=None, tool_choice='auto', max_tokens=4096, temperature=0.2):
            kw = {k: v for k, v in CAPTURA['kwargs'].items() if k not in ('stream', 'stream_options')}
            kw['messages'] = messages
            if tools:
                kw['tools'] = tools
                kw['tool_choice'] = tool_choice
            t0 = time.time()
            try:
                out = litellm.completion(**kw)
            except Exception as e:
                return {'error': f'{type(e).__name__}: {e}', 'seconds': round(time.time() - t0, 2),
                        'content': None, 'tool_calls': [], 'reasoning': None}
            msg = out.choices[0].message
            calls = []
            for i, c in enumerate(getattr(msg, 'tool_calls', None) or []):
                raw = c.function.arguments or '{}'
                try:
                    args = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    args = {'_raw': raw}
                calls.append({'id': getattr(c, 'id', None) or f'call_{i}', 'name': c.function.name, 'args': args, 'raw': raw})
            return {'seconds': round(time.time() - t0, 2), 'finish': out.choices[0].finish_reason,
                    'content': msg.content, 'reasoning': getattr(msg, 'reasoning_content', None),
                    'tool_calls': calls, 'usage': None}
    return ModeloReplay


def args_intactos(resp):
    """Self-test: do the edit_file arguments arrive with their keys and the full regex?"""
    c = next((c for c in resp.get('tool_calls', []) if c['name'] == 'edit_file'), None)
    if not c or not isinstance(c['args'], dict):
        return False
    return set(c['args']) == {'filepath', 'old_string', 'new_string'} and ';:&' in c['args'].get('old_string', '')

def run_bateria(evaluator, tasks, base='http://127.0.0.1:8000'):
    """Battery of approaches (lab/motor.py, not included in this repository) on real repositories + scoring with hidden tests."""
    import urllib.request
    cfg = json.loads(base64.b64decode(BATERIA_B64).decode('utf-8'))
    motor_path = WORKING_DIR / 'lab_motor.py'
    motor_path.write_text(base64.b64decode(MOTOR_B64).decode('utf-8'))
    sys.path.insert(0, str(WORKING_DIR))
    import lab_motor as motor
    from swegemma.deduplication import resolve_task_snapshot_paths
    with urllib.request.urlopen(f'{base}/v1/models', timeout=60) as r:
        model_id = json.loads(r.read())['data'][0]['id']
    by_id = {t.instance_id: t for t in tasks}
    state['battery'] = {'config': cfg, 'results': []}

    # 1) capture how the official harness calls the model (one real task)
    state['stage'] = 'bateria_captura'; save_state()
    try:
        capturar_llamadas_harness(evaluator, by_id[cfg.get('capture_task', cfg['tasks'][0])])
    except Exception as e:
        CAPTURA['error'] = f'{type(e).__name__}: {e}'
        CAPTURA['trace'] = traceback.format_exc()[-2000:]
        log(f'CAPTURE failed: {CAPTURA["error"]}')
    state['battery']['capture'] = {k: (v if k != 'kwargs' else {kk: vv for kk, vv in v.items() if kk != 'api_key'})
                                   for k, v in CAPTURA.items()}
    save_state()

    # 2) self-test: the same probe with a raw call and with the harness call; use the one that arrives intact
    sonda = cfg.get('selftest_probe')
    modelos = {'raw_call': motor.Modelo(base, model_id)}
    if CAPTURA.get('kwargs'):
        modelos['harness'] = hacer_modelo_replay(motor)(base, model_id)
    auto = {}
    for nombre, mdl in modelos.items():
        oks = []
        for _ in range(3):
            resp = mdl.chat(sonda['messages'], tools=sonda['tools']) if sonda else {}
            oks.append(args_intactos(resp))
            auto.setdefault(nombre + '_ejemplo', [c['args'] for c in resp.get('tool_calls', [])][:1] or resp.get('error'))
        auto[nombre] = oks
    elegido = 'harness' if all(auto.get('harness') or [False]) else ('raw_call' if all(auto.get('raw_call') or [False]) else
              ('harness' if 'harness' in modelos else 'raw_call'))
    auto['chosen'] = elegido
    state['battery']['selftest'] = auto
    log(f'SELFTEST {auto}')
    save_state()
    modelo = modelos[elegido]

    tareas = []
    for tid in cfg['tasks']:
        t = evaluator._hydrate_task_from_secret(by_id[tid])
        sp, bsp, pp = resolve_task_snapshot_paths(evaluator.config.snapshots_dir, t.instance_id, t.repo)
        tareas.append({'id': tid, 'problem_statement': t.problem_statement, 'snapshot': sp if Path(sp).exists() else None,
                       'base': bsp, 'parche': pp})
        log(f'BATTERY task {tid}: snapshot={sp} exists={Path(sp).exists()} base={bsp} patch={pp}')

    def guardar(res):
        state['battery']['results'] = res
        save_state()

    res = motor.ejecutar_bateria(modelo, tareas, cfg['strategies'], cfg['ctx'],
                                 Path('/tmp/lab_trabajo'), paralelo=cfg.get('parallel', 8),
                                 deadline_s=cfg.get('deadline_s', 480), max_llamadas=cfg.get('max_calls', 30),
                                 log=log, guardar=guardar)
    state['stage'] = 'bateria_verificar'; save_state()
    for fila in res:
        if not fila.get('patch', '').strip():
            fila['resolved'] = False
            continue
        try:
            v = oracle_verify(by_id[fila['task']], evaluator, patch=fila['patch'])
            fila['resolved'] = v.get('resolved')
            fila['test_exit_code'] = v.get('test_exit_code')
            fila['test_output'] = str(v.get('test_output', ''))[-1200:]
        except Exception as e:
            fila['resolved'] = None
            fila['verify_error'] = f'{type(e).__name__}: {e}'
        log(f"VERIFIED {fila['strategy']:18} {fila['task']:16} resolved={fila.get('resolved')}")
        guardar(res)
    resumen = {}
    for fila in res:
        r = resumen.setdefault(fila['strategy'], {'solved_count': 0, 'with_patch': 0, 'total': 0})
        r['total'] += 1
        r['with_patch'] += bool(fila.get('patch', '').strip())
        r['solved_count'] += bool(fila.get('resolved'))
    state['battery']['summary_by_strategy'] = resumen
    log(f'BATTERY summary: {resumen}')
    save_state()

def make_eval_config(agent_dir, data_dir, models, limits, gen_constraints, adapters, results_dir):
    import yaml
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from swegemma.config import EvalConfig
    ev_file = agent_dir / 'eval_config.yaml'
    ev = yaml.safe_load(ev_file.read_text()) if ev_file.is_file() else {}
    ev = (ev or {}).get('evaluation', ev or {})
    if os.environ.get('NERVO_MINUTOS'):  # local mode ONLY: the external API is slower than vLLM
        ev['max_time_minutes'] = float(os.environ['NERVO_MINUTOS'])
    turns = ev.get('max_turns', ev.get('max_llm_calls'))
    return EvalConfig(
        tasks_path=data_dir / 'tasks.jsonl', snapshots_dir=data_dir / 'snapshots',
        results_dir=results_dir, submission_dir=agent_dir, models=models if models is not None else {},
        sandbox='subprocess',
        timeout_seconds=int(ev.get('timeout_seconds', 300)),
        verification_timeout_seconds=int(ev.get('verification_timeout_seconds', 300)),
        max_time_minutes=float(ev.get('max_time_minutes', 60.0)),
        max_tool_calls=int(ev.get('max_tool_calls', 100)),
        max_turns=int(turns) if turns is not None else None,
        limits=limits, generation_constraints=gen_constraints, adapter_manifest=adapters,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                        token_threshold=14336, event_retention_size=5),
        graph_dir=str(data_dir / 'graphs'), embeddings_dir=str(data_dir / 'embeddings'),
        wheels_dir=data_dir / 'wheels', verbose=False,
    ), ev


def main() -> None:
    quiet_loggers()
    if not API_BASE and not os.environ.get('NERVO_SKIP_WHEELHOUSE'):  # Modal: the environment is already installed
        state['stage'] = 'wheelhouse'; save_state()
        install_wheelhouse()
        quiet_loggers()
    patch_sandbox_src_layout()
    if DIAG:
        diagnose()
        state['stage'] = 'done'; save_state()
        return

    import litellm
    from adk_submission import discover_adapters
    from adk_submission.discovery import discover_declared_models
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, build_submission_limits
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks
    litellm.drop_params = True

    data_dir = Path(os.environ.get('NERVO_DATA', '/kaggle/input/competitions/gemma-4-developer-agent'))
    if BANCO:
        data_dir = preparar_banco()
    elif not data_dir.exists():
        cands = [Path(p) for p in glob.glob('/kaggle/input/**/tasks.jsonl', recursive=True)]
        data_dir = cands[0].parent if cands else data_dir

    bundle = load_bundle()
    state['variants'] = list(bundle)
    state['stage'] = 'validate'; save_state()
    from adk_submission import validate_directory
    limits, gen_constraints = build_submission_limits()
    agent_dirs = {}
    for name, files in bundle.items():
        agent_dirs[name] = write_submission(name, files)
        validate_directory(agent_dirs[name], limits=limits)
    declared = set()
    for d in agent_dirs.values():
        declared |= set(discover_declared_models(d))
    assert len(declared) == 1, f'expected one model across variants, got {sorted(declared)}'
    model_name = next(iter(declared))
    first_dir = next(iter(agent_dirs.values()))
    adapters = discover_adapters(str(first_dir), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    adapter_map = getattr(adapters, 'adapters', None) or {}

    need_model = not (ORACLE and N_TASKS == 0)
    state['stage'] = 'vllm'; save_state()
    t0 = time.time()
    server = None
    models = None
    if need_model and API_BASE:
        from adk_submission.registry import ModelRegistry
        from adk_submission.resolvers.generation import install_litellm_reasoning_patch
        from google.adk.models.lite_llm import LiteLlm
        install_litellm_reasoning_patch()
        models = ModelRegistry()
        models.register(model_name, LiteLlm(model=f'openai/{model_name}', api_base=API_BASE, api_key='EMPTY'))
        log(f'local mode: model {model_name} at {API_BASE}')
    elif need_model:
        import torch
        from adk_submission import VllmConfig, VllmServer
        model_path = (Path(os.environ['NERVO_MODEL_DIR']) / model_name if os.environ.get('NERVO_MODEL_DIR')
                      else Path(f'/kaggle/input/models/google/gemma-4/other/{model_name}/2'))
        if not model_path.exists():
            cands = [Path(p) for p in glob.glob(f'/kaggle/input/**/{model_name}/*', recursive=True) if Path(p).is_dir()]
            model_path = cands[0] if cands else model_path
        assert model_path.exists(), f'model weights not found for {model_name}'
        log(f'model {model_name} at {model_path}')
        ranks = [r for info in adapter_map.values() if (r := getattr(info, 'rank', None))]
        gpus = torch.cuda.device_count() if torch.cuda.is_available() else 1
        tp = 4 if gpus >= 4 else (2 if gpus >= 2 else 1)
        extra = ()
        if model_name == 'gemma-4-12b-it-qat-w4a16-ct':
            extra = ('--hf-overrides', '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}')
        cfg = VllmConfig(
            model=str(model_path), port=8000, host='127.0.0.1',
            tool_call_parser='gemma4', reasoning_parser='gemma4', max_model_len=32768,
            dtype='bfloat16' if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else 'auto',
            gpu_memory_utilization=0.90, enable_auto_tool_choice=True,
            enable_lora=bool(adapter_map), max_loras=max(1, len(adapter_map)),
            max_lora_rank=max(ranks) if ranks else 128, scheduler_reserve_full_isl=False,
            tensor_parallel_size=tp, startup_timeout=60 * 20, extra_args=extra,
        )
        server = VllmServer(cfg, adapter_manifest=adapters)
        server.start()
        models = server.create_model_registry(aliases=[model_name], model_prefix='openai/',
                                              api_key=os.environ.get('LOCAL_API_KEY', 'EMPTY'))
        state['vllm_start_seconds'] = round(time.time() - t0, 1)
        log(f'vLLM ready in {state["vllm_start_seconds"]}s (tp={tp}, gpus={gpus})')

    tasks = load_tasks(data_dir / 'tasks.jsonl')
    sample = pick_tasks(tasks, N_TASKS)
    state['n_public_tasks'] = len(tasks)
    state['sample'] = [t.instance_id for t in sample]

    evaluators = {}
    for name, agent_dir in agent_dirs.items():
        cfg_e, ev = make_eval_config(agent_dir, data_dir, models, limits, gen_constraints, adapters,
                                     WORKING_DIR / 'results' / name)
        evaluators[name] = Evaluator(cfg_e)
        state.setdefault('budgets', {})[name] = ev
    first_eval = next(iter(evaluators.values()))

    if LAB:
        state['stage'] = 'lab'; save_state()
        if _tiene(LAB_PROBES_B64):
            run_lab()
        if _tiene(BATERIA_B64):
            run_bateria(first_eval, tasks)
        if server is not None:
            server.stop()
        state['stage'] = 'done'; save_state()
        return
    if ORACLE:
        state['stage'] = 'oracle'; save_state()
        state['oracle'] = []
        oracle_tasks = tasks if (not TASK_IDS and N_TASKS == 0) else sample
        for task in oracle_tasks:
            try:
                res = oracle_verify(task, first_eval)
            except Exception as e:
                res = {'error': f'{type(e).__name__}: {e}', 'trace': traceback.format_exc()[-3000:]}
            res['id'] = task.instance_id
            res['repo'] = task.repo
            res['test_output'] = str(res.get('test_output', ''))[-1500:]
            state['oracle'].append(res)
            log(f'ORACLE {task.instance_id}: resolved={res.get("resolved")} error={res.get("error")}')
            save_state()

    state['stage'] = 'evaluate'; save_state()
    # Interleaved by task (task 1: A, B; task 2: A, B...) so that, if the kernel is cut off,
    # every variant has the same tasks done.
    for i, task in enumerate(sample if need_model else [], start=1):
        for name, evaluator in evaluators.items():
            rec = {'variant': name, 'id': task.instance_id, 'repo': task.repo}
            try:
                r = run_sync(evaluator.evaluate_task, task=task, task_index=i, total_tasks=len(sample))
                patch = (r.agent_patch or '').strip()
                rec.update(resolved=bool(r.resolved), patch_chars=len(patch), tool_calls=r.tool_calls,
                           duration_s=round(r.duration_seconds or 0, 1), exit_code=r.test_exit_code,
                           error=getattr(r, 'error', None), patch=patch[:4000], raw=dump_obj(r))
            except Exception as e:  # one broken task must not kill the run
                rec.update(resolved=False, error=f'{type(e).__name__}: {e}', trace=traceback.format_exc()[-3000:])
            state['tasks'].append(rec)
            hechas = [t for t in state['tasks'] if t['variant'] == name]
            log(f'[{i}/{len(sample)}] {name:16} {task.instance_id}: resolved={rec["resolved"]} '
                f'patch={rec.get("patch_chars")} calls={rec.get("tool_calls")} t={rec.get("duration_s")}s '
                f'-> {sum(t["resolved"] for t in hechas)}/{len(hechas)}')
            save_state()

    resumen = {}
    for t in state['tasks']:
        r = resumen.setdefault(t['variant'], {'resolved': 0, 'total': 0, 'with_patch': 0})
        r['total'] += 1
        r['resolved'] += bool(t['resolved'])
        r['with_patch'] += bool(t.get('patch_chars'))
    state['summary'] = resumen
    state['stage'] = 'done'; save_state()
    log(f'SUMMARY {resumen}')
    if server is not None:
        server.stop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        state['error'] = f'{type(e).__name__}: {e}'
        state['trace'] = traceback.format_exc()
        save_state()
        raise
