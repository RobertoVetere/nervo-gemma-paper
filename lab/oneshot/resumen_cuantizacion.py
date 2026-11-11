#!/usr/bin/env python3
"""Section 4.3-4.4: numbers of the single-call probes (unquantized vs quantized E4B).

Reads lab/oneshot/cadena3.jsonl (unquantized, API), cadena3_cuantizado.jsonl (quantized, vLLM 0.19.1),
loc.jsonl / loc_cuantizado.jsonl (localization) and cadena_funcion_cuantizado.jsonl (whole-function rewrite).
Usage: python3 lab/oneshot/resumen_cuantizacion.py
"""
import json, os, statistics as st
from math import comb

H = os.path.dirname(os.path.abspath(__file__))
K = ['e4b_A', 'e4b_C', 'e4b_t_A', 'e4b_t_C']
load = lambda f: [json.loads(l) for l in open(os.path.join(H, f))]


def fisher(a, n1, b, n2):
    N, T = n1 + n2, a + b
    pr = lambda x: comb(n1, x) * comb(n2, T - x) / comb(N, T)
    p0 = pr(a)
    return sum(pr(x) for x in range(max(0, T - n2), min(n1, T) + 1) if pr(x) <= p0 + 1e-12)


U, Q = load('cadena3.jsonl'), load('cadena3_cuantizado.jsonl')
for name, R in (('unquantized', U), ('quantized', Q)):
    s = {k: sum(bool(r[k]['resuelve']) for r in R) for k in K}
    mis = sum('no encaja' in str(r[k].get('motivo', '')) for r in R for k in K)
    tok = st.median(r[k]['tokens'] for r in R for k in ('e4b_t_A', 'e4b_t_C') if r[k].get('tokens'))
    print(f'{name:12} fix no-reasoning {s["e4b_A"]}/{len(R)} | with reasoning {s["e4b_t_A"]}/{len(R)} | '
          f'+tests {s["e4b_C"]}/{len(R)} | search mismatch {mis}/{4 * len(R)} | median tokens with reasoning {tok:.0f}')
mu = sum('no encaja' in str(r[k].get('motivo', '')) for r in U for k in K)
mq = sum('no encaja' in str(r[k].get('motivo', '')) for r in Q for k in K)
print(f'search mismatch Fisher p = {fisher(mu, 88, mq, 88):.3f}; reasoning 9/22 vs 5/22 p = {fisher(9, 22, 5, 22):.2f}')
ku, kq = {(r['tarea'], r['muestra']): r for r in U}, {(r['tarea'], r['muestra']): r for r in Q}
same = [k for k in ku if k in kq and ku[k]['where'] == kq[k]['where'] and ku[k]['archivo'] == kq[k]['archivo']]
diff_tasks = {k[0] for k in ku if k not in same}
print(f'same location in {len(same)} of {len(ku)} samples; located function differs in {len(diff_tasks)} of '
      f'{len({k[0] for k in ku})} tasks')
for k in K:
    print(f'  same-location samples, {k}: unquantized {sum(bool(ku[x][k]["resuelve"]) for x in same)}, '
          f'quantized {sum(bool(kq[x][k]["resuelve"]) for x in same)}')
right = [r for r in Q if r['archivo_ok']]
print(f'quantized, right file: {sum(not r[k]["resuelve"] for r in right for k in K)} of {4 * len(right)} attempts fail')
for name, f in (('unquantized', 'loc.jsonl'), ('quantized', 'loc_cuantizado.jsonl')):
    R = [r for r in load(f) if r['modelo'] == 'e4b']
    print(f'localization {name}: ' + ', '.join(f'{c} symbol {sum(r["simbolo_ok"] for r in R if r["cond"] == c)}/'
                                              f'{sum(r["cond"] == c for r in R)}' for c in ('lista', 'mapa')))
F = load('cadena_funcion_cuantizado.jsonl')
ok = [r for r in F if not r['e4b_F'].get('na')]
for c in ('e4b', 'e4b_t'):
    print(f'whole-function ({c}): rewrite {sum(r[c + "_F"]["resuelve"] for r in ok)} vs search/replace '
          f'{sum(r[c + "_A"]["resuelve"] for r in ok)} of {len(ok)}')
