#!/usr/bin/env python3
"""Tests EXISTENTES de un símbolo (agnóstico al caso, sin modelo): cómo se prueba hoy esa función/clase.

Los tests ocultos de una tarea suelen ir en el mismo archivo que los tests que ya existen del código que se toca;
ver qué casos y qué estilo usan es la mejor pista de lo que se pedirá. Solo usa el repositorio tal como lo ve el
agente (antes de que el harness añada los tests ocultos).
Uso: python3 tests_de.py <repo> <simbolo> [--max 3000]   (simbolo: Clase, Clase.metodo o funcion)
"""
import argparse, ast, os, re, subprocess

ES_TEST = re.compile(r'(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('simbolo'); ap.add_argument('--max', type=int, default=3000)
    a = ap.parse_args()
    partes = re.sub(r'\(.*', '', a.simbolo.strip().strip('`')).split('.')
    nombres = [p for p in partes[-2:] if p and not (p.startswith('__') and p.endswith('__'))] or partes[-1:]
    hallados = []
    for nombre in reversed(nombres):  # primero el método/función, luego la clase
        out = subprocess.run(['git', 'grep', '-l', '-w', '-F', nombre, '--', '*.py'], cwd=a.repo,
                             capture_output=True, text=True).stdout.split()
        for ruta in [r for r in out if ES_TEST.search(r)]:
            try:
                src = open(os.path.join(a.repo, ruta), errors='replace').read(); arbol = ast.parse(src)
            except Exception:  # noqa: BLE001
                continue
            L = src.splitlines()
            for n in ast.walk(arbol):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test'):
                    ini = n.decorator_list[0].lineno if n.decorator_list else n.lineno
                    cod = '\n'.join(L[ini - 1:n.end_lineno])
                    if re.search(r'\b' + re.escape(nombre) + r'\b', cod):
                        hallados.append((ruta, n.name, cod))
        if hallados:
            break
    if not hallados:
        print(f'# No existing tests mention {a.simbolo}'); return
    vistos, sel, total = set(), [], 0
    for ruta, nom, cod in sorted(hallados, key=lambda x: len(x[2])):
        if (ruta, nom) in vistos or total + len(cod) > a.max:
            continue
        vistos.add((ruta, nom)); sel.append((ruta, nom, cod)); total += len(cod)
        if len(sel) >= 5: break
    print(f'# Existing tests that use {a.simbolo} ({len(hallados)} found, shortest shown)')
    for ruta, nom, cod in sel:
        print(f'\n# {ruta}::{nom}\n{cod}')


if __name__ == '__main__':
    main()
