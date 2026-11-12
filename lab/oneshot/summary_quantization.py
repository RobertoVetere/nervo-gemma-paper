#!/usr/bin/env python3
"""Sections 4.4-4.5: numbers of the single-call probes.

Quantization comparison, same vLLM 0.19.1 server and parser: chain3_bf16.jsonl / loc_bf16.jsonl (E4B, original bf16
weights) against chain3_quantized.jsonl / loc_quantized.jsonl (E4B, official w4a16 weights).
chain3.jsonl / loc.jsonl were requested as E4B from an API (DeepInfra) that served google/gemma-4-31B-it-turbo
instead (the E4B model there is marked replaced_by it); they are kept and labelled as such.
chain_function_quantized.jsonl: whole-function rewrite with the quantized E4B.
Usage: python3 lab/oneshot/summary_quantization.py
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


U, Q = load('chain3_bf16.jsonl'), load('chain3_quantized.jsonl')
API = load('chain3.jsonl')
for name, R in (('bf16 E4B', U), ('w4a16 E4B', Q), ('API (31B)', API)):
    s = {k: sum(bool(r[k]['resuelve']) for r in R) for k in K}
    mis = sum('no encaja' in str(r[k].get('motivo', '')) for r in R for k in K)
    tok = st.median(r[k]['tokens'] for r in R for k in ('e4b_t_A', 'e4b_t_C') if r[k].get('tokens'))
    print(f'{name:10} fix no-reasoning {s["e4b_A"]}/{len(R)} | with reasoning {s["e4b_t_A"]}/{len(R)} | '
          f'+tests {s["e4b_C"]}/{len(R)} | search mismatch {mis}/{4 * len(R)} | median tokens with reasoning {tok:.0f}')
su = {k: sum(bool(r[k]['resuelve']) for r in U) for k in K}; sq = {k: sum(bool(r[k]['resuelve']) for r in Q) for k in K}
mu = sum('no encaja' in str(r[k].get('motivo', '')) for r in U for k in K)
mq = sum('no encaja' in str(r[k].get('motivo', '')) for r in Q for k in K)
print(f'bf16 vs w4a16: search mismatch {mu}/88 vs {mq}/88, Fisher p = {fisher(mu, 88, mq, 88):.3f}; '
      f'reasoning {su["e4b_t_A"]}/22 vs {sq["e4b_t_A"]}/22, p = {fisher(su["e4b_t_A"], 22, sq["e4b_t_A"], 22):.2f}')
ku, kq = {(r['tarea'], r['muestra']): r for r in U}, {(r['tarea'], r['muestra']): r for r in Q}
same = [k for k in ku if k in kq and ku[k]['where'] == kq[k]['where'] and ku[k]['archivo'] == kq[k]['archivo']]
diff_tasks = {k[0] for k in ku if k not in same}
print(f'bf16 vs w4a16: same location in {len(same)} of {len(ku)} samples; located function differs in '
      f'{len(diff_tasks)} of {len({k[0] for k in ku})} tasks')
right = [r for r in Q if r['archivo_ok']]
print(f'quantized, right file: {sum(not r[k]["resuelve"] for r in right for k in K)} of {4 * len(right)} attempts fail')
for name, f in (('bf16 E4B', 'loc_bf16.jsonl'), ('w4a16 E4B', 'loc_quantized.jsonl'), ('API (31B)', 'loc.jsonl')):
    R = [r for r in load(f) if r['modelo'] == 'e4b']
    print(f'localization {name}: ' + ', '.join(f'{ {"lista": "file list", "mapa": "repo map"}[c]} symbol {sum(r["simbolo_ok"] in (True, 'True') for r in R if r["cond"] == c)}/'
                                              f'{sum(r["cond"] == c for r in R)}' for c in ('lista', 'mapa')))
F = load('chain_function_quantized.jsonl')
ok = [r for r in F if not r['e4b_F'].get('na')]
for c in ('e4b', 'e4b_t'):
    print(f'whole-function ({c}): rewrite {sum(r[c + "_F"]["resuelve"] for r in ok)} vs search/replace '
          f'{sum(r[c + "_A"]["resuelve"] for r in ok)} of {len(ok)}')
