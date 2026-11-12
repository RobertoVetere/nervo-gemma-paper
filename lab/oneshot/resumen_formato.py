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
def fails(key):
    v = g.get(key, []); return sum(not x['exact'] for x in v), len(v)


for f in sorted({k[2] for k in g}):
    for ctx in ('', '+ctx36k'):
        pairs = [(('modal', 'e4b-bf16' + ctx, f), ('modal', 'e4b' + ctx, f)),     # quantization, same server and parser
                 (('deepinfra', 'e4b' + ctx, f), ('modal', 'e4b' + ctx, f))]      # API (served by a 31B) vs quantized E4B
        for a, b in pairs:
            (fa, na), (fb, nb) = fails(a), fails(b)
            if na and nb:
                print(f'{f}{ctx}: {a[0]}/{a[1]} {fa}/{na} vs {b[0]}/{b[1]} {fb}/{nb} failures, Fisher p = '
                      f'{fisher(fa, na - fa, fb, nb - fb):.3f}')
    for m in ('e4b', 'e4b-bf16'):
        (fa, na), (fb, nb) = fails(('modal', m, f)), fails(('modal', m + '+ctx36k', f))
        if na and nb:
            print(f'{f}: context effect modal/{m}: {fa}/{na} -> {fb}/{nb}, Fisher p = {fisher(fa, na - fa, fb, nb - fb):.3f}')

# Paired, block-level test (avoids treating the two samples of a block as independent): a block fails if any sample
# lost fields with the nested interface; McNemar over the 80 blocks, 4-bit vs bf16 with long context.
by = defaultdict(dict)
for r in rows:
    if r['iface'] == 'three_field' and r['backend'] == 'modal':
        by[r['modelo']].setdefault(r['id'], False)
        by[r['modelo']][r['id']] |= bool(r['called'] and not r['args_ok'])
for ctx in ('', '+ctx36k'):
    q, b = by.get('e4b' + ctx), by.get('e4b-bf16' + ctx)
    if q and b:
        ids = sorted(set(q) & set(b))
        oq = sum(q[i] and not b[i] for i in ids); ob = sum(b[i] and not q[i] for i in ids); n = oq + ob
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(oq, ob) + 1)) / 2 ** n)
        print(f'blocks{ctx or " (short)"}: 4-bit {sum(q[i] for i in ids)}/{len(ids)} vs bf16 {sum(b[i] for i in ids)}/{len(ids)} '
              f'blocks with lost fields; discordant {oq} vs {ob}, McNemar p = {p:.3f}')
