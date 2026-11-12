#!/usr/bin/env python3
"""Figure 1: 2x2 over three replicas (mean line, one dot per replica).
Usage: python3 local/fig_replicas.py out.png results/local_deepinfra/l40 .../l40_r2 .../l40_r3"""
import glob, json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out, dirs = sys.argv[1], sys.argv[2:]
CELLS = {('Free-form agent (edit_file)', 0): 'e4b_t0', ('Free-form agent (edit_file)', 1): 'community_base',
         ('fixer (scripts, one-field calls)', 0): 'e4b_cmd', ('fixer (scripts, one-field calls)', 1): 'e4b_cmd_t'}
COL = {'Free-form agent (edit_file)': '#2a6fdb', 'fixer (scripts, one-field calls)': '#d9480f'}
MRK = {'Free-form agent (edit_file)': 'o', 'fixer (scripts, one-field calls)': 's'}


def solved(d, v):
    return sum(int(bool((json.load(open(f)).get('tasks') or [{}])[0].get('resolved')))
               for f in glob.glob(os.path.join(d, v + '__*.json')))


vals = {k: [solved(d, v) for d in dirs] for k, v in CELLS.items()}
fig, ax = plt.subplots(figsize=(6, 4.2), dpi=160)
for agent in COL:
    m = [sum(vals[(agent, x)]) / len(dirs) for x in (0, 1)]
    ax.plot([0, 1], m, color=COL[agent], marker=MRK[agent], lw=2.2, ms=8, label=agent)
    for x in (0, 1):
        ax.scatter([x + (0.03 if MRK[agent] == 's' else -0.03)] * len(dirs), vals[(agent, x)], color=COL[agent],
                   alpha=0.35, s=22, marker=MRK[agent])
        ax.annotate(f'{m[x]:.1f}', (x, m[x]), xytext=(12 if x else -34, -4), textcoords='offset points',
                    color=COL[agent], fontsize=10)
ax.set_xticks([0, 1], ['No reasoning', 'Reasoning (4,096)']); ax.set_xlim(-0.35, 1.35); ax.set_ylim(0, 24)
ax.set_ylabel('Solved tasks (of 40)'); ax.spines[['top', 'right']].set_visible(False)
ax.set_title(f'31B (API), 40 random tasks, {len(dirs)} replicas (line = mean, dots = replicas)', fontsize=10)
ax.legend(frameon=False, loc='lower left', fontsize=9)
fig.tight_layout(); fig.savefig(out)
print({f'{a[:8]}|{x}': v for (a, x), v in vals.items()})
