#!/usr/bin/env python3
"""2x2 (agent x reasoning) over several replicas of the same 40 tasks.
Usage: python3 -I local/replica_table.py results/local_deepinfra/l40 results/local_deepinfra/l40_r2 ...
Cells: community_base (free-form, reasoning), e4b_t0 (free-form, no reasoning), e4b_cmd_t (fixer, reasoning),
e4b_cmd (fixer, no reasoning). Interaction per task and replica: (pub_t - pub_0) - (fix_t - fix_0)."""
import glob, json, math, os, sys

CELLS = {'pub_t': 'community_base', 'pub_0': 'e4b_t0', 'fix_t': 'e4b_cmd_t', 'fix_0': 'e4b_cmd'}


def sign_p(pos, neg):
    n = pos + neg
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(pos, neg) + 1)) / 2 ** n)


reps = []
for d in sys.argv[1:]:
    r = {}
    for f in glob.glob(os.path.join(d, '*__*.json')):
        v, t = os.path.basename(f)[:-5].split('__', 1)
        x = (json.load(open(f)).get('tasks') or [{}])[0]
        r[(v, t)] = int(bool(x.get('resolved')))
    reps.append(r)
tasks = sorted({t for r in reps for (_, t) in r})
print('| Replica | ' + ' | '.join(CELLS) + ' | interaction + / - | sign p |')
print('|---|---|---|---|---|---|---|')
tot = {t: 0 for t in tasks}
for i, r in enumerate(reps):
    cnt = {c: sum(r.get((v, t), 0) for t in tasks) for c, v in CELLS.items()}
    miss = [(v, t) for v in CELLS.values() for t in tasks if (v, t) not in r]
    inter = {t: (r.get((CELLS['pub_t'], t), 0) - r.get((CELLS['pub_0'], t), 0))
             - (r.get((CELLS['fix_t'], t), 0) - r.get((CELLS['fix_0'], t), 0)) for t in tasks}
    for t in tasks:
        tot[t] += inter[t]
    pos = sum(x > 0 for x in inter.values()); neg = sum(x < 0 for x in inter.values())
    print(f'| {os.path.basename(sys.argv[1 + i].rstrip("/"))} | ' + ' | '.join(str(cnt[c]) for c in CELLS)
          + f' | {pos} / {neg} | {sign_p(pos, neg):.3g} |' + (f' (missing {len(miss)})' if miss else ''))
mean = {c: sum(sum(r.get((v, t), 0) for t in tasks) for r in reps) / len(reps) for c, v in CELLS.items()}
print('\nMean solved per cell: ' + ', '.join(f'{c} {m:.1f}' for c, m in mean.items()))
pos = sum(x > 0 for x in tot.values()); neg = sum(x < 0 for x in tot.values())
print(f'Pooled over replicas, per task: interaction positive in {pos} tasks, negative in {neg} (sign test p = {sign_p(pos, neg):.3g})')
for a, b in (('pub_t', 'pub_0'), ('fix_t', 'fix_0')):
    d = {t: sum(r.get((CELLS[a], t), 0) - r.get((CELLS[b], t), 0) for r in reps) for t in tasks}
    p_, n_ = sum(x > 0 for x in d.values()), sum(x < 0 for x in d.values())
    print(f'Reasoning effect {a} vs {b}: tasks better {p_}, worse {n_} (sign p = {sign_p(p_, n_):.3g})')
