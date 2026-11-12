#!/usr/bin/env python3
"""Summary of the tool-call format experiment (call_format.py).
Usage: python3 -I summary_format.py res1.jsonl res2.jsonl ..."""
import json, math, sys
from collections import defaultdict


def fisher(a, b, c, d):  # two-sided exact test on [[a, b], [c, d]]
    n = a + b + c + d; r1, c1 = a + b, a + c
    p = lambda x: math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


def etiqueta(b_, m):  # readable label; DeepInfra answers requests for E4B with a 31B (see Section 4.6 of the paper)
    base, ctx = m.replace('+ctx36k', ''), ('+ctx36k' if '+ctx36k' in m else '')
    if b_ == 'deepinfra':
        return '31B (API; asked for e4b)' + ctx
    nombres = {'e4b': 'e4b 4-bit', 'e2b': 'e2b 4-bit', 'qwen3-4b-awq': 'qwen3-4b AWQ 4-bit'}
    return nombres.get(base, base) + ctx


rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
g = defaultdict(list)
for r in rows:
    g[(r['backend'], r['modelo'], r['iface'])].append(r)
print('Model labels: e4b, e2b = official 4-bit (QAT w4a16) weights on our vLLM server; -bf16 = original weights; "31B (API; asked for e4b)" = DeepInfra, which served a 31B for E4B requests.\n')
print('| Backend | Model | Interface | Calls | Not called | Fields lost / unparsable | Text not exact | Exact |')
print('|---|---|---|---|---|---|---|---|')
for k in sorted(g):
    v = g[k]; n = len(v)
    nc = sum(not x['called'] for x in v); bad = sum(x['called'] and not x['args_ok'] for x in v)
    ne = sum(x['args_ok'] and not x['exact'] for x in v); ex = sum(x['exact'] for x in v)
    print(f'| {k[0]} | {etiqueta(k[0], k[1])} | {k[2]} | {n} | {nc} | {bad} | {ne} | {ex} ({100*ex/n:.0f}%) |')
print()
for k in sorted(g):
    v = g[k]
    q = [x for x in v if x['ends_quote']]; o = [x for x in v if not x['ends_quote']]
    fq = sum(not x['exact'] for x in q); fo = sum(not x['exact'] for x in o)
    print(f'{etiqueta(k[0], k[1])} {k[2]}: failures ending in quote {fq}/{len(q)}, other {fo}/{len(o)}, Fisher p = {fisher(fq, len(q)-fq, fo, len(o)-fo):.3f}')
print()
PARES = [('e4b-bf16', 'e4b'), ('e2b-bf16', 'e2b'), ('qwen3-4b-bf16', 'qwen3-4b-awq')]  # (original, 4-bit)


def fails(key):
    v = g.get(key, []); return sum(not x['exact'] for x in v), len(v)


for f in sorted({k[2] for k in g}):
    for ctx in ('', '+ctx36k'):
        pairs = [(('modal', o + ctx, f), ('modal', q + ctx, f)) for o, q in PARES]   # original vs 4-bit, same server
        pairs += [(('deepinfra', 'e4b' + ctx, f), ('modal', 'e4b' + ctx, f))]      # API (served by a 31B) vs 4-bit E4B
        for a, b in pairs:
            (fa, na), (fb, nb) = fails(a), fails(b)
            if na and nb:
                print(f'{f}{ctx}: {etiqueta(*a[:2])} {fa}/{na} vs {etiqueta(*b[:2])} {fb}/{nb} failures, Fisher p = '
                      f'{fisher(fa, na - fa, fb, nb - fb):.3f}')
    for m in sorted({k[1].replace('+ctx36k', '') for k in g if k[0] == 'modal'}):
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
for (orig, cuant), ctx in [(p_, c_) for p_ in PARES for c_ in ('', '+ctx36k')]:
    q, b = by.get(cuant + ctx), by.get(orig + ctx)
    if q and b:
        ids = sorted(set(q) & set(b))
        oq = sum(q[i] and not b[i] for i in ids); ob = sum(b[i] and not q[i] for i in ids); n = oq + ob
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(oq, ob) + 1)) / 2 ** n)
        print(f'{cuant} vs {orig}, blocks{ctx or " (short)"}: 4-bit {sum(q[i] for i in ids)}/{len(ids)} vs bf16 {sum(b[i] for i in ids)}/{len(ids)} '
              f'blocks with lost fields; discordant {oq} vs {ob}, McNemar p = {p:.3f}')


print('\nLost fields (called but required fields missing), nested / flat / one field, per model and context:')
for m in sorted({k[1] for k in g}, key=lambda x: (x.replace('+ctx36k', ''), x)):
    for b_ in sorted({k[0] for k in g if k[1] == m}):
        cells = []
        for f in ('three_field', 'edit_file', 'one_field'):
            v = g.get((b_, m, f), [])
            cells.append(f"{sum(x['called'] and not x['args_ok'] for x in v)}/{len(v)}")
        print(f'  {etiqueta(b_, m):34} ' + '  '.join(cells))


# Re-scoring from the raw message: separate a structurally lost field (a required key absent, or arguments that do
# not parse) from content that ignores the requested layout (e.g. a write_file content without SEARCH/REPLACE markers).
REQ = {'three_field': (('skill_name', 'file_path', 'args'), ('search', 'replace')), 'edit_file': (('path', 'old_string', 'new_string'), ()),
       'one_field': (('path', 'content'), ())}


def clase_fallo(r):
    if not r['called'] or r['args_ok']:
        return None
    try:
        a = json.loads(json.loads(r['raw'])['tool_calls'][0]['function']['arguments'] or '{}')
    except Exception:  # noqa: BLE001
        return 'lost'
    top, inner = REQ[r['iface']]
    if any(k not in a for k in top):
        return 'lost'
    if inner:
        x = a.get('args')
        if isinstance(x, str):
            try:
                x = json.loads(x)
            except Exception:  # noqa: BLE001
                return 'lost'
        if not isinstance(x, dict) or any(k not in x for k in inner):
            return 'lost'
    return 'layout'


print('\nRe-scored: calls with a LOST field (layout errors in brackets), nested / flat / one field:')
for m in sorted({k[1] for k in g}, key=lambda x: (x.replace('+ctx36k', ''), x)):
    for b_ in sorted({k[0] for k in g if k[1] == m}):
        cells = []
        for f in ('three_field', 'edit_file', 'one_field'):
            v = g.get((b_, m, f), []); c = [clase_fallo(x) for x in v]
            cells.append(f"{c.count('lost')}/{len(v)} ({c.count('layout')})")
        print(f'  {etiqueta(b_, m):34} ' + '  '.join(cells))


# Structural failure = the call never runs (no parsed tool call; usually written as text the parser could not extract)
# or a required field is lost. Layout errors in a well-formed call (no SEARCH/REPLACE markers) are not counted.
def fallo_estructural(r):
    return (not r['called']) or clase_fallo(r) == 'lost'


print('\nStructural failures (not executed + lost field), nested / flat / one field, per model and context:')
for m in sorted({k[1] for k in g}, key=lambda x: (x.replace('+ctx36k', ''), x)):
    for b_ in sorted({k[0] for k in g if k[1] == m}):
        cells = []
        for f in ('three_field', 'edit_file', 'one_field'):
            v = g.get((b_, m, f), [])
            cells.append(f"{sum(fallo_estructural(x) for x in v)}/{len(v)} ({sum(not x['called'] for x in v)} not run)")
        print(f'  {etiqueta(b_, m):34} ' + '  '.join(cells))


# One field against each multi-field interface, paired by block (a block fails if any of its samples failed
# structurally); McNemar per model, pooling short and long context as separate blocks.
print('\nOne field vs multi-field, block-level McNemar per model (short and long context pooled; e4b, e2b = 4-bit; Modal only):')
modelos = sorted({k[1].replace('+ctx36k', '') for k in g if k[0] == 'modal'})
for m in modelos:
    res = []
    for otra in ('three_field', 'edit_file'):
        a_ = b_ = 0; nb = 0
        for ctx in ('', '+ctx36k'):
            blk = defaultdict(lambda: [False, False])
            for x in g.get(('modal', m + ctx, 'one_field'), []):
                blk[x['id']][0] |= fallo_estructural(x)
            for x in g.get(('modal', m + ctx, otra), []):
                blk[x['id']][1] |= fallo_estructural(x)
            nb += len(blk)
            a_ += sum(1 for u, w in blk.values() if u and not w); b_ += sum(1 for u, w in blk.values() if w and not u)
        n = a_ + b_
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(a_, b_) + 1)) / 2 ** n)
        res.append(f'vs {otra}: one field worse in {a_}, better in {b_} blocks (p = {p:.2g})')
    print(f'  {m:16} ' + '; '.join(res))


print('\n4-bit vs original weights, structural failures of the nested call, block-level McNemar:')
for orig, cuant in PARES:
    for ctx in ('', '+ctx36k'):
        q_ = defaultdict(bool); o_ = defaultdict(bool)
        for x in g.get(('modal', cuant + ctx, 'three_field'), []):
            q_[x['id']] |= fallo_estructural(x)
        for x in g.get(('modal', orig + ctx, 'three_field'), []):
            o_[x['id']] |= fallo_estructural(x)
        ids = sorted(set(q_) & set(o_))
        if not ids:
            continue
        a_ = sum(q_[i] and not o_[i] for i in ids); b_ = sum(o_[i] and not q_[i] for i in ids); n = a_ + b_
        p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(a_, b_) + 1)) / 2 ** n)
        print(f'  {cuant} vs {orig}{ctx or " (short)"}: blocks failing {sum(q_[i] for i in ids)} vs {sum(o_[i] for i in ids)} of {len(ids)}; '
              f'discordant {a_} vs {b_}, p = {p:.3g}')
