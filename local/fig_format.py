#!/usr/bin/env python3
"""Figure 2: structural failures (of 320 calls: short + long context) per model and interface.
Usage: python3 local/fig_format.py out.png results/call_format/*.jsonl"""
import json, sys
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.argv, out, files = sys.argv, sys.argv[1], sys.argv[2:]
REQ = {'three_field': (('skill_name', 'file_path', 'args'), ('search', 'replace')),
       'edit_file': (('path', 'old_string', 'new_string'), ()), 'one_field': (('path', 'content'), ())}


def falla(r):
    if not r['called']:
        return True
    if r['args_ok']:
        return False
    try:
        a = json.loads(json.loads(r['raw'])['tool_calls'][0]['function']['arguments'] or '{}')
    except Exception:  # noqa: BLE001
        return True
    top, inner = REQ[r['iface']]
    if any(k not in a for k in top):
        return True
    x = a.get('args') if inner else {}
    if inner and isinstance(x, str):
        try:
            x = json.loads(x)
        except Exception:  # noqa: BLE001
            return True
    return bool(inner) and (not isinstance(x, dict) or any(k not in x for k in inner))


c = defaultdict(int)
for f in files:
    for l in open(f):
        r = json.loads(l)
        if r['backend'] == 'modal':
            c[(r['modelo'].replace('+ctx36k', ''), r['iface'])] += falla(r)
ORDEN = [('e4b-bf16', 'Gemma 4 E4B bf16'), ('e4b', 'Gemma 4 E4B 4-bit'), ('e2b-bf16', 'Gemma 4 E2B bf16'),
         ('e2b', 'Gemma 4 E2B 4-bit'), ('qwen3-4b-bf16', 'Qwen3-4B bf16'), ('qwen3-4b-awq', 'Qwen3-4B AWQ'),
         ('qwen3-1.7b-bf16', 'Qwen3-1.7B bf16')]
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=160)
w = 0.26
for j, (iface, lab, col) in enumerate((('three_field', 'Nested (args object)', '#d9480f'),
                                       ('edit_file', 'Flat, three fields', '#f59f00'), ('one_field', 'One field', '#2a6fdb'))):
    ax.bar([i + (j - 1) * w for i in range(len(ORDEN))], [c[(m, iface)] / 320 * 100 for m, _ in ORDEN], w, label=lab, color=col)
ax.set_xticks(range(len(ORDEN)), [n for _, n in ORDEN], rotation=25, ha='right', fontsize=8)
ax.set_ylabel('Calls failing structurally (%)'); ax.set_ylim(0, 80); ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False, fontsize=8); ax.set_title('Same edit, three interfaces, 320 calls per bar (short + long context)', fontsize=9)
fig.tight_layout(); fig.savefig(out)
print({k: v for k, v in c.items()})
