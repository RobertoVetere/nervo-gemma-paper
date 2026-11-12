"""SHOW_FUNCTION: print the code of a function, method or class with line numbers.

args: {"file": "pkg/module.py", "name": "Class.method"}   (name can be just "method")
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re  # noqa: E402
from _common import called_definitions, class_outline, definitions, go_to_repo, index_definitions, numbered, source_files  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--name', required=True)
    a = ap.parse_args()
    go_to_repo()
    try:
        src = open(a.file, encoding='utf-8', errors='replace').read()
    except OSError as e:
        print(f'ERROR: {e}')
        return
    lines, defs = src.splitlines(), definitions(src)
    match = [d for d in defs if d[0] == a.name] or [d for d in defs if d[0].split('.')[-1] == a.name.split('.')[-1]]
    if not match:
        print(f'ERROR: {a.name} not found in {a.file}. Definitions: ' + ', '.join(d[0] for d in defs[:60]))
        return
    index = index_definitions(source_files())
    for d in match[:2]:
        print(f'### {a.file} :: {d[0]} (lines {d[1]}-{d[2]})')
        print(numbered(lines, d[1], 120 if d[3] else 150))
        if d[3]:
            continue
        calls = called_definitions('\n'.join(lines[d[1] - 1:d[2]]), index, a.file, d[0])
        if calls:
            print('\nREPOSITORY FUNCTIONS IT CALLS (the real behaviour is often there):')
            for f, q, s0, e0, _ in calls:
                print(f'- {q}  {f}:{s0}')
            for f, q, s0, e0, _ in sorted(calls, key=lambda c: c[3] - c[2])[:3]:
                try:
                    cl = open(f, encoding='utf-8', errors='replace').read().splitlines()
                except OSError:
                    continue
                print(f'\n### {f} :: {q} (lines {s0}-{e0})')
                print(numbered(cl, s0, 40))
        body = '\n'.join(lines[d[1] - 1:d[2]])
        used = []
        for name in sorted(set(re.findall(r'\b([A-Z][A-Za-z0-9_]+)\b', body))):
            for f, q, s0, e0, is_class in index.get(name, []):
                if is_class and (f, q) not in used:
                    used.append((f, q))
                    print('\nCLASS USED IN THIS FUNCTION:')
                    print(class_outline(f, q, s0, e0))
                    break
            if len(used) >= 3:
                break


if __name__ == '__main__':
    main()
    print('\nNEXT: at most one more show_function, then run_command with: python3 .fixer/callers.py --names <function_to_change>')
