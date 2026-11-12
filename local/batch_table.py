#!/usr/bin/env python3
"""Table for a batch: solved tasks with Wilson intervals, medians, limit hits and paired comparison (exact McNemar).
Usage: python3 local/batch_table.py results/local_deepinfra/l40"""
import glob, json, math, os, sys
from collections import defaultdict

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)

r = defaultdict(dict)
for f in glob.glob(os.path.join(sys.argv[1], '*__*.json')):
    v, t = os.path.basename(f)[:-5].split('__', 1)
    x = (json.load(open(f)).get('tareas') or [{}])[0]
    r[v][t] = (bool(x.get('resolved')), x.get('tool_calls') or 0, x.get('duration_s') or 0, x.get('error') or '')
med = lambda xs: sorted(xs)[len(xs) // 2]
print('| Variant | Solved | 95% CI | Calls (median) | Seconds (median) | Time limit hit | Turn limit hit |')
print('|---|---|---|---|---|---|---|')
for v in sorted(r, key=lambda v: -sum(a[0] for a in r[v].values())):
    a = list(r[v].values()); k = sum(x[0] for x in a); n = len(a); lo, hi = wilson(k, n)
    print(f'| {v} | {k}/{n} | {lo*100:.0f}-{hi*100:.0f} % | {med([x[1] for x in a])} | {med([x[2] for x in a]):.0f} | '
          f'{sum("timeout" in x[3] for x in a)} | {sum("turns" in x[3] for x in a)} |')
vs = sorted(r)
print()
for i, a in enumerate(vs):
    for b in vs[i + 1:]:
        com = set(r[a]) & set(r[b])
        sa = sum(r[a][t][0] and not r[b][t][0] for t in com); sb = sum(r[b][t][0] and not r[a][t][0] for t in com)
        print(f'{a} vs {b}: only {a} {sa}, only {b} {sb}, both {sum(r[a][t][0] and r[b][t][0] for t in com)}; exact McNemar p = {mcnemar(sa, sb):.3f}')
