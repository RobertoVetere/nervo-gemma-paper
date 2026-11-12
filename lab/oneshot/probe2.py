#!/usr/bin/env python3
"""Case-agnostic single-call chain: the model localizes, code retrieves the context, the model repairs.

Per task and model, without reasoning and without looking at the official patch:
  1. LOCALIZE: issue + list of files -> FILE and WHERE (Class, Class.method or function).
  2. REPAIR, under two conditions with the same localization:
       A  only the symbol's code                       (context2.py --only)
       B  symbol + peers + uses in the repository      (context2.py)
  3. Score: apply the SEARCH/REPLACE and run the hidden tests (FAIL_TO_PASS and the PASS_TO_PASS files).
Usage: python3 lab/oneshot/probe2.py --tasks t1,t2 --models e4b,31b --n 2
"""
import argparse, json, os, re, shutil, subprocess, sys, tarfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import llamar, puntuar_arreglo, INSTR_EDIT  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CTX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'context2.py')


def preparar(tid):
    tarea = next(json.loads(l) for l in open(f'{RAIZ}/data/new_bench/validation_tasks.jsonl')
                 if json.loads(l)['instance_id'] == tid)
    d = os.path.join(os.environ.get('NERVO_WORK', '/tmp/nervo_probes'), tid)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    tarfile.open(os.path.join(os.environ.get('NERVO_BENCH', 'bench'), 'snapshots', f'{tid}.tgz')).extractall(d, filter='data')
    pys = subprocess.run(['git', 'ls-files', '*.py'], cwd=d, capture_output=True, text=True).stdout.split()
    pys = [p for p in pys if not re.search(r'(^|/)(tests?|testing|docs?)/|(^|/)test_|conftest', p)]
    return tarea, d, pys


def localizar(modelo, tarea, pys):
    p = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{tarea["problem_statement"].strip()}\n\n'
         'PYTHON FILES IN THE REPOSITORY:\n' + '\n'.join(pys[:400]) +
         '\n\nWhich file and which class, method or function must change to fix this issue? Answer in exactly 2 lines:\n'
         'FILE: path/to/file.py\nWHERE: Class.method, Class, or function_name')
    r = llamar(modelo, p, 0, tope=300)
    f = re.search(r'FILE:\s*`?([\w./-]+\.py)', r['texto']); w = re.search(r'WHERE:\s*`?([\w.]+)', r['texto'])
    return (f.group(1) if f else None), (w.group(1) if w else None), r


def arreglar(modelo, tarea, archivo, ctx):
    p = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{tarea["problem_statement"].strip()}\n\n'
         f'The code to change is in {archivo}:\n```python\n{ctx}\n```\n\n' + INSTR_EDIT.format(archivo=archivo))
    return llamar(modelo, p, 0, tope=4000)


def una(tid, modelo, i, k):
    tarea, d, pys = preparar_cache[tid]
    archivo, where, r0 = localizar(modelo, tarea, pys)
    gold = re.findall(r'^\+\+\+ b/(\S+\.py)', tarea['patch'], re.M)
    fila = {'tarea': tid, 'modelo': modelo, 'muestra': i, 'archivo': archivo, 'where': where,
            'archivo_ok': archivo in gold, 'loc_respuesta': r0['texto']}
    if not archivo or not where or not os.path.exists(os.path.join(d, archivo)):
        return {**fila, 'A': {'resuelve': False, 'motivo': 'invalid localization'}, 'B': {'resuelve': False, 'motivo': 'invalid localization'}}
    for cond, extra in (('A', ['--solo']), ('B', [])):
        c = subprocess.run([sys.executable, CTX, d, archivo, where, *extra], capture_output=True, text=True)
        if c.returncode != 0:
            fila[cond] = {'resuelve': False, 'motivo': 'symbol not found: ' + c.stderr.strip()[-80:]}; continue
        r = arreglar(modelo, tarea, archivo, c.stdout)
        nota = puntuar_arreglo(d, tarea, archivo, r['texto'], f'{modelo}{i}{cond}{k}')
        fila[cond] = {**nota, 'ctx_chars': len(c.stdout), 'respuesta': r['texto']}
    return fila


preparar_cache = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', '--tareas', dest='tareas', required=True); ap.add_argument('--models', '--modelos', dest='modelos', default='e4b,31b')
    ap.add_argument('--n', type=int, default=2); ap.add_argument('--out', default=f'{RAIZ}/lab/oneshot/chain.jsonl')
    a = ap.parse_args()
    tareas = a.tareas.split(',')
    for t in tareas: preparar_cache[t] = preparar(t)
    trabajos = [(t, m, i, k) for k, (t, m, i) in enumerate((t, m, i) for t in tareas for m in a.modelos.split(',') for i in range(a.n))]
    with cf.ThreadPoolExecutor(4) as ex, open(a.out, 'a') as out:
        for fila in ex.map(lambda x: una(*x), trabajos):
            out.write(json.dumps(fila, ensure_ascii=False) + '\n'); out.flush()
            print(f"{fila['tarea'][:36]:36} {fila['modelo']:3} #{fila['muestra']} loc={fila['archivo_ok']!s:5} {fila['where']!s:32} "
                  f"A={fila['A'].get('resuelve')!s:5} B={fila['B'].get('resuelve')!s:5} "
                  f"{fila['A'].get('motivo','')[:30]} {fila['B'].get('motivo','')[:30]}", flush=True)


if __name__ == '__main__':
    main()
