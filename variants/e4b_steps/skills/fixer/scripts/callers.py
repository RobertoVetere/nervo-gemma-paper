"""CALLERS: every place in the source code that calls the given functions, plus copies of them.

args: {"names": "should_skip,sort_imports"}   (function or method names, comma separated)
Use it before writing /tmp/check.py: the check must exercise EVERY call site, because a fix that works
for one caller can still be wrong for another.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import definitions, enclosing_function, go_to_repo, source_files  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', default='')
    ap.add_argument('--name', default='')  # tolerated: the model sometimes reuses show_function's args
    a, _ = ap.parse_known_args()
    a.names = a.names or a.name
    if not a.names:
        print('ERROR: args must be {"names": "function_a,function_b"}')
        return
    if not go_to_repo():
        print('ERROR: repository not found')
        return
    names = [n.strip().split('.')[-1] for n in a.names.split(',') if n.strip()]
    files = source_files()
    loaded = {}
    for f in files:
        try:
            s = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        loaded[f] = (s, s.splitlines(), definitions(s))
    for name in names:
        pat = re.compile(r'\b' + re.escape(name) + r'\s*\(')
        defs = [(f, d) for f, (_, _, ds) in loaded.items() for d in ds if d[0].split('.')[-1] == name]
        print(f'== {name}')
        print('DEFINED AT: ' + (', '.join(f'{f}:{d[1]} ({d[0]})' for f, d in defs) or 'not found in source'))
        if len(defs) > 1:
            print('COPIES: the same name is defined in several places. If you change one, check whether the '
                  'others need the same change.')
        calls = []
        for f, (text, lines, ds) in loaded.items():
            if name not in text:
                continue
            for i, l in enumerate(lines, 1):
                if pat.search(l) and not re.match(r'\s*(async\s+)?def\s', l):
                    fn = enclosing_function(ds, i)
                    calls.append(f'- {f}:{i} in {fn[0] if fn else "<module>"}: {l.strip()[:140]}')
        print(f'CALLED FROM ({len(calls)}):')
        print('\n'.join(calls[:25]) if calls else '- no calls found in source')
        print()


if __name__ == '__main__':
    main()
