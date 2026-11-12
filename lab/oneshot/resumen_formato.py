#!/usr/bin/env python3
"""Summary of the tool-call format experiment (formato_llamadas.py).
Usage: python3 -I resumen_formato.py res1.jsonl res2.jsonl ..."""
import json, math, sys
from collections import defaultdict


def fisher(a, b, c, d):  # two-sided exact test on [[a, b], [c, d]]
    n = a + b + c + d; r1, c1 = a + b, a + c
    p = lambda x: math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
g = defaultdict(list)
for r in rows:
    g[(r['backend'], r['modelo'], r['iface'])].append(r)
print('| Backend | Model | Interface | Calls | Not called | Fields lost / unparsable | Text not exact | Exact |')
print('|---|---|---|---|---|---|---|---|')
for k in sorted(g):
    v = g[k]; n = len(v)
    nc = sum(not x['called'] for x in v); bad = sum(x['called'] and not x['args_ok'] for x in v)
    ne = sum(x['args_ok'] and not x['exact'] for x in v); ex = sum(x['exact'] for x in v)
    print(f'| {k[0]} | {k[1]} | {k[2]} | {n} | {nc} | {bad} | {ne} | {ex} ({100*ex/n:.0f}%) |')
print()
for k in sorted(g):
    v = g[k]
    q = [x for x in v if x['ends_quote']]; o = [x for x in v if not x['ends_quote']]
    fq = sum(not x['exact'] for x in q); fo = sum(not x['exact'] for x in o)
    print(f'{k}: failures ending in quote {fq}/{len(q)}, other {fo}/{len(o)}, Fisher p = {fisher(fq, len(q)-fq, fo, len(o)-fo):.3f}')
print()
bk = sorted({(k[0], k[1]) for k in g})
for i, a in enumerate(bk):
    for b in bk[i + 1:]:
        if a[1] != b[1]:
            continue
        for f in sorted({k[2] for k in g}):
            va, vb = g.get((*a, f), []), g.get((*b, f), [])
            if va and vb:
                fa = sum(not x['exact'] for x in va); fb = sum(not x['exact'] for x in vb)
                print(f'{f}: {a[0]} {fa}/{len(va)} vs {b[0]} {fb}/{len(vb)} failures, Fisher p = '
                      f'{fisher(fa, len(va)-fa, fb, len(vb)-fb):.3f}')
