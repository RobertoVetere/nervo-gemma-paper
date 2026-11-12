#!/usr/bin/env python3
"""Single-call chain v3: localize with the repository map, then fix with or without the symbol's existing tests.

Per task and sample (without looking at the official patch or the hidden tests):
  1. LOCALIZE (E4B, no reasoning) with repo_map.py, retrying if the symbol does not exist. The same localization is
     used in every configuration, so that only the repair step is compared.
  2. REPAIR under two conditions:  A = symbol code   C = symbol code + its existing tests (existing_tests.py)
     (and F = rewrite the whole function, with SONDA_CONDS=F), and three configurations:
       e4b      E4B without reasoning
       e4b_t    E4B with reasoning, capped at 16384 tokens so it has room to answer
       31b_r    31B without reasoning + SCOPE RULE in code: if a SEARCH touches definitions other than the localized
                symbol (except new methods added to its class), it is rejected and the model is asked once to redo it.
  3. Score with the hidden tests (FAIL_TO_PASS and the PASS_TO_PASS files).
Usage: python3 lab/oneshot/probe3.py --tasks t1,t2 --n 2   (NERVO_BENCH = folder with snapshots/, default ./bench)
"""
import argparse, ast, json, os, re, subprocess, sys, tarfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import llamar, puntuar_arreglo, bloques, INSTR_EDIT  # noqa: E402
import repo_map as M  # noqa: E402
from loc import PREG, leer, TAREAS  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIGS = {'e4b': ('e4b', 0, 4000, False), 'e4b_t': ('e4b', 1, 16384, False), '31b_r': ('31b', 0, 4000, True)}
CONDS = os.environ.get('SONDA_CONDS', 'A,C').split(',')  # F = rewrite the whole function (no SEARCH copy)
INSTR_FUNC = ('Answer with the complete new version of {where}: the whole definition (decorators, def line and body), '
              'in ONE ```python block, with the same name. Include only that definition, nothing else.')
if os.environ.get('SONDA_CONFIGS'):  # e.g. 'e4b,e4b_t' to use only the quantized E4B server on Modal
    CONFIGS = {k: v for k, v in CONFIGS.items() if k in os.environ['SONDA_CONFIGS'].split(',')}


def localizar(d, issue):
    mp = M.mapa(d, issue, 12000)
    prompt = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nREPOSITORY MAP (files most related '
              f'to the issue first; classes with their methods, and functions):\n{mp}' + PREG)
    r = llamar('e4b', prompt, 0, tope=300); archivo, where = leer(r['texto'])
    if where and not M.existe(d, where)[0]:
        extra = M.existe(d, where)[2]
        r = llamar('e4b', prompt + f'\n\n(Your previous answer named {where}, which does not exist in this repository. '
                   'Closest real symbols: ' + '; '.join(extra) + '. Answer again.)', 0, tope=300)
        archivo, where = leer(r['texto'])
    return archivo, where


def fuera_de_alcance(ruta, where, texto):
    """Definitions touched by each SEARCH that are not the localized symbol (nor its class, when a method is added)."""
    src = open(ruta, errors='replace').read(); arbol = ast.parse(src); L = src.splitlines()
    objetivo = re.sub(r'\(.*', '', where).split('.')
    defs = []
    for c in ast.walk(arbol):
        if isinstance(c, ast.ClassDef):
            for f in c.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)): defs.append((f'{c.name}.{f.name}', f.lineno, f.end_lineno))
    for f in arbol.body:
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)): defs.append((f.name, f.lineno, f.end_lineno))
    malos = set()
    for s, _ in bloques(texto):
        bus = [x.strip() for x in s.splitlines() if x.strip()]
        if not bus: continue
        ini = next((i + 1 for i in range(len(L)) if L[i].strip() == bus[0]), None)
        if ini is None: continue
        fin = ini + len(s.splitlines()) - 1
        for nombre, a, b in defs:
            if a <= fin and b >= ini:
                ok = nombre == '.'.join(objetivo[-2:]) or nombre == objetivo[-1] or \
                     (len(objetivo) >= 2 and nombre.split('.')[0] == objetivo[-2] and objetivo[-1] not in [d[0].split('.')[-1] for d in defs])
                if not ok: malos.add(nombre)
    return sorted(malos)


def nodo_funcion(ruta, where):
    """(start, end, indent), 1-based, of the def named by where ('Class.method' or 'function'), or None."""
    src = open(ruta, errors='replace').read(); partes = re.sub(r'\(.*', '', where).split('.')
    for n in ast.walk(ast.parse(src)):
        cuerpo = n.body if isinstance(n, (ast.Module, ast.ClassDef)) else []
        if isinstance(n, ast.ClassDef) and (len(partes) < 2 or n.name != partes[-2]):
            continue
        if isinstance(n, ast.Module) and len(partes) >= 2:
            continue
        for f in cuerpo:
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == partes[-1]:
                ini = f.decorator_list[0].lineno if f.decorator_list else f.lineno
                return ini, f.end_lineno, f.col_offset
    return None


def funcion_a_bloque(ruta, where, texto):
    """Turn the function rewritten by the model into an exact SEARCH/REPLACE block (done by code, not by the model)."""
    import textwrap
    pos = nodo_funcion(ruta, where)
    codigos = re.findall(r'```(?:python)?\n(.*?)```', texto, re.S)
    if not pos or not codigos:
        return ''
    ini, fin, col = pos; L = open(ruta, errors='replace').read().splitlines()
    nuevo = textwrap.indent(textwrap.dedent(max(codigos, key=len)).strip('\n'), ' ' * col)
    return '<<<<<<< SEARCH\n' + '\n'.join(L[ini - 1:fin]) + '\n=======\n' + nuevo + '\n>>>>>>> REPLACE'


def arreglar(cfg, tarea, archivo, where, ctx, d, cond='A'):
    modelo, razonar, tope, regla = CONFIGS[cfg]
    instr = INSTR_FUNC.format(where=where) if cond == 'F' else INSTR_EDIT.format(archivo=archivo)
    p = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{tarea["problem_statement"].strip()}\n\n'
         f'The code to change ({where}) is in {archivo}:\n```python\n{ctx}\n```\n\n' + instr)
    if regla:
        p += f'\nChange only {where} (you may add new methods to its class). Do not modify any other function or method.'
    r = llamar(modelo, p, razonar, tope=tope); rechazos = 0
    if cond == 'F':
        r['texto'] = funcion_a_bloque(os.path.join(d, archivo), where, r['texto'])
        return r, 0
    if regla and r['texto']:
        malos = fuera_de_alcance(os.path.join(d, archivo), where, r['texto'])
        if malos:
            rechazos = 1
            r = llamar(modelo, p + f'\n\nYour previous answer also modified {", ".join(malos)}, which is outside {where}. '
                       f'That change was REJECTED. Answer again changing only {where}.', razonar, tope=tope)
    return r, rechazos


def una(tid, i):
    t = TAREAS[tid]; d = os.path.join(os.environ.get('NERVO_WORK', '/tmp/nervo_probes'), 'loc', tid)
    archivo, where = localizar(d, t['problem_statement'].strip())
    gold = re.findall(r'^\+\+\+ b/(\S+\.py)', t['patch'], re.M)
    fila = {'task': tid, 'sample': i, 'file': archivo, 'where': where, 'file_ok': archivo in gold}
    if not archivo or not where or not os.path.exists(os.path.join(d, archivo)):
        return {**fila, 'nota': 'invalid localization'}
    cod = subprocess.run([sys.executable, f'{AQUI}/context2.py', d, archivo, where, '--solo'], capture_output=True, text=True)
    if cod.returncode != 0:  # new method: give the class
        cod = subprocess.run([sys.executable, f'{AQUI}/context2.py', d, archivo, where.split('.')[0], '--solo'], capture_output=True, text=True)
    tests = subprocess.run([sys.executable, f'{AQUI}/existing_tests.py', d, where], capture_output=True, text=True).stdout
    fila['tests_chars'] = len(tests); fila['has_tests'] = not tests.startswith('# No existing')
    for cfg in CONFIGS:
        ctxs = {'A': cod.stdout, 'C': cod.stdout + '\n\n' + tests, 'F': cod.stdout}
        for cond in CONDS:
            ctx = ctxs[cond]
            if cond == 'F' and not nodo_funcion(os.path.join(d, archivo), where):
                fila[f'{cfg}_F'] = {'solved': False, 'reason': 'symbol is not an existing function', 'na': True}
                continue
            r, rech = arreglar(cfg, t, archivo, where, ctx, d, cond)
            nota = puntuar_arreglo(d, t, archivo, r['texto'], f'{cfg}{cond}{i}')
            fila[f'{cfg}_{cond}'] = {'solved': nota['solved'], 'f2p': nota.get('f2p'), 'reason': nota.get('reason', ''),
                                     'rejections': rech, 'tokens': r['usage'].get('completion_tokens'), 'empty': not r['texto']}
    return fila


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', '--tareas', dest='tareas', required=True); ap.add_argument('--n', type=int, default=2)
    ap.add_argument('--out', default=f'{RAIZ}/lab/oneshot/chain3.jsonl')
    a = ap.parse_args()
    tareas = a.tareas.split(',')
    for tid in tareas:
        d = os.path.join(os.environ.get('NERVO_WORK', '/tmp/nervo_probes'), 'loc', tid)
        if not os.path.isdir(d):
            os.makedirs(d); tarfile.open(os.path.join(os.environ.get('NERVO_BENCH', 'bench'), 'snapshots', f'{tid}.tgz')).extractall(d, filter='data')
        subprocess.run(['rm', '-rf', f'{d}/.fixer'])
    filas = []
    with cf.ThreadPoolExecutor(4) as ex, open(a.out, 'w') as out:
        for f in ex.map(lambda x: una(*x), [(t, i) for t in tareas for i in range(a.n)]):
            filas.append(f); out.write(json.dumps(f, ensure_ascii=False) + '\n'); out.flush()
            print(f"{f['task'][:34]:34} #{f['sample']} loc={f['file_ok']!s:5} {str(f['where'])[:30]:30} tests={f.get('has_tests')!s:5} " +
                  ' '.join(f"{k}={'X' if f[k]['solved'] else '.'}" for k in f if '_' in k and isinstance(f[k], dict)), flush=True)
    print('\nSolved (of', len(filas), 'rows):')
    for cfg in CONFIGS:
        for c in CONDS:
            print(f'  {cfg:6} {c}: solved', sum(bool(f.get(f'{cfg}_{c}', {}).get('solved')) for f in filas),
                  '| SEARCH does not match', sum('does not match' in str(f.get(f'{cfg}_{c}', {}).get('reason', '')) for f in filas),
                  '| no block', sum('no SEARCH/REPLACE' in str(f.get(f'{cfg}_{c}', {}).get('reason', '')) for f in filas),
                  '| n/a (not a function)', sum(bool(f.get(f'{cfg}_{c}', {}).get('na')) for f in filas))
        a_ = sum(bool(f.get(f'{cfg}_A', {}).get('solved')) for f in filas); c_ = sum(bool(f.get(f'{cfg}_C', {}).get('solved')) for f in filas)
        sa = sum(bool(f.get(f'{cfg}_A', {}).get('solved')) and not f.get(f'{cfg}_C', {}).get('solved') for f in filas)
        sc = sum(bool(f.get(f'{cfg}_C', {}).get('solved')) and not f.get(f'{cfg}_A', {}).get('solved') for f in filas)
        vac = sum(bool(f.get(f'{cfg}_{c}', {}).get('empty')) for f in filas for c in 'AC')
        rech = sum(f.get(f'{cfg}_{c}', {}).get('rejections', 0) for f in filas for c in 'AC')
        print(f'  {cfg:6} A (code only) {a_:2}   C (+ existing tests) {c_:2}   only A {sa} / only C {sc}   empty answers {vac}   rejections {rech}')


if __name__ == '__main__':
    main()
