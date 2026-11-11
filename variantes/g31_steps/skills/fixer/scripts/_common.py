"""Shared helpers for the skill scripts (standard library only)."""
import ast
import os
import re
import subprocess

ENV = dict(os.environ, GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='safe.directory', GIT_CONFIG_VALUE_0='*')
NON_SOURCE = re.compile(r'(^|/)(\w+_)?(tests?|testing|samples?|docs?|examples?|benchmarks?|demos?|tutorials?|vendor(?:ed)?|_vendor)/'
                        r'|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)setup\.py$')
NOT_CALLS = {'print', 'len', 'isinstance', 'issubclass', 'str', 'int', 'dict', 'list', 'set', 'tuple', 'super',
             'getattr', 'setattr', 'hasattr', 'type', 'range', 'enumerate', 'zip', 'sorted', 'min', 'max', 'repr',
             'bool', 'any', 'all', 'iter', 'next', 'open', 'format', 'join', 'get', 'update', 'append', 'pop',
             'items', 'keys', 'values', 'split', 'strip', 'replace', 'startswith', 'endswith'}


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=ENV)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, f'(timeout after {timeout}s)'


def go_to_repo():
    """ADK runs skill scripts after chdir to a temp folder. The task repo is /workspace (Docker)
    or is on PYTHONPATH (subprocess sandbox)."""
    cands = [p for p in os.environ.get('PYTHONPATH', '').split(os.pathsep) if p]
    cands += ['/workspace', os.environ.get('PWD', ''), os.getcwd()]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, '.git')):
            os.chdir(c)
            return c
    return None


def source_files():
    _, out = sh('git ls-files "*.py"')
    return [f for f in out.split() if f.endswith('.py') and not NON_SOURCE.search(f)]


def definitions(src):
    """[(qualified_name, start, end, is_class)] for every function, method and class."""
    out = []

    def walk(node, prefix):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append((prefix + n.name, n.lineno, n.end_lineno, False))
                walk(n, prefix + n.name + '.')
            elif isinstance(n, ast.ClassDef):
                out.append((prefix + n.name, n.lineno, n.end_lineno, True))
                walk(n, prefix + n.name + '.')
    try:
        walk(ast.parse(src), '')
    except SyntaxError:
        pass
    return out


def enclosing_function(defs, line):
    inside = [d for d in defs if d[1] <= line <= d[2] and not d[3]]
    return min(inside, key=lambda d: d[2] - d[1]) if inside else None


def enclosing_definition(defs, line):
    """Smallest function OR class around a line."""
    inside = [d for d in defs if d[1] <= line <= d[2]]
    return min(inside, key=lambda d: d[2] - d[1]) if inside else None


def common_prefix(a, b):
    n = 0
    for x, y in zip(a.split('/'), b.split('/')):
        if x != y:
            break
        n += 1
    return n


def numbered(lines, start, limit=90):
    sel = lines[start - 1:start - 1 + limit]
    text = '\n'.join(f'{start + i:5}| {l}' for i, l in enumerate(sel))
    if len(lines) - (start - 1) > limit:
        text += '\n      ... (truncated; use scripts/show_function.py to see more)'
    return text


def tail(text, n):
    text = text.strip()
    return text if len(text) <= n else '...' + text[-n:]


def index_definitions(files):
    """{short_name: [(file, qualified_name, start, end, is_class)]} for all source files."""
    index = {}
    for f in files:
        try:
            src = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for d in definitions(src):
            index.setdefault(d[0].split('.')[-1], []).append((f, d[0], d[1], d[2], d[3]))
    return index


def called_definitions(code, index, own_file, own_name, limit=6):
    """Repository functions called inside `code` (same file first), excluding the function itself."""
    names = []
    for n in re.findall(r'\b([A-Za-z_]\w*)\s*\(', code):
        if n not in names and n not in NOT_CALLS and n != own_name.split('.')[-1] and n in index:
            names.append(n)
    out = []
    for n in names:
        cands = [c for c in index[n] if not c[4]] or index[n]
        cands.sort(key=lambda c: (c[0] != own_file, -common_prefix(c[0], own_file), c[3] - c[2] > 400))
        out.append(cands[0])
        if len(out) >= limit:
            break
    return out


def entry_points():
    """{command: 'module:function'} from setup.py, setup.cfg and pyproject.toml."""
    found = {}
    for f in ('setup.py', 'setup.cfg', 'pyproject.toml'):
        try:
            text = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for name, target in re.findall(r'["\']?([A-Za-z0-9_.-]+)["\']?\s*=\s*["\']?([A-Za-z_][\w.]*:[A-Za-z_][\w.]*)', text):
            found.setdefault(name, target)
    return found


def module_file(module, files):
    rel = module.replace('.', '/')
    for cand in (rel + '.py', rel + '/__init__.py', rel + '/__main__.py'):
        for f in files:
            if f == cand or f.endswith('/' + cand) and f.startswith('src/'):
                return f
    return None


def class_outline(path, qualified, start, end, limit=25):
    """Method signatures of a class."""
    try:
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    except OSError:
        return ''
    sig = [f'{i + 1:5}| {lines[i].strip()}' for i in range(start - 1, end)
           if re.match(r'\s*(async\s+)?def\s', lines[i])]
    return f'### {path} :: class {qualified} (lines {start}-{end}), methods:\n' + '\n'.join(sig[:limit])
