#!/usr/bin/env python3
"""Cadena one shot v3: localizar con el mapa, y arreglar con o sin los tests existentes del símbolo.

Por tarea y muestra (sin mirar el parche oficial ni los tests ocultos):
  1. LOCALIZAR (E4B, sin razonar) con mapa.py y reintento si el símbolo no existe. La misma localización se usa en
     todas las configuraciones, para comparar solo la fase de arreglo.
  2. ARREGLAR en dos condiciones:  A = código del símbolo   C = código del símbolo + sus tests existentes (tests_de.py)
     y tres configuraciones:
       e4b      E4B sin razonar
       e4b_t    E4B razonando, con tope de 16384 tokens para que le dé tiempo a responder
       31b_r    31B sin razonar + REGLA DE ALCANCE en código: si el SEARCH toca definiciones distintas del símbolo
                localizado (salvo añadir métodos nuevos a su clase), se rechaza y se le pide una vez que lo rehaga.
  3. Puntuar con los tests ocultos (FAIL_TO_PASS y archivos de PASS_TO_PASS).
Uso: python3 lab/oneshot/sonda3.py --tareas t1,t2 --n 2
"""
import argparse, ast, json, os, re, subprocess, sys, tarfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonda import llamar, puntuar_arreglo, bloques, INSTR_EDIT  # noqa: E402
import mapa as M  # noqa: E402
from loc import PREG, leer, TAREAS  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AQUI = os.path.dirname(os.path.abspath(__file__))
CONFIGS = {'e4b': ('e4b', 0, 4000, False), 'e4b_t': ('e4b', 1, 16384, False), '31b_r': ('31b', 0, 4000, True)}
CONDS = os.environ.get('SONDA_CONDS', 'A,C').split(',')  # F = reescribir la función entera (sin copiar SEARCH)
INSTR_FUNC = ('Answer with the complete new version of {where}: the whole definition (decorators, def line and body), '
              'in ONE ```python block, with the same name. Include only that definition, nothing else.')
if os.environ.get('SONDA_CONFIGS'):  # p. ej. 'e4b,e4b_t' para usar solo el servidor E4B cuantizado de Modal
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
    """Definiciones que toca cada SEARCH y no son el símbolo localizado (ni su clase, si se añade un método)."""
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
    """(inicio, fin, sangría) 1-based del def nombrado por where ('Clase.metodo' o 'funcion'), o None."""
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
    """Convierte la función reescrita por el modelo en un bloque SEARCH/REPLACE exacto (lo hace el código, no el modelo)."""
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
    t = TAREAS[tid]; d = f'/home/claude/sondas_loc/{tid}'
    archivo, where = localizar(d, t['problem_statement'].strip())
    gold = re.findall(r'^\+\+\+ b/(\S+\.py)', t['patch'], re.M)
    fila = {'tarea': tid, 'muestra': i, 'archivo': archivo, 'where': where, 'archivo_ok': archivo in gold}
    if not archivo or not where or not os.path.exists(os.path.join(d, archivo)):
        return {**fila, 'nota': 'localización inválida'}
    cod = subprocess.run([sys.executable, f'{AQUI}/contexto2.py', d, archivo, where, '--solo'], capture_output=True, text=True)
    if cod.returncode != 0:  # método nuevo: se da la clase
        cod = subprocess.run([sys.executable, f'{AQUI}/contexto2.py', d, archivo, where.split('.')[0], '--solo'], capture_output=True, text=True)
    tests = subprocess.run([sys.executable, f'{AQUI}/tests_de.py', d, where], capture_output=True, text=True).stdout
    fila['tests_chars'] = len(tests); fila['hay_tests'] = not tests.startswith('# No existing')
    for cfg in CONFIGS:
        ctxs = {'A': cod.stdout, 'C': cod.stdout + '\n\n' + tests, 'F': cod.stdout}
        for cond in CONDS:
            ctx = ctxs[cond]
            if cond == 'F' and not nodo_funcion(os.path.join(d, archivo), where):
                fila[f'{cfg}_F'] = {'resuelve': False, 'motivo': 'símbolo no es una función existente', 'na': True}
                continue
            r, rech = arreglar(cfg, t, archivo, where, ctx, d, cond)
            nota = puntuar_arreglo(d, t, archivo, r['texto'], f'{cfg}{cond}{i}')
            fila[f'{cfg}_{cond}'] = {'resuelve': nota['resuelve'], 'f2p': nota.get('f2p'), 'motivo': nota.get('motivo', ''),
                                     'rechazos': rech, 'tokens': r['uso'].get('completion_tokens'), 'vacia': not r['texto']}
    return fila


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tareas', required=True); ap.add_argument('--n', type=int, default=2)
    ap.add_argument('--out', default=f'{RAIZ}/lab/oneshot/cadena3.jsonl')
    a = ap.parse_args()
    tareas = a.tareas.split(',')
    for tid in tareas:
        d = f'/home/claude/sondas_loc/{tid}'
        if not os.path.isdir(d):
            os.makedirs(d); tarfile.open(f'/home/claude/banco/snapshots/{tid}.tgz').extractall(d, filter='data')
        subprocess.run(['rm', '-rf', f'{d}/.fixer'])
    filas = []
    with cf.ThreadPoolExecutor(4) as ex, open(a.out, 'w') as out:
        for f in ex.map(lambda x: una(*x), [(t, i) for t in tareas for i in range(a.n)]):
            filas.append(f); out.write(json.dumps(f, ensure_ascii=False) + '\n'); out.flush()
            print(f"{f['tarea'][:34]:34} #{f['muestra']} loc={f['archivo_ok']!s:5} {str(f['where'])[:30]:30} tests={f.get('hay_tests')!s:5} " +
                  ' '.join(f"{k}={'X' if f[k]['resuelve'] else '.'}" for k in f if '_' in k and isinstance(f[k], dict)), flush=True)
    print('\nResueltas (de', len(filas), 'filas):')
    for cfg in CONFIGS:
        for c in CONDS:
            print(f'  {cfg:6} {c}: resueltas', sum(bool(f.get(f'{cfg}_{c}', {}).get('resuelve')) for f in filas),
                  '| SEARCH no encaja', sum('no encaja' in str(f.get(f'{cfg}_{c}', {}).get('motivo', '')) for f in filas),
                  '| sin bloque', sum('sin bloques' in str(f.get(f'{cfg}_{c}', {}).get('motivo', '')) for f in filas),
                  '| no aplica (no es función)', sum(bool(f.get(f'{cfg}_{c}', {}).get('na')) for f in filas))
        a_ = sum(bool(f.get(f'{cfg}_A', {}).get('resuelve')) for f in filas); c_ = sum(bool(f.get(f'{cfg}_C', {}).get('resuelve')) for f in filas)
        sa = sum(bool(f.get(f'{cfg}_A', {}).get('resuelve')) and not f.get(f'{cfg}_C', {}).get('resuelve') for f in filas)
        sc = sum(bool(f.get(f'{cfg}_C', {}).get('resuelve')) and not f.get(f'{cfg}_A', {}).get('resuelve') for f in filas)
        vac = sum(bool(f.get(f'{cfg}_{c}', {}).get('vacia')) for f in filas for c in 'AC')
        rech = sum(f.get(f'{cfg}_{c}', {}).get('rechazos', 0) for f in filas for c in 'AC')
        print(f'  {cfg:6} A (solo código) {a_:2}   C (+ tests existentes) {c_:2}   solo A {sa} / solo C {sc}   respuestas vacías {vac}   rechazos {rech}')


if __name__ == '__main__':
    main()
