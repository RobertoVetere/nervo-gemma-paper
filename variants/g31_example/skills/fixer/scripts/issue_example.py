"""Run the issue's own example code (the code decides, not the model).

Extracts runnable Python from .fixer/issue.txt: interactive sessions (>>> / ... lines) and ```python blocks
that look like code. Runs it on the current code with a timeout and returns the last error line, or 'OK'.
"""
import os
import re
import subprocess
import sys


def extract(issue):
    blocks = re.findall(r'```(?:python|py|pycon)?[ \t]*\n(.*?)```', issue, re.S)
    out = []
    for b in blocks:
        lines = b.split('\n')
        if any(l.lstrip().startswith('>>>') for l in lines):
            code = [re.sub(r'^\s*(>>>|\.\.\.) ?', '', l) for l in lines if re.match(r'^\s*(>>>|\.\.\.)', l)]
        elif re.search(r'^\s*(import |from \w+ import |\w+\s*=|print\()', b, re.M) \
                and not re.search(r'^\s*(\$ |Traceback|pip |\w+@)', b, re.M):
            code = lines
        else:
            continue
        out.append('\n'.join(code))
    return '\n\n'.join(out).strip()


def run(code, timeout=30):
    """'OK', or the last line of the error (e.g. 'TypeError: unhashable type: dict'), or None if it cannot run."""
    if not code:
        return None
    path = os.path.join('.fixer', '_issue_example.py')
    with open(path, 'w') as f:
        f.write(code + '\n')
    env = dict(os.environ, PYTHONPATH=os.getcwd() + os.pathsep + os.environ.get('PYTHONPATH', ''))
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    if r.returncode == 0:
        return 'OK'
    err = [l for l in r.stderr.strip().split('\n') if l.strip()]
    return err[-1][:300] if err else f'exit code {r.returncode}'
