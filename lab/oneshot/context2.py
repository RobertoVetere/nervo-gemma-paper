#!/usr/bin/env python3
"""Case-agnostic context for fixing one symbol of a Python repository, with no model and without looking at the patch.

Input: repository, file and symbol as the model names it ("Class", "Class.method" or "function"; if the method does
not exist yet, the class is used). Output, ordered and capped in characters:
  1. the symbol's code (or the class, trimmed if huge);
  2. its PEERS: how the repository itself solves the same thing
       - method:   the same method in the base class and in sibling classes (the shortest versions);
       - class:    the "hooks" of its bases that many siblings override and it does not, with examples;
       - function: functions of the same module with a similar name or signature;
  3. who calls it (git grep) and which repository functions it calls.
Usage: python3 context2.py <repo> <file.py> <symbol> [--max 6000] [--only]
"""
import argparse, ast, os, re, subprocess

SALTAR = re.compile(r'(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$')


def indexar(repo):
    clases, funcs = {}, {}
    rutas = subprocess.run(['git', 'ls-files', '*.py'], cwd=repo, capture_output=True, text=True).stdout.split()
    for ruta in rutas:
        if SALTAR.search(ruta):
            continue
        try:
            src = open(os.path.join(repo, ruta), errors='replace').read(); arbol = ast.parse(src)
        except Exception:  # noqa: BLE001
            continue
        L = src.splitlines()
        cod = lambda n: '\n'.join(L[(n.decorator_list[0].lineno if getattr(n, 'decorator_list', None) else n.lineno) - 1:n.end_lineno])
        for n in arbol.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.setdefault(n.name, []).append({'ruta': ruta, 'codigo': cod(n), 'args': [x.arg for x in n.args.args]})
        for n in ast.walk(arbol):
            if isinstance(n, ast.ClassDef):
                bases = [b.id if isinstance(b, ast.Name) else getattr(b, 'attr', '') for b in n.bases]
                met = {f.name: cod(f) for f in n.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
                clases.setdefault(n.name, {'ruta': ruta, 'bases': bases, 'metodos': met, 'codigo': cod(n), 'linea': n.lineno})
    return clases, funcs


def ancestros(c, cl, v=None):
    v = [] if v is None else v
    for b in cl.get(c, {}).get('bases', []):
        if b in cl and b not in v:
            v.append(b); ancestros(b, cl, v)
    return v


def hermanas(c, cl):
    anc = set(ancestros(c, cl))
    return [o for o in cl if o != c and (set(ancestros(o, cl)) | {o}) & anc]


def recortar_clase(info, maximo=2500):
    if len(info['codigo']) <= maximo:
        return info['codigo']
    cab = info['codigo'].splitlines()[0]
    firmas = [m.splitlines()[0].strip() if not m.lstrip().startswith('@') else
              next(l.strip() for l in m.splitlines() if l.strip().startswith(('def', 'async def'))) for m in info['metodos'].values()]
    return cab + '\n    # (class too long: method signatures only)\n' + '\n'.join('    ' + f for f in firmas)


def llamadas_de(codigo, cl, funcs):
    nombres = set(re.findall(r'(?<![\w.])([A-Za-z_]\w*)\(', codigo)) | set(re.findall(r'\.(\w+)\(', codigo))
    return [n for n in sorted(nombres) if n in funcs or any(n in c['metodos'] for c in cl.values())][:12]


def usos(repo, nombre, metodo):
    patron = f'.{nombre}(' if metodo else f'{nombre}('
    out = subprocess.run(['git', 'grep', '-n', '-F', patron, '--', '*.py'], cwd=repo, capture_output=True, text=True).stdout
    filas = [u for u in out.splitlines() if f'def {nombre}' not in u and not SALTAR.search(u.split(':')[0])]
    return filas[:6]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('archivo'); ap.add_argument('simbolo')
    ap.add_argument('--max', type=int, default=6000)
    ap.add_argument('--only', '--solo', dest='solo', action='store_true', help='only the symbol code (control without context)')
    a = ap.parse_args()
    cl, funcs = indexar(a.repo)
    s = re.sub(r'\(.*', '', a.simbolo.strip().strip('`')).split('.')
    partes = []
    if len(s) >= 2 and s[-2] in cl:
        c, m = s[-2], s[-1]
        if m in cl[c]['metodos']:
            cod = cl[c]['metodos'][m]
            partes.append(f'# {c}.{m} ({cl[c]["ruta"]})\n{cod}')
            partes.append(f'# The rest of class {c} (for context)\n' + recortar_clase(cl[c]))
            for b in ancestros(c, cl):
                if m in cl[b]['metodos']:
                    partes.append(f'# {b}.{m} (base class)\n{cl[b]["metodos"][m]}'); break
            pares = sorted((o for o in hermanas(c, cl) if m in cl[o]['metodos']), key=lambda o: len(cl[o]['metodos'][m]))[:2]
            for o in pares:
                partes.append(f'# {o}.{m} (sibling class)\n{cl[o]["metodos"][m]}')
            u = usos(a.repo, m, True)
            if u: partes.append(f'# Where {m} is called\n' + '\n'.join(x[:160] for x in u))
            ll = llamadas_de(cod, cl, funcs)
            if ll: partes.append('# Repository functions/methods it calls: ' + ', '.join(ll))
        else:
            s = [c]
    if not partes and s[-1] in cl:
        c = s[-1]
        partes.append(f'# Class {c} ({cl[c]["ruta"]})\n' + recortar_clase(cl[c]))
        propios = set(cl[c]['metodos']); her = hermanas(c, cl); gan = []
        for b in ancestros(c, cl):
            for m, cod in cl[b]['metodos'].items():
                if m in propios or (m.startswith('__') and m.endswith('__')):
                    continue
                quien = [o for o in her if m in cl[o]['metodos'] and o != b]
                if len(quien) >= 2: gan.append((len(quien), m, b, quien))
        gan.sort(reverse=True)
        if gan:
            partes.append(f'# Methods of its base classes that many sibling classes override but {c} does NOT:\n' +
                          '\n'.join(f'- {m}: defined in {b}, overridden by {n} classes' for n, m, b, _ in gan[:5]))
        for n, m, b, quien in gan[:2]:
            partes.append(f'# {b}.{m} (base implementation)\n{cl[b]["metodos"][m]}')
            for o in sorted(quien, key=lambda o: len(cl[o]['metodos'][m]))[:2]:
                partes.append(f'# {o}.{m} (sibling class)\n{cl[o]["metodos"][m]}')
            u = usos(a.repo, m, True)
            if u: partes.append(f'# Where {m} is called\n' + '\n'.join(x[:160] for x in u))
    if not partes and s[-1] in funcs:
        f = s[-1]
        defs = sorted(funcs[f], key=lambda d: d['ruta'] != a.archivo)
        partes.append(f'# {f} ({defs[0]["ruta"]})\n{defs[0]["codigo"]}')
        tokens = set(f.strip('_').split('_')) - {'', 'get', 'set', 'is', 'to', 'from', 'do'}
        mismo = [(n, d) for n, ds in funcs.items() for d in ds if n != f and d['ruta'] == defs[0]['ruta']]
        puntua = lambda nd: (len(tokens & set(nd[0].split('_'))), len(set(nd[1]['args']) & set(defs[0]['args'])), -len(nd[1]['codigo']))
        pares = [x for x in sorted(mismo, key=puntua, reverse=True) if puntua(x)[:2] != (0, 0)][:2]
        for n, d in pares:
            partes.append(f'# {n} (similar function in the same module)\n{d["codigo"]}')
        u = usos(a.repo, f, False)
        if u: partes.append(f'# Where {f} is called\n' + '\n'.join(x[:160] for x in u))
        ll = llamadas_de(defs[0]['codigo'], cl, funcs)
        if ll: partes.append('# Repository functions/methods it calls: ' + ', '.join(ll))
    if not partes:
        raise SystemExit(f'symbol not found: {a.simbolo}')
    texto = partes[0] if a.solo else '\n\n'.join(partes)
    print(texto[:a.max] + ('\n[... cut]' if len(texto) > a.max else ''))


if __name__ == '__main__':
    main()
