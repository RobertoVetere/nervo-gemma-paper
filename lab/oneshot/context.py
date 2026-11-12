#!/usr/bin/env python3
"""Retrieve, with no model, the context a small model needs to fix a class:
how the repository ITSELF solves the same thing in sibling classes.

Idea (single-call probes on traitlets-773): the models localize the class well, but without seeing the repository's
mechanism they invent names. This script finds it on its own:
  1. the class code;
  2. the "hooks": methods of its base classes that many sibling classes override and this class does not;
  3. for each hook, the base version and two short sibling versions;
  4. where each hook is called in the repository.
Usage: python3 context.py <repo> <file.py> <Class> [--max 6000]
"""
import argparse, ast, os, re, subprocess


def clases_del_repo(repo):
    out = {}
    for ruta in subprocess.run(['git', 'ls-files', '*.py'], cwd=repo, capture_output=True, text=True).stdout.split():
        if '/tests/' in ruta or ruta.split('/')[-1].startswith('test_'):
            continue
        try:
            src = open(os.path.join(repo, ruta)).read(); arbol = ast.parse(src)
        except Exception:  # noqa: BLE001
            continue
        lineas = src.splitlines()
        for n in ast.walk(arbol):
            if isinstance(n, ast.ClassDef):
                bases = [b.id if isinstance(b, ast.Name) else getattr(b, 'attr', '') for b in n.bases]
                metodos = {f.name: '\n'.join(lineas[f.lineno - 1:f.end_lineno])
                           for f in n.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
                ini = n.decorator_list[0].lineno if n.decorator_list else n.lineno
                out.setdefault(n.name, {'ruta': ruta, 'bases': bases, 'metodos': metodos,
                                        'codigo': '\n'.join(lineas[ini - 1:n.end_lineno])})
    return out


def ancestros(nombre, cl, vistos=None):
    vistos = vistos or []
    for b in cl.get(nombre, {}).get('bases', []):
        if b in cl and b not in vistos:
            vistos.append(b); ancestros(b, cl, vistos)
    return vistos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('file'); ap.add_argument('clase')
    ap.add_argument('--max', type=int, default=6000)
    a = ap.parse_args()
    cl = clases_del_repo(a.repo)
    if a.clase not in cl:
        raise SystemExit(f'class not found: {a.clase}')
    anc = ancestros(a.clase, cl)
    propios = set(cl[a.clase]['metodos'])
    # siblings: classes that share an ancestor with the target class
    hermanas = [c for c in cl if c != a.clase and set(ancestros(c, cl) + [c]) & set(anc)]
    ganchos = []
    for base in anc:
        for m, cod in cl[base]['metodos'].items():
            if m in propios or (m.startswith('__') and m not in ('__call__',)):
                continue
            quien = [c for c in hermanas if m in cl[c]['metodos'] and c != base]
            if len(quien) >= 2:
                ganchos.append((len(quien), m, base, quien))
    ganchos.sort(reverse=True)
    partes = [f'# Class {a.clase} ({cl[a.clase]["ruta"]})\n{cl[a.clase]["codigo"]}']
    if ganchos:
        partes.append('# Methods of its base classes that many sibling classes override but '
                      f'{a.clase} does NOT (the usual way this codebase customises behaviour):\n' +
                      '\n'.join(f'- {m}: defined in {b}, overridden by {n} classes' for n, m, b, _ in ganchos[:5]))
    for n, m, b, quien in ganchos[:2]:
        cortas = sorted(quien, key=lambda c: len(cl[c]['metodos'][m]))[:2]
        partes.append(f'# {b}.{m} (base implementation)\n{cl[b]["metodos"][m]}')
        for c in cortas:
            partes.append(f'# {c}.{m} (sibling class {c}({", ".join(cl[c]["bases"])}))\n{cl[c]["metodos"][m]}')
        usos = subprocess.run(['git', 'grep', '-n', '-F', f'.{m}(', '--', '*.py', ':!*tests*'], cwd=a.repo,
                              capture_output=True, text=True).stdout.splitlines()
        usos = [u for u in usos if f'def {m}' not in u][:6]
        if usos:
            partes.append(f'# Where {m} is called\n' + '\n'.join(u.strip()[:160] for u in usos))
    texto = '\n\n'.join(partes)
    print(texto[:a.max] + ('\n[... cut]' if len(texto) > a.max else ''))


if __name__ == '__main__':
    main()
