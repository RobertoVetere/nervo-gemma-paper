#!/usr/bin/env python3
"""Interface A/B inside the agent (paper 4.3): format-rejected tool calls per agent, from the bridge log.

  python3 local/count_ab.py --from-log shim_ab.jsonl --out results/modal_e4b_4bit/ab_calls.jsonl   (extract)
  python3 local/count_ab.py results/modal_e4b_4bit/ab_calls.jsonl results/modal_e4b_4bit/ab        (count)
Agent: `steps` = every script through the three-field skill call (variants/e4b_steps); `cmd` = one skill call to
install, then one-field run_command (variants/e4b_cmd). Rejected = the tool result is a validation error.
"""
import glob, json, math, os, re, sys

FMT = re.compile(r'SKILL_NOT_FOUND|INVALID_ARGUMENTS|SCRIPT_NOT_FOUND|validation error|Field required|'
                 r'missing \d+ required|unexpected keyword')
if sys.argv[1] in ('--from-log', '--desde-log'):
    var, res = {}, {}
    for l in open(sys.argv[2]):
        x = json.loads(l); msgs = x['peticion'].get('messages') or []
        s = str(msgs[0].get('content'))[:3000] if msgs else ''
        v = 'cmd' if 'run_command' in s else ('steps' if 'run_skill_script' in s else '?')
        for ch in (x.get('answer') or {}).get('choices') or []:
            for tc in (ch.get('message') or {}).get('tool_calls') or []:
                var[tc['id']] = (v, tc['function']['name'])
        for m in msgs:
            if m.get('role') == 'tool':
                res[m.get('tool_call_id')] = str(m.get('content'))[:600]
    with open(sys.argv[4], 'w') as o:
        for k, c in res.items():
            v, name = var.get(k, ('?', '?'))
            o.write(json.dumps({'id': k, 'agent': v, 'tool': name, 'rejected': bool(FMT.search(c)), 'result': c[:200]}) + '\n')
    sys.exit()
rows = [json.loads(l) for l in open(sys.argv[1])]
for a in ('steps', 'cmd'):
    R = [r for r in rows if r['agent'] == a]
    print(f'{a:5}: {sum(r["rejected"] for r in R)} of {len(R)} tool calls rejected for format')
s = {}
for f in glob.glob(os.path.join(sys.argv[2], '*__*.json')):
    v, t = os.path.basename(f)[:-5].split('__', 1); s[(v, t)] = bool(json.load(open(f))['tasks'][0].get('resolved'))
T = sorted({t for _, t in s})
for v in ('e4b_steps', 'e4b_cmd'):
    print(f'{v}: solved {sum(s.get((v, t), False) for t in T)} of {len(T)}')
a = sum(s.get(('e4b_steps', t), False) and not s.get(('e4b_cmd', t), False) for t in T)
b = sum(s.get(('e4b_cmd', t), False) and not s.get(('e4b_steps', t), False) for t in T)
print(f'only three-field {a}, only one-field {b}')
