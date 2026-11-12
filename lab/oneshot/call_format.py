#!/usr/bin/env python3
"""Controlled tool-call format experiment (no agent, no repository changes).

Each item is a real block of Python code (6-30 lines; half of them ending in a quote or backtick) taken from the validation-set repositories, plus an edited
version (one inserted line). The model is asked to apply the edit with ONE tool call, copying both texts exactly.
Three interfaces, same text, same instructions:
  three_field  run_skill_script(skill_name, file_path, args={path, search, replace})   (the old skill call)
  edit_file    edit_file(path, old_string, new_string)                                   (built-in style edit)
  one_field    write_file(path, content) with the edit as a SEARCH/REPLACE block in content (our interface)
Scored per call: tool called with the right name / arguments parse and required fields present / texts exact
(trailing whitespace of each line ignored). Also records whether the block ends in a quote or backtick, the trigger
other participants report for the Gemma 4 string delimiter.
Backends: our vLLM server on Modal (--modal URL, ~/.modal_vllm_key, vLLM gemma4 tool parser) with the official quantized
weights (--modelo e4b) or the unquantized bf16 weights (--modelo e4b-bf16); or an API (DeepInfra). Note: in Nov 2026
DeepInfra served google/gemma-4-E4B-it requests with google/gemma-4-31B-it-turbo (replaced_by), so its 'e4b' is a 31B.
Usage: python3 -I call_format.py --items 80 --samples 2 [--context 36000] --model e4b --backend modal --modal <url>/v1 --out res.jsonl
"""
import argparse, ast, concurrent.futures as cf, glob, json, os, random, tarfile, tempfile, time, urllib.request

MOD_DI = {'e4b': 'google/gemma-4-E4B-it', '31b': 'google/gemma-4-31B-it'}
MOD_Q = {'e4b': 'gemma-4-e4b-it-qat-w4a16-ct', '31b': 'gemma-4-31b-it-qat-w4a16-ct',
         'e4b-bf16': 'gemma-4-e4b-it',  # same vLLM server and parser, unquantized weights
         'e2b': 'gemma-4-e2b-it-qat-w4a16-ct', 'e2b-bf16': 'gemma-4-e2b-it',
         'qwen3-4b-awq': 'qwen3-4b-awq', 'qwen3-4b-bf16': 'qwen3-4b', 'qwen3-1.7b-bf16': 'qwen3-1.7b'}

S = {'type': 'string'}
TOOLS = {
    'three_field': {'name': 'run_skill_script', 'description': 'Run a script of a skill.',
                    'parameters': {'type': 'object', 'required': ['skill_name', 'file_path', 'args'], 'properties': {
                        'skill_name': S, 'file_path': S,
                        'args': {'type': 'object', 'description': 'Arguments for the script.',
                                 'properties': {'path': S, 'search': S, 'replace': S}}}}},
    'edit_file': {'name': 'edit_file', 'description': 'Replace old_string with new_string in a file.',
                  'parameters': {'type': 'object', 'required': ['path', 'old_string', 'new_string'],
                                 'properties': {'path': S, 'old_string': S, 'new_string': S}}},
    'one_field': {'name': 'write_file', 'description': 'Write content to a file.',
                  'parameters': {'type': 'object', 'required': ['path', 'content'],
                                 'properties': {'path': S, 'content': S}}},
}
HOW = {
    'three_field': 'Call run_skill_script with skill_name "fixer", file_path "scripts/apply_edit.py" and args '
                   '{"path": "<FILE>", "search": <OLD TEXT>, "replace": <NEW TEXT>}.',
    'edit_file': 'Call edit_file with path "<FILE>", old_string = OLD TEXT and new_string = NEW TEXT.',
    'one_field': 'Call write_file with path ".fixer/edit.txt" and content =\n<<<<<<< SEARCH\n<OLD TEXT>\n=======\n'
                 '<NEW TEXT>\n>>>>>>> REPLACE',
}


def bloques_de_codigo(banco, n, semilla):
    rnd = random.Random(semilla); out = []
    tgzs = sorted(glob.glob(os.path.join(banco, 'snapshots', '*.tgz')))
    tmp = tempfile.mkdtemp(prefix='fmt_')
    cands = []
    for tz in tgzs:
        repo = os.path.basename(tz).split('-')[0]
        with tarfile.open(tz) as t:
            for m in t.getmembers():
                if not m.isfile() or not m.name.endswith('.py') or '/test' in m.name or m.size > 200_000:
                    continue
                try:
                    src = t.extractfile(m).read().decode()
                    tree = ast.parse(src)
                except Exception:  # noqa: BLE001
                    continue
                lines = src.splitlines()
                for f in ast.walk(tree):
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and 8 <= f.end_lineno - f.lineno <= 60:
                        cands.append((repo, m.name, lines, f.lineno, f.end_lineno))
    rnd.shuffle(cands); vistos = set()
    for repo, path, lines, a, b in cands:
        if len(out) >= n:
            break
        if (repo, path) in vistos:
            continue
        k = rnd.randint(6, 30)
        finales = [i for i in range(a + 5, b + 1) if lines[i - 1].rstrip()[-1:] in '\'"`']
        if len(out) % 2 == 0 and finales:  # half the items end in a quote or backtick (reported delimiter trigger)
            e = rnd.choice(finales); ini = max(a, e - k + 1)
        else:
            ini = rnd.randint(a, max(a, b - k))
        blk = lines[ini - 1:ini - 1 + k] if not (len(out) % 2 == 0 and finales) else lines[ini - 1:e]
        if len(blk) < 6 or not blk[-1].strip():
            continue
        old = '\n'.join(blk)
        ind = len(blk[1]) - len(blk[1].lstrip()) if blk[1].strip() else 4
        new = '\n'.join([blk[0], ' ' * ind + '_edit_marker = True  # inserted'] + blk[1:])
        # partial blocks are fine: the test is copying, not compiling
        vistos.add((repo, path))
        out.append({'id': f'{repo}:{path}:{ini}', 'file': path.split('/', 1)[-1], 'old': old, 'new': new,
                    'ends_quote': old.rstrip()[-1:] in '\'"`',
                    'specials': sum(old.count(c) for c in '"\'`\\')})
    return out


CONTEXTO = {'texto': ''}


def contexto_de(banco, chars):
    out, total = [], 0
    for tz in sorted(glob.glob(os.path.join(banco, 'snapshots', '*.tgz')))[::-1]:
        with tarfile.open(tz) as t:
            for m in t.getmembers():
                if m.isfile() and m.name.endswith('.py') and '/test' not in m.name and 2000 < m.size < 20000:
                    txt = t.extractfile(m).read().decode(errors='replace')
                    out.append(f'--- read_file {m.name} ---\n{txt}'); total += len(txt)
                    if total >= chars:
                        return '\n'.join(out)
    return '\n'.join(out)


def prompt(it, iface):
    pre = (f'Files you read earlier in this session:\n{CONTEXTO["texto"]}\n\n' if CONTEXTO['texto'] else '')
    return pre + (f'Apply this edit to the file {it["file"]} with ONE tool call. Copy both texts EXACTLY, character by '
            f'character, keeping indentation.\n\nOLD TEXT:\n```python\n{it["old"]}\n```\n\nNEW TEXT:\n```python\n'
            f'{it["new"]}\n```\n\n' + HOW[iface].replace('<FILE>', it['file']))


def llamar(backend, modelo, msg, tool, modal):
    if backend == 'deepinfra':
        url, key, name = 'https://api.deepinfra.com/v1/openai/chat/completions', '~/.deepinfra_key', MOD_DI[modelo]
    else:
        url, key, name = modal.rstrip('/') + '/chat/completions', '~/.modal_vllm_key', MOD_Q[modelo]
    body = {'model': name, 'messages': [{'role': 'user', 'content': msg}], 'temperature': 0.2, 'top_p': 0.95,
            'max_tokens': 4096, 'tools': [{'type': 'function', 'function': tool}], 'tool_choice': 'auto',
            'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {
        'Authorization': 'Bearer ' + open(os.path.expanduser(key)).read().strip(), 'Content-Type': 'application/json'})
    err = ''
    for i in range(5):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=600))
            return d['choices'][0]['message'], d.get('usage', {}), ''
        except Exception as e:  # noqa: BLE001
            err = str(e)[:300]; time.sleep(5 * (i + 1))
    return None, {}, err


def norm(s):
    return '\n'.join(l.rstrip() for l in (s or '').strip('\n').splitlines())


def puntuar(it, iface, msg):
    r = {'called': False, 'args_ok': False, 'exact': False, 'text_call': False}
    if not msg:
        return r
    calls = msg.get('tool_calls') or []
    r['text_call'] = (not calls) and any(k in (msg.get('content') or '') for k in ('run_skill_script', 'edit_file',
                                                                                  'write_file', 'tool_call'))
    if not calls:
        return r
    f = calls[0].get('function', {})
    r['called'] = f.get('name') == TOOLS[iface]['name']
    try:
        a = json.loads(f.get('arguments') or '{}')
    except Exception:  # noqa: BLE001
        return r
    if iface == 'three_field':
        x = a.get('args') or {}
        if isinstance(x, str):
            try:
                x = json.loads(x)
            except Exception:  # noqa: BLE001
                x = {}
        ok = all(k in a for k in ('skill_name', 'file_path')) and all(k in x for k in ('search', 'replace'))
        o, n = x.get('search'), x.get('replace')
    elif iface == 'edit_file':
        ok = all(k in a for k in ('path', 'old_string', 'new_string')); o, n = a.get('old_string'), a.get('new_string')
    else:
        ok = 'content' in a and 'path' in a; c = a.get('content') or ''
        o = n = None
        if '<<<<<<< SEARCH' in c and '=======' in c and '>>>>>>> REPLACE' in c:
            body = c.split('<<<<<<< SEARCH', 1)[1].split('>>>>>>> REPLACE', 1)[0]
            o, _, n = body.partition('\n=======\n')
        else:
            ok = False
    r['args_ok'] = bool(r['called'] and ok)
    r['exact'] = bool(r['args_ok'] and norm(o) == norm(it['old']) and norm(n) == norm(it['new']))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bench', '--banco', dest='banco', default=os.environ.get('NERVO_BENCH', 'bench'), help='folder with snapshots/')
    ap.add_argument('--items', type=int, default=60)
    ap.add_argument('--seed', '--semilla', dest='semilla', type=int, default=12)
    ap.add_argument('--model', '--modelo', dest='modelo', default='e4b', help='key of MOD_Q (Modal) or MOD_DI (API)')
    ap.add_argument('--backend', choices=['deepinfra', 'modal'], default='deepinfra')
    ap.add_argument('--modal', default=os.environ.get('NERVO_SONDA_MODAL', ''))
    ap.add_argument('--samples', '--muestras', dest='muestras', type=int, default=1); ap.add_argument('--threads', '--hilos', dest='hilos', type=int, default=8)
    ap.add_argument('--out', required=True)
    ap.add_argument('--context', '--contexto', dest='contexto', type=int, default=0, help='characters of real code read earlier, put before the request')
    a = ap.parse_args()
    if a.contexto:
        CONTEXTO['texto'] = contexto_de(a.banco, a.contexto)
    items = bloques_de_codigo(a.banco, a.items, a.semilla)
    hechos = set()
    if os.path.exists(a.out):
        for l in open(a.out):
            x = json.loads(l); hechos.add((x['id'], x['iface'], x['sample']))
    trabajos = [(it, f, k) for it in items for f in TOOLS for k in range(a.muestras) if (it['id'], f, k) not in hechos]
    print(f'{len(items)} blocks, {len(trabajos)} calls', flush=True)

    def uno(t):
        it, f, k = t
        m, uso, err = llamar(a.backend, a.modelo, prompt(it, f), TOOLS[f], a.modal)
        r = puntuar(it, f, m)
        return {'id': it['id'], 'iface': f, 'sample': k, 'backend': a.backend, 'model': a.modelo + (f'+ctx{a.contexto // 1000}k' if a.contexto else ''),
                'ends_quote': it['ends_quote'], 'specials': it['specials'], 'error': err, 'usage': uso, **r,
                'raw': (json.dumps(m)[:4000] if m else '')}
    with open(a.out, 'a') as fo, cf.ThreadPoolExecutor(a.hilos) as ex:
        for res in ex.map(uno, trabajos):
            fo.write(json.dumps(res) + '\n'); fo.flush()
    print('done', flush=True)


if __name__ == '__main__':
    main()
