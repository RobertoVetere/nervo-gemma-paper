"""Run the OFFICIAL harness (swegemma Evaluator, subprocess or Docker sandbox) locally, with the
model served through local/shim_vllm.py (which poses as vLLM).

Same configuration as scripts/kernel_template.py (budgets, compaction, cache), so that what works
here behaves the same in the competition environment.

Usage:
  python local/shim_vllm.py --port 8000 --log /tmp/calls.jsonl &
  python local/run_local.py --oracle                                 # bench check: does the official fix pass?
  python local/run_local.py --variant variants/community_base        # run an agent
Data: --data points to a folder with tasks.jsonl and snapshots/<id>.tgz (see local/build_bench.py).
Output JSON keys are in Spanish (modelo = model, presupuesto = budget, tareas = tasks); see README, "Field names".
"""
import argparse
import asyncio
import inspect
import json
import re
import shutil
import sys
import time
from pathlib import Path

MODELO = 'gemma-4-31b-it-qat-w4a16-ct'  # only with --force-31b (AI Studio serves only the 31B)


def run_sync(fn, *a, **kw):
    return asyncio.run(fn(*a, **kw))


def dump_obj(o, limit=6000):
    try:
        d = o.model_dump() if hasattr(o, 'model_dump') else dict(vars(o))
    except Exception:
        d = {k: getattr(o, k) for k in dir(o) if not k.startswith('_') and not callable(getattr(o, k, None))}
    return {k: (v if isinstance(v, (int, float, bool, type(None))) else str(v)[-limit:]) for k, v in d.items()}


def preparar_submission(variant: Path, destino: Path, forzar: bool) -> Path:
    """Copy the variant. With forzar=True, set the model to the 31B in every YAML file (AI Studio only has the 31B).
    NOTE (10 Nov): until that day this was ALWAYS forced, so every earlier local "E4B" run used the 31B."""
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(variant, destino)
    if not forzar:
        return destino
    for y in list(destino.rglob('*.yaml')) + list(destino.rglob('*.yml')):
        txt = y.read_text()
        nuevo = re.sub(r'(?m)^(\s*model:\s*)gemma-4-[\w.-]+', rf'\g<1>{MODELO}', txt)
        if nuevo != txt:
            y.write_text(nuevo)
    return destino


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default='variants/community_base')
    ap.add_argument('--tasks', default='rich_3454')
    ap.add_argument('--data', default='bench')
    ap.add_argument('--work', default='work')
    ap.add_argument('--api-base', default='http://127.0.0.1:8000/v1')
    ap.add_argument('--oracle', action='store_true', help='only score the official fix (no model)')
    ap.add_argument('--force-31b', '--forzar-31b', dest='forzar_31b', action='store_true', help='replace the variant model with the 31B (AI Studio)')
    ap.add_argument('--sandbox', default='subprocess', choices=['subprocess', 'docker'],
                    help='docker = like the competition (image swebench-sandbox:latest, see local/docker/)')
    ap.add_argument('--out', default=None)
    ap.add_argument('--minutes', '--minutos', dest='minutos', type=float, default=None,
                    help='local only: raise max_time_minutes because AI Studio is much slower than vLLM')
    a = ap.parse_args()

    import litellm
    import yaml
    from adk_submission import validate_directory
    from adk_submission.discovery import discover_declared_models
    from adk_submission.registry import ModelRegistry
    from adk_submission.resolvers.generation import install_litellm_reasoning_patch
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from google.adk.models.lite_llm import LiteLlm
    from swegemma.config import EvalConfig, build_submission_limits
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks
    litellm.drop_params = True

    data = Path(a.data)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    agent_dir = preparar_submission(Path(a.variant).resolve(), work / 'submission', a.forzar_31b)
    limits, gen_constraints = build_submission_limits()
    validate_directory(agent_dir, limits=limits)
    declared = discover_declared_models(agent_dir)
    assert len(declared) == 1, f'modelos declarados: {declared}'
    modelo = next(iter(declared))
    print(f'variant model: {modelo}', flush=True)

    # Same as VllmServer.create_model_registry(aliases=[modelo], model_prefix='openai/')
    install_litellm_reasoning_patch()
    models = ModelRegistry()
    models.register(modelo, LiteLlm(model=f'openai/{modelo}', api_base=a.api_base, api_key='EMPTY'))

    ev_file = agent_dir / 'eval_config.yaml'
    ev = yaml.safe_load(ev_file.read_text()) if ev_file.is_file() else {}
    ev = (ev or {}).get('evaluation', ev or {})
    turns = ev.get('max_turns', ev.get('max_llm_calls'))
    if a.minutos:
        ev['max_time_minutes'] = a.minutos
    eval_config = EvalConfig(
        tasks_path=data / 'tasks.jsonl', snapshots_dir=data / 'snapshots',
        results_dir=work / 'results', submission_dir=agent_dir, models=models,
        sandbox=a.sandbox,
        timeout_seconds=int(ev.get('timeout_seconds', 300)),
        verification_timeout_seconds=int(ev.get('verification_timeout_seconds', 300)),
        max_time_minutes=float(ev.get('max_time_minutes', 60.0)),
        max_tool_calls=int(ev.get('max_tool_calls', 100)),
        max_turns=int(turns) if turns is not None else None,
        limits=limits, generation_constraints=gen_constraints, adapter_manifest=None,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                        token_threshold=14336, event_retention_size=5),
        graph_dir=str(data / 'graphs'), embeddings_dir=str(data / 'embeddings'),
        wheels_dir=data / 'wheels', verbose=False,
    )
    evaluator = Evaluator(eval_config)
    by_id = {t.instance_id: t for t in load_tasks(data / 'tasks.jsonl')}
    salida = {'variant': a.variant, 'modelo': modelo, 'presupuesto': ev, 'tareas': []}

    for tid in a.tasks.split(','):
        task = by_id[tid]
        t0 = time.time()
        rec = {'id': tid}
        try:
            if a.oracle:
                from swegemma.deduplication import resolve_task_snapshot_paths
                from swegemma.evaluate import verify_task

                async def call():
                    t = evaluator._hydrate_task_from_secret(task)
                    sp, bsp, pp = resolve_task_snapshot_paths(evaluator.config.snapshots_dir, t.instance_id, t.repo)
                    kw = {'agent_patch': '' if __import__('os').environ.get('PARCHE_VACIO') else t.patch}
                    params = inspect.signature(verify_task).parameters
                    if 'base_snapshot_path' in params:
                        kw.update(base_snapshot_path=bsp, patch_path=pp)
                    if 'start_time' in params:
                        kw['start_time'] = time.perf_counter()
                    return await verify_task(evaluator.docker, evaluator.config, t, sp, **kw)
                r = dump_obj(run_sync(call))
                rec.update(resolved=r.get('resolved'), raw=r)
            else:
                r = run_sync(evaluator.evaluate_task, task=task, task_index=1, total_tasks=1)
                patch = (r.agent_patch or '').strip()
                rec.update(resolved=bool(r.resolved), patch=patch, tool_calls=r.tool_calls,
                           duration_s=round(r.duration_seconds or 0, 1), error=getattr(r, 'error', None),
                           raw=dump_obj(r))
        except Exception as e:
            import traceback
            rec.update(resolved=False, error=f'{type(e).__name__}: {e}', trace=traceback.format_exc()[-4000:])
        rec['segundos_reloj'] = round(time.time() - t0, 1)
        salida['tareas'].append(rec)
        print(f"{tid}: resolved={rec.get('resolved')} calls={rec.get('tool_calls')} "
              f"t={rec['segundos_reloj']}s patch={len(rec.get('patch') or '')} error={rec.get('error')}", flush=True)

    out = Path(a.out or work / f"salida_{'oraculo' if a.oracle else Path(a.variant).name}_{time.strftime('%H%M%S')}.json")
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    print('saved to', out)


if __name__ == '__main__':
    sys.exit(main())
