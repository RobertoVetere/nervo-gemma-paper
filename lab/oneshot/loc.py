#!/usr/bin/env python3
"""¿Localiza mejor el modelo con el mapa del repositorio? Solo localización, una llamada (y un reintento validado).

Condiciones: lista (issue + nombres de archivo)  /  mapa (issue + mapa.py, y si el símbolo no existe, un reintento
con los 5 reales más parecidos). Se puntúa contra los símbolos que toca el parche oficial (archivo y símbolo).
Uso: python3 lab/oneshot/loc.py --tareas-archivo lote40.txt --modelos e4b,31b
"""
import argparse, ast, json, os, re, shutil, subprocess, sys, tarfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonda import llamar  # noqa: E402
import mapa as M  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAREAS = {json.loads(l)['instance_id']: json.loads(l) for l in open(f'{RAIZ}/datos/banco_nuevo/validation_tasks.jsonl')}
PREG = ('\n\nWhich file and which class, method or function must change to fix this issue? If the fix needs a NEW method '
        'or function, name it as Class.new_name or new_name. Answer in exactly 2 lines:\nFILE: path/to/file.py\n'
        'WHERE: Class.method, Class, or function_name')


def oro(repo, parche):
    """Símbolos que toca el parche oficial: {(archivo, 'Clase.metodo' | 'Clase' | 'funcion')}."""
    out = set()
    for bloque in re.split(r'^(?=--- (?:a/|/dev/null))', parche, flags=re.M):
        m = re.search(r'^\+\+\+ b/(\S+\.py)', bloque, re.M)
        if not m or M.SALTAR.search(m.group(1)): continue
        ruta = m.group(1); p = os.path.join(repo, ruta)
        if not os.path.exists(p): out.add((ruta, '<new file>')); continue
        arbol = ast.parse(open(p, errors='replace').read())
        for h in re.finditer(r'^@@ -(\d+)(?:,(\d+))? ', bloque, re.M):
            ini = int(h.group(1)); fin = ini + max(int(h.group(2) or 1), 1) - 1
            mejor = None
            for n in ast.walk(arbol):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.lineno <= fin and n.end_lineno >= ini:
                    if mejor is None or n.lineno > mejor.lineno: mejor = n
            if mejor is None: out.add((ruta, '<module>')); continue
            nombre = mejor.name
            for c in ast.walk(arbol):
                if isinstance(c, ast.ClassDef) and mejor in c.body: nombre = f'{c.name}.{mejor.name}'
            out.add((ruta, nombre))
    return out


def acierto(archivo, where, gold):
    if not archivo or not where: return False, False
    w = re.sub(r'\(.*', '', where).strip('`')
    f_ok = any(archivo == g[0] for g in gold)
    s_ok = any(archivo == g[0] and (w == g[1] or w.split('.')[0] == g[1].split('.')[0] or g[1] in ('<module>',) or
                                     w.split('.')[-1] == g[1].split('.')[-1]) for g in gold)
    return f_ok, s_ok


def leer(texto):
    f = re.search(r'FILE:\s*`?([\w./-]+\.py)', texto); w = re.search(r'WHERE:\s*`?([\w.]+)', texto)
    return (f.group(1) if f else None), (w.group(1) if w else None)


def una(tid, modelo, cond):
    t = TAREAS[tid]; d = f'/home/claude/sondas_loc/{tid}'
    issue = t['problem_statement'].strip(); gold = oro(d, t['patch'])
    if cond == 'lista':
        pys = [p for p in subprocess.run(['git', 'ls-files', '*.py'], cwd=d, capture_output=True, text=True).stdout.split()
               if not M.SALTAR.search(p)]
        r = llamar(modelo, f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nPYTHON FILES IN THE REPOSITORY:\n'
                   + '\n'.join(pys[:400]) + PREG, 0, tope=300)
        archivo, where = leer(r['texto']); reintento = False
    else:
        mp = M.mapa(d, issue, 12000)
        prompt = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nREPOSITORY MAP (files most related '
                  f'to the issue first; classes with their methods, and functions):\n{mp}' + PREG)
        r = llamar(modelo, prompt, 0, tope=300); archivo, where = leer(r['texto']); reintento = False
        if where:
            ok, ruta, extra = M.existe(d, where)
            if not ok:
                reintento = True
                r = llamar(modelo, prompt + f'\n\n(Your previous answer named {where}, which does not exist in this repository. '
                           'Closest real symbols: ' + '; '.join(extra) + '. Answer again.)', 0, tope=300)
                archivo, where = leer(r['texto'])
    f_ok, s_ok = acierto(archivo, where, gold)
    return {'tarea': tid, 'modelo': modelo, 'cond': cond, 'archivo': archivo, 'where': where, 'oro': sorted(gold),
            'archivo_ok': f_ok, 'simbolo_ok': s_ok, 'reintento': reintento, 'respuesta': r['texto']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tareas-archivo', required=True); ap.add_argument('--modelos', default='e4b,31b')
    ap.add_argument('--out', default=f'{RAIZ}/lab/oneshot/loc.jsonl')
    a = ap.parse_args()
    tareas = open(a.tareas_archivo).read().split()
    for tid in tareas:
        d = f'/home/claude/sondas_loc/{tid}'
        if not os.path.isdir(d):
            os.makedirs(d); tarfile.open(f'/home/claude/banco/snapshots/{tid}.tgz').extractall(d, filter='data')
    trabajos = [(t, m, c) for t in tareas for m in a.modelos.split(',') for c in ('lista', 'mapa')]
    filas = []
    with cf.ThreadPoolExecutor(8) as ex, open(a.out, 'w') as out:
        for f in ex.map(lambda x: una(*x), trabajos):
            filas.append(f); out.write(json.dumps(f, ensure_ascii=False) + '\n'); out.flush()
    for m in a.modelos.split(','):
        for c in ('lista', 'mapa'):
            S = [f for f in filas if f['modelo'] == m and f['cond'] == c]
            print(f'{m:3} {c:5} archivo {sum(f["archivo_ok"] for f in S)}/{len(S)}  símbolo {sum(f["simbolo_ok"] for f in S)}/{len(S)}'
                  f'  reintentos {sum(f["reintento"] for f in S)}')


if __name__ == '__main__':
    main()
