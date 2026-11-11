#!/usr/bin/env python3
"""Sondas one shot sobre UNA tarea real: dónde se rompe el modelo (localizar, entender o escribir el arreglo).

Sin agente ni harness: nosotros damos el contexto y el código puntúa cada respuesta con los tests ocultos de la tarea.
Niveles (cada uno da más contexto que el anterior):
  L0  issue + lista de archivos .py        -> ¿qué archivo, clase y función cambiaría? (se puntúa contra el parche oficial)
  L1  issue + código de la clase culpable  -> bloque SEARCH/REPLACE (se aplica y se pasan los tests ocultos)
  L2  L1 + dos métodos hermanos de ejemplo -> igual que L1
  L3  issue + contexto recuperado por contexto.py (sin mirar el parche oficial) -> igual que L1
Uso: python3 lab/oneshot/sonda.py --task ipython__traitlets-773 --modelos e4b,31b --razonar 0,1 --n 3 --niveles L0,L1,L2
"""
import argparse, ast, json, os, re, shutil, subprocess, sys, tarfile, time, urllib.request, concurrent.futures as cf

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELOS = {'e4b': 'google/gemma-4-E4B-it', '31b': 'google/gemma-4-31B-it'}
URL = 'https://api.deepinfra.com/v1/openai/chat/completions'


BASE_MODAL = os.environ.get('NERVO_SONDA_MODAL', '')  # p. ej. https://...--nervo-vllm-e4b-servir.modal.run/v1 (modelo cuantizado)
MODELOS_KAGGLE = {'e4b': 'gemma-4-e4b-it-qat-w4a16-ct', '31b': 'gemma-4-31b-it-qat-w4a16-ct'}


def llamar(modelo, prompt, razonar, tope=8192):
    url, clave, nombre = URL, '~/.deepinfra_key', MODELOS[modelo]
    if BASE_MODAL:
        url, clave, nombre = BASE_MODAL.rstrip('/') + '/chat/completions', '~/.modal_vllm_key', MODELOS_KAGGLE[modelo]
    body = {'model': nombre, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.2,
            'top_p': 0.95, 'max_tokens': tope, 'chat_template_kwargs': {'enable_thinking': bool(razonar)}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {
        'Authorization': 'Bearer ' + open(os.path.expanduser(clave)).read().strip(),
        'Content-Type': 'application/json'})
    for intento in range(4):
        try:
            t = time.time()
            d = json.load(urllib.request.urlopen(req, timeout=1200))
            m = d['choices'][0]['message']
            return {'texto': m.get('content') or '', 'razonamiento': m.get('reasoning_content') or '',
                    'uso': d.get('usage', {}), 'segundos': round(time.time() - t, 1)}
        except Exception as e:  # noqa: BLE001
            err = str(e); time.sleep(5 * (intento + 1))
    return {'texto': '', 'razonamiento': '', 'uso': {}, 'error': err}


def clase(src, nombre):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.ClassDef) and n.name == nombre:
            ini = n.decorator_list[0].lineno if n.decorator_list else n.lineno
            return '\n'.join(src.splitlines()[ini - 1:n.end_lineno])
    raise SystemExit(f'no encuentro la clase {nombre}')


def metodo(src, cls, nombre):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.ClassDef) and n.name == cls:
            for f in n.body:
                if isinstance(f, ast.FunctionDef) and f.name == nombre:
                    return f'class {cls}(...):\n    ...\n' + '\n'.join(src.splitlines()[f.lineno - 1:f.end_lineno])
    raise SystemExit(f'no encuentro {cls}.{nombre}')


def bloques(texto):
    return re.findall(r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE', texto, re.S)


def aplicar(ruta, bl):
    src = open(ruta).read()
    for s, r in bl:
        if src.count(s) == 1:
            src = src.replace(s, r); continue
        # tolerante a espacios al final de línea y sangría común
        lineas = src.splitlines(); bus = [l.rstrip() for l in s.splitlines()]
        hit = [i for i in range(len(lineas) - len(bus) + 1)
               if [l.rstrip() for l in lineas[i:i + len(bus)]] == bus]
        if len(hit) != 1:
            return False, f'SEARCH no encaja ({len(hit)} coincidencias): {s[:80]!r}'
        i = hit[0]; lineas[i:i + len(bus)] = r.splitlines(); src = '\n'.join(lineas) + '\n'
    open(ruta, 'w').write(src)
    return True, 'ok'


def puntuar_arreglo(base, tarea, archivo, texto, n):
    bl = bloques(texto)
    if not bl:
        return {'aplica': False, 'motivo': 'sin bloques SEARCH/REPLACE', 'resuelve': False}
    d = f'{base}_prueba_{n}'
    shutil.rmtree(d, ignore_errors=True); shutil.copytree(base, d)
    ok, motivo = aplicar(os.path.join(d, archivo), bl)
    if not ok:
        shutil.rmtree(d, ignore_errors=True)
        return {'aplica': False, 'motivo': motivo, 'resuelve': False}
    subprocess.run(['git', 'apply', '-'], cwd=d, input=tarea['test_patch'].encode(), check=True)
    f2p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider', *tarea['FAIL_TO_PASS']],
                         cwd=d, capture_output=True, text=True, timeout=300)
    archivos_p2p = sorted({t.split('::')[0] for t in tarea['PASS_TO_PASS']})
    p2p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *archivos_p2p],
                         cwd=d, capture_output=True, text=True, timeout=600)
    shutil.rmtree(d, ignore_errors=True)
    ult = lambda p: (p.stdout.strip().splitlines() or [''])[-1]
    return {'aplica': True, 'f2p': f2p.returncode == 0, 'p2p': p2p.returncode == 0,
            'resuelve': f2p.returncode == 0 and p2p.returncode == 0, 'f2p_salida': ult(f2p), 'p2p_salida': ult(p2p)}


INSTR_EDIT = ('Answer with the code change only, as one or more SEARCH/REPLACE blocks for {archivo}, exactly in this format:\n'
              '<<<<<<< SEARCH\n<exact lines copied from the code above>\n=======\n<new lines>\n>>>>>>> REPLACE\n'
              'The SEARCH part must be copied exactly from the code shown. Keep the original indentation.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task', default='ipython__traitlets-773')
    ap.add_argument('--clase', default='Union')
    ap.add_argument('--hermanos', default='TraitType.from_string,Int.from_string')
    ap.add_argument('--modelos', default='e4b,31b')
    ap.add_argument('--razonar', default='0,1')
    ap.add_argument('--niveles', default='L0,L1,L2')
    ap.add_argument('--n', type=int, default=3)
    ap.add_argument('--out', default=None)
    ap.add_argument('--etiqueta', default='')
    a = ap.parse_args()
    tarea = next(json.loads(l) for l in open(f'{RAIZ}/datos/banco_nuevo/validation_tasks.jsonl')
                 if json.loads(l)['instance_id'] == a.task)
    archivo = re.findall(r'^\+\+\+ b/(\S+\.py)', tarea['patch'], re.M)[0]
    trabajo = f'/home/claude/sondas/{a.task}'
    shutil.rmtree(trabajo, ignore_errors=True); os.makedirs(trabajo)
    tarfile.open(f'/home/claude/banco/snapshots/{a.task}.tgz').extractall(trabajo)
    base = trabajo if os.path.isdir(f'{trabajo}/.git') else os.path.join(trabajo, os.listdir(trabajo)[0])
    src = open(os.path.join(base, archivo)).read()
    issue = tarea['problem_statement'].strip()
    pys = subprocess.run(['git', 'ls-files', '*.py'], cwd=base, capture_output=True, text=True).stdout.split()
    pys = [p for p in pys if '/tests/' not in p and not p.split('/')[-1].startswith('test_')]
    cod = clase(src, a.clase)
    herm = '\n\n'.join(metodo(src, *h.split('.')) for h in a.hermanos.split(',')) if a.hermanos else ''
    prompts = {
        'L0': (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nPYTHON FILES IN THE REPOSITORY:\n'
               + '\n'.join(pys) + '\n\nWhich file, class and function/method must change to fix this issue, and what '
               'must the change do? Answer in 3 lines:\nFILE: ...\nWHERE: Class.method (or "new method Class.name")\nCHANGE: one sentence'),
        'L1': (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nThe bug is in this class from {archivo}:\n'
               f'```python\n{cod}\n```\n\n' + INSTR_EDIT.format(archivo=archivo)),
        'L2': (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nThe bug is in this class from {archivo}:\n'
               f'```python\n{cod}\n```\n\nFor reference, this is how other trait types in the same file implement the same '
               f'mechanism:\n```python\n{herm}\n```\n\n' + INSTR_EDIT.format(archivo=archivo)),
    }
    ctx = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'contexto.py'),
                          base, archivo, a.clase], capture_output=True, text=True).stdout
    prompts['L3'] = (f'You are fixing a bug in a Python repository.\n\nISSUE:\n{issue}\n\nThe bug is in class {a.clase} '
                     f'from {archivo}. Here is the class and how the same codebase implements related behaviour:\n'
                     f'```python\n{ctx}\n```\n\n' + INSTR_EDIT.format(archivo=archivo))
    gold_where = re.findall(r'^\+\s*def (\w+)', tarea['patch'], re.M)
    trabajos = [(nv, m, int(r), i) for nv in a.niveles.split(',') for m in a.modelos.split(',')
                for r in a.razonar.split(',') for i in range(a.n)]
    out = a.out or f'{RAIZ}/lab/oneshot/resultados_{a.task}{a.etiqueta}.jsonl'
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(llamar, m, prompts[nv], r): (nv, m, r, i) for nv, m, r, i in trabajos}
        res = []
        for f in cf.as_completed(futs):
            nv, m, r, i = futs[f]; resp = f.result()
            res.append((nv, m, r, i, resp))
    filas = []
    for k, (nv, m, r, i, resp) in enumerate(sorted(res, key=lambda x: x[:4])):
        t = resp['texto']
        if nv == 'L0':
            nota = {'archivo_ok': archivo in t, 'clase_ok': a.clase in t,
                    'metodo_ok': any(g in t for g in gold_where), 'resuelve': None}
        else:
            nota = puntuar_arreglo(base, tarea, archivo, t, k)
        fila = {'tarea': a.task, 'nivel': nv, 'modelo': m, 'razonar': r, 'muestra': i, **nota,
                'tokens_salida': resp['uso'].get('completion_tokens'), 'segundos': resp.get('segundos'),
                'error': resp.get('error'), 'respuesta': t, 'razonamiento': resp['razonamiento']}
        filas.append(fila)
        print(f"{nv} {m:3} razonar={r} #{i} ", {k2: v for k2, v in nota.items() if k2 in
              ('archivo_ok', 'clase_ok', 'metodo_ok', 'aplica', 'f2p', 'p2p', 'resuelve', 'motivo')}, flush=True)
    with open(out, 'w') as f:
        for x in filas: f.write(json.dumps(x, ensure_ascii=False) + '\n')
    coste = sum((x.get('tokens_salida') or 0) for x in filas)
    print('guardado', out, 'tokens de salida', coste)


if __name__ == '__main__':
    main()
