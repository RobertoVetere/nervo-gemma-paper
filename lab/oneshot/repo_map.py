#!/usr/bin/env python3
"""Repository map for localizing without inventing names (in the style of Aider's repo map; no model, case-agnostic).

  repo_map.py <repo> --issue issue.txt [--max 12000]  -> map: files ranked by relation to the issue, with their
                                                          classes (bases and method signatures) and functions
  repo_map.py <repo> --existe 'Class.method'          -> OK path  /  NO + the 5 closest real symbols
                                                          (--exists is an alias of --existe)

Ranking: points for each issue word (identifiers, CamelCase, snake_case, paths) found in the path or in the file's
symbol names; exact names from the issue weigh more.
"""
import argparse, ast, difflib, os, re, subprocess

SALTAR = re.compile(r'(^|/)(tests?|testing|docs?|examples?|benchmarks?)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|setup\.py$')
VACIAS = set('the and for with this that from into when then than not are was were has have but use used using can '
             'should would could will what which where how why its also only just like same some other more most none '
             'true false self return value values type types code line lines file files error errors issue bug fix test '
             'tests example examples python version expected actual output input result results def class import'.split())


def simbolos(repo):
    out = {}
    for ruta in subprocess.run(['git', 'ls-files', '*.py'], cwd=repo, capture_output=True, text=True).stdout.split():
        if SALTAR.search(ruta):
            continue
        try:
            arbol = ast.parse(open(os.path.join(repo, ruta), errors='replace').read())
        except Exception:  # noqa: BLE001
            continue
        filas = []
        def firma(f):
            args = [a.arg for a in f.args.args if a.arg not in ('self', 'cls')]
            if f.args.vararg: args.append('*' + f.args.vararg.arg)
            if f.args.kwarg: args.append('**' + f.args.kwarg.arg)
            return f'{f.name}({", ".join(args)})'
        for n in arbol.body:
            if isinstance(n, ast.ClassDef):
                bases = ', '.join(b.id if isinstance(b, ast.Name) else getattr(b, 'attr', '?') for b in n.bases)
                mets = [firma(f) for f in n.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]
                filas.append(('class', n.name, f'class {n.name}({bases}): ' + '; '.join(mets),
                              [f.name for f in n.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))]))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                filas.append(('def', n.name, 'def ' + firma(n), []))
        out[ruta] = filas
    return out


def palabras(issue):
    ident = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}', issue))
    exactos = {w for w in ident if '_' in w or re.search(r'[a-z][A-Z]', w) or w[0].isupper()}
    partes = set()
    for w in ident:
        partes |= {p.lower() for p in re.split(r'_|(?<=[a-z])(?=[A-Z])', w) if len(p) > 2}
    return {w.lower() for w in exactos}, partes - VACIAS


def puntuar(ruta, filas, exactos, partes):
    nombres = {ruta.lower()} | {f[1].lower() for f in filas} | {m.lower() for f in filas for m in f[3]}
    trozos = set()
    for n in nombres:
        trozos |= {p for p in re.split(r'[_/.]|(?<=[a-z])(?=[A-Z])', n) if len(p) > 2}
    return 5 * len(exactos & nombres) + len(partes & trozos) + len(partes & set(re.split(r'[/_.]', ruta.lower())))


def _toca(nombre, exactos, partes):
    n = nombre.lower()
    return n in exactos or bool(partes & {p for p in re.split(r'_|(?<=[a-z])(?=[A-Z])', nombre.lower()) if len(p) > 2}) \
        or bool(partes & {p.lower() for p in re.split(r'_|(?<=[a-z])(?=[A-Z])', nombre) if len(p) > 2})


def bloque(ruta, filas, exactos, partes, grande):
    """Block for one file; if large, only the symbols that touch the issue (and the methods that touch it)."""
    if not grande:
        return ruta + '\n' + '\n'.join('  ' + f[2] for f in filas)
    lineas = []
    for tipo, n, txt, mets in filas:
        if tipo == 'def':
            if _toca(n, exactos, partes): lineas.append('  ' + txt)
            continue
        sel = [m for m in txt.split(': ', 1)[1].split('; ') if m and _toca(m.split('(')[0], exactos, partes)]
        if _toca(n, exactos, partes) or sel:
            resto = len(mets) - len(sel)
            lineas.append('  ' + txt.split(': ', 1)[0] + ': ' + '; '.join(sel) + (f'  (+{resto} more methods)' if resto > 0 else ''))
    otros = len(filas) - len(lineas)
    return ruta + '  (large file: only symbols related to the issue)\n' + '\n'.join(lineas) + \
        (f'\n  ... {otros} other classes/functions' if otros > 0 else '')


def mapa(repo, issue, maximo):
    sim = simbolos(repo); exactos, partes = palabras(issue)
    pts = {r: puntuar(r, sim[r], exactos, partes) for r in sim}
    orden = sorted(sim, key=lambda r: (-pts[r], r))
    trozos, resto, usado = [], [], 0
    for r in orden:
        b = bloque(r, sim[r], exactos, partes, False)
        if len(b) > maximo // 3:
            b = bloque(r, sim[r], exactos, partes, True)
        if usado + len(b) <= maximo and (pts[r] > 0 or not trozos):
            trozos.append(b); usado += len(b) + 1
        else:
            resto.append(r)
    texto = '\n'.join(trozos)
    if resto:
        texto += '\n# other files (no details): ' + ', '.join(resto[:80])
    return texto


def existe(repo, simbolo):
    sim = simbolos(repo); s = re.sub(r'\(.*', '', simbolo.strip().strip('`')).split('.')
    todos = []
    for r, filas in sim.items():
        for tipo, n, _, mets in filas:
            todos.append((n, r)); todos += [(f'{n}.{m}', r) for m in mets]
    clave = '.'.join(s[-2:]) if len(s) >= 2 else s[0]
    hit = [r for n, r in todos if n == clave]
    if hit:
        return True, hit[0], []
    if len(s) >= 2 and any(n == s[-2] for n, r in todos):  # new method in a class that does exist
        return True, next(r for n, r in todos if n == s[-2]), ['NEW METHOD in existing class ' + s[-2]]
    parecidos = difflib.get_close_matches(clave, [n for n, _ in todos], n=5, cutoff=0.5)
    return False, None, [f'{p} ({next(r for n, r in todos if n == p)})' for p in parecidos]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('--issue'); ap.add_argument('--existe', '--exists', dest='existe'); ap.add_argument('--max', type=int, default=12000)
    a = ap.parse_args()
    if a.existe:
        ok, ruta, extra = existe(a.repo, a.existe)
        print(('OK ' + ruta) if ok else 'NO', *extra, sep='\n')
    else:
        print(mapa(a.repo, open(a.issue).read(), a.max))
