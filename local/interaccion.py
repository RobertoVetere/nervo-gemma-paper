#!/usr/bin/env python3
"""Section 4.2: interaction test of the 2x2 (agent x reasoning) on the 40-task sample.

For each task: (gain from reasoning of the free-form agent) - (gain from reasoning of fixer); exact two-sided sign test
on the non-zero differences. Usage: python3 local/interaccion.py [resultados/local_deepinfra/l40]
"""
import glob, json, sys
from math import comb

D = sys.argv[1] if len(sys.argv) > 1 else 'resultados/local_deepinfra/l40'


def solved(variant):
    r = {}
    for f in glob.glob(f'{D}/{variant}__*.json'):
        for t in json.load(open(f))['tareas']:
            r[t['id']] = int(bool(t.get('resolved')))
    return r


free0, free1, fix0, fix1 = (solved(v) for v in ('e4b_t0', 'base_comunidad', 'e4b_cmd', 'e4b_cmd_t'))
ids = sorted(free0)
assert len(ids) == 40 and set(ids) == set(free1) == set(fix0) == set(fix1)
print('solved: free-form no-reasoning', sum(free0.values()), '| reasoning', sum(free1.values()),
      '| fixer no-reasoning', sum(fix0.values()), '| reasoning', sum(fix1.values()))
d = [(free1[i] - free0[i]) - (fix1[i] - fix0[i]) for i in ids]
pos, neg = sum(x > 0 for x in d), sum(x < 0 for x in d)
n = pos + neg
p = min(1.0, 2 * sum(comb(n, k) for k in range(min(pos, neg) + 1)) / 2 ** n)
print(f'interaction: {pos} tasks favour, {neg} against; exact sign test p = {p:.4f}')
