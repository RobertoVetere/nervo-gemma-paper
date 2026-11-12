"""Count tool calls rejected for format in the evaluation traces (Kaggle output artifacts).

Usage: python3 -I results/format_agents/count_format.py <folder_with_one_subfolder_per_run>
Broken format = the call is rejected by validation (SKILL_NOT_FOUND, INVALID_ARGUMENTS, SCRIPT_NOT_FOUND,
argument validation errors). Failed edit = the change was not applied (FileEditError, block not applied).
Prints per run: folder, tasks, calls, rejected for format, failed edits.
"""
import glob
import json
import re
import sys

FMT = re.compile(r'SKILL_NOT_FOUND|INVALID_ARGUMENTS|SCRIPT_NOT_FOUND|validation error|Field required|'
                 r'missing \d+ required|unexpected keyword')
EDIT = re.compile(r'FileEditError|not applied \(|old_string not found')
base = sys.argv[1]
for run in sorted(glob.glob(f'{base}/*/')):
    calls = fmt = ed = tasks = 0
    for f in glob.glob(f'{run}results/*/traces/trace_*.json'):
        tasks += 1
        for s in json.load(open(f))['steps']:
            for c in s.get('tool_calls') or []:
                calls += 1
                o = s.get('observation')
                o = o.get('content', '') if isinstance(o, dict) else str(o)
                if FMT.search(o[:600]):
                    fmt += 1
                elif EDIT.search(o[:600]):
                    ed += 1
    print(run, tasks, calls, fmt, ed)
