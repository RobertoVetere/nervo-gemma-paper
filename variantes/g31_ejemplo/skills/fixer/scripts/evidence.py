"""EVIDENCE: search the repository for what the issue mentions and show the code involved.

args: {"issue": "<the full issue text, verbatim>"}
  1. Traceback functions that exist in this repo (with their code).
  2. Issue strings (code, messages, names) found in the source code.
  3. Definitions of the names the issue mentions.
  4. Candidates ranked by evidence, and the code of the best one.
"""
import argparse
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import called_definitions, class_outline, definitions, enclosing_definition, enclosing_function, entry_points, go_to_repo, index_definitions, module_file, numbered, source_files  # noqa: E402

MAX_CHARS = 14000


def strings_to_search(issue):
    blocks = re.findall(r'```.*?```', issue, re.S)
    code = ' '.join(blocks)
    inline = ' '.join(re.findall(r'`([^`\n]+)`', issue))
    found = set(re.findall(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+', code + ' ' + inline))
    found |= set(re.findall(r'"([^"\n{}]{6,60})"', code)) | set(re.findall(r"'([^'\n{}]{6,60})'", code))
    found |= set(re.findall(r'(?:Error|Exception|Warning): ([^\n]{8,70})', issue))
    # Fixed parts of output messages: "undefined name 'a' in __all__" -> "undefined name", "in __all__"
    for block in blocks:
        for line in block.splitlines()[1:]:
            line = re.sub(r'^\S+:\d+(:\d+)?:?\s*', '', line.strip())
            for part in re.split(r"'[^']*'|\"[^\"]*\"|\b\d+\b", line):
                part = part.strip(' :,.()[]')
                if len(part) >= 8 and re.search(r'[a-z]{3}', part) and not part.startswith(('$', '>>>', '#')):
                    found.add(part)
    return sorted({s.strip() for s in found if len(s.strip()) >= 6 and 'site-packages' not in s}, key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--issue', default='')
    ap.add_argument('--issue-file', default='.fixer/issue.txt')
    a, extra = ap.parse_known_args()
    if not go_to_repo():
        print('ERROR: repository not found')
        return
    issue = a.issue or ' '.join(extra)
    if not issue and os.path.exists(a.issue_file):
        issue = open(a.issue_file, encoding='utf-8', errors='replace').read()
    if len(issue) < 20:
        print('ERROR: .fixer/issue.txt is missing or empty. Use the tool write_file with filepath '
              '.fixer/issue.txt and content = the full issue text, then run python3 .fixer/evidence.py again.')
        return
    files = source_files()
    cache = {}

    def load(f):
        if f not in cache:
            try:
                s = open(f, encoding='utf-8', errors='replace').read()
            except OSError:
                s = ''
            cache[f] = (s, s.splitlines(), definitions(s))
        return cache[f]

    out, score, shown, parts0 = [], Counter(), set(), []

    # 0. command run in the issue -> its entry point and the functions it calls (shortest first)
    eps = entry_points()
    cmds = re.findall(r'(?:^|\n)\s*[$%>]\s*(?:python\d?(?:\.\d+)?\s+-m\s+)?([A-Za-z][\w.-]*)', issue)
    cmds += re.findall(r'`(?:python\d?\s+-m\s+)?([A-Za-z][\w.-]*)\s+[^`]*`', issue)
    seen_cmd = set()
    for cmd in cmds:
        target = eps.get(cmd) or (f'{cmd}.__main__:main' if module_file(cmd + '.__main__', files) else None)
        if not target or cmd in seen_cmd:
            continue
        seen_cmd.add(cmd)
        mod, func = target.split(':')
        f = module_file(mod, files)
        if not f:
            continue
        _, lines, defs = load(f)
        d = next((d for d in defs if d[0] == func.split('.')[-1] or d[0] == func), None)
        if not d:
            continue
        score[(f, d[0])] += 1
        calls = called_definitions('\n'.join(lines[d[1] - 1:d[2]]), index_definitions(files), f, d[0], limit=10)
        text = (f'== 0. THE COMMAND `{cmd}` IN THE ISSUE RUNS {target} ({f}:{d[1]}) ==\n'
                'It calls these repository functions (shortest first, they are often the bridges where the bug is):\n')
        calls = sorted(calls, key=lambda c: c[3] - c[2])
        text += '\n'.join(f'- {q}  {cf}:{s0} ({e0 - s0 + 1} lines)' for cf, q, s0, e0, _ in calls)
        for cf, q, s0, e0, _ in calls[:2]:
            score[(cf, q)] += 2
            _, cl, _ = load(cf)
            text += f'\n### {cf} :: {q} (lines {s0}-{e0})\n' + numbered(cl, s0, 30)
        parts0.append(text)
    if parts0:
        out.append('\n\n'.join(parts0))

    # 1. traceback: identify each frame by the source line the traceback shows, not only by the name
    parts, outlines = [], []
    frames = re.findall(r'File "([^"]+)", line (\d+), in (\S+)\n[ \t]*([^\n]*)', issue)
    frames += [(p_, l_, n_, '') for p_, l_, n_ in re.findall(r'File "([^"]+)", line (\d+), in (\S+)', issue)
               if not any(p_ == f_[0] and l_ == f_[1] for f_ in frames)]
    for path, line_no, name, code_line in frames:
        path = path.replace('\\', '/')
        cands = [f for f in files if path.endswith('/' + f) or path == f]
        if not cands:
            continue
        f = max(cands, key=len)
        _, lines, defs = load(f)
        match = [d for d in defs if d[0].split('.')[-1] == name and not d[3]]
        if not match:
            continue
        code_line = code_line.strip()
        if code_line and len(match) > 1:
            with_line = [d for d in match if any(code_line in l for l in lines[d[1] - 1:d[2]])]
            match = with_line or match
        if len(match) > 1:
            match.sort(key=lambda d: abs(d[1] - int(line_no)))
        d = match[0]
        if (f, d[0]) in shown:
            continue
        shown.add((f, d[0]))
        score[(f, d[0])] += 2
        parts.append(f'### {f} :: {d[0]} (lines {d[1]}-{d[2]})\n' + numbered(lines, d[1], 35))
        if '.' in d[0] and len(outlines) < 3:
            cls = d[0].rsplit('.', 1)[0]
            c = next((c for c in defs if c[0] == cls and c[3]), None)
            if c and not any(cls in o for o in outlines):
                outlines.append(class_outline(f, cls, c[1], c[2]))
    if outlines:
        out.append('== 1b. CLASSES OF THE METHODS IN THE TRACEBACK (method signatures) ==\n' + '\n'.join(outlines))
    if parts:
        out.append('== 1. TRACEBACK FUNCTIONS FOUND IN THIS REPO (outermost first) ==\n' + '\n'.join(parts))

    # 2. issue strings in source
    hits, classes_hit = [], set()
    for s in strings_to_search(issue):
        n = 0
        for f in files:
            text, lines, defs = load(f)
            if s not in text:
                continue
            for i, l in enumerate(lines, 1):
                if s in l:
                    fn = enclosing_function(defs, i) or enclosing_definition(defs, i)
                    name = fn[0] if fn else '<module>'
                    if fn and fn[3] and re.search(r'[\'"][^\'"]*' + re.escape(s), l):
                        # issue text found inside a string of a class (e.g. a message class): follow its usages
                        classes_hit.add(fn[0].split('.')[-1])
                    score[(f, name)] += 1 if name != '<module>' else 0
                    hits.append(f'- `{s[:50]}` {f}:{i} in {name}: {l.strip()[:120]}')
                    n += 1
                    if n >= 4:
                        break
            if n >= 4:
                break
    if hits:
        out.append('== 2. ISSUE STRINGS FOUND IN SOURCE (file:line in function) ==\n' + '\n'.join(hits[:30]))
    uses = []
    for cls in sorted(classes_hit):
        pat = re.compile(r'\b' + re.escape(cls) + r'\b')
        for f in files:
            text, lines, defs = load(f)
            if cls not in text:
                continue
            for i, l in enumerate(lines, 1):
                if pat.search(l) and not re.match(r'\s*class ' + re.escape(cls) + r'\b', l):
                    fn = enclosing_function(defs, i)
                    if fn:
                        score[(f, fn[0])] += 2
                        uses.append(f'- {cls} used at {f}:{i} in {fn[0]}: {l.strip()[:120]}')
    if uses:
        out.append('== 2b. WHERE THE CLASSES ABOVE ARE USED ==\n' + '\n'.join(uses[:15]))

    # 3. definitions of mentioned names
    code = ' '.join(re.findall(r'```.*?```', issue, re.S)) + ' ' + ' '.join(re.findall(r'`([^`\n]+)`', issue))
    names = set(re.findall(r'\b([A-Za-z_]\w{2,})\s*\(', code))
    names |= {w for w in re.findall(r'\b[A-Za-z_]\w{3,}\b', ' '.join(re.findall(r'`([^`\n]+)`', issue)))
              if '_' in w or any(c.isupper() for c in w[1:])}
    defs_found = []
    for name in sorted(names):
        for f in files:
            _, _, defs = load(f)
            for d in defs:
                if d[0].split('.')[-1] == name:
                    defs_found.append(f'- {name}: {f}:{d[1]} ({"class" if d[3] else "def"} {d[0]})')
                    score[(f, d[0])] += 1
    if defs_found:
        out.append('== 3. DEFINITIONS OF NAMES MENTIONED IN THE ISSUE ==\n' + '\n'.join(defs_found[:25]))

    # 4. candidates
    score.pop(next((k for k in score if k[1] == '<module>'), None), None)
    score = Counter({k: v for k, v in score.items() if k[1] != '<module>' and v > 0})
    if score:
        top = [f'{i}. {f} :: {n}' for i, ((f, n), _) in enumerate(score.most_common(6), 1)]
        out.insert(0, '== CANDIDATES (most evidence first) ==\n' + '\n'.join(top))
        (f, n), _ = score.most_common(1)[0]
        if (f, n) not in shown and n != '<module>':
            _, lines, defs = load(f)
            d = next((d for d in defs if d[0] == n), None)
            if d:
                out.append(f'== CODE OF TOP CANDIDATE: {f} :: {n} ==\n' + numbered(lines, d[1], 70))
                calls = called_definitions('\n'.join(lines[d[1] - 1:d[2]]), index_definitions(files), f, n)
                if calls:
                    out.append('== REPOSITORY FUNCTIONS THE TOP CANDIDATE CALLS (the real behaviour is often there) ==\n'
                               + '\n'.join(f'- {q}  {cf}:{s0}' for cf, q, s0, _, _ in calls))
    else:
        out.append('No direct evidence found. Use run_command with grep -rn on key words of the issue '
                   '(exclude tests), then python3 .fixer/show_function.py.')
    text = '\n\n'.join(out)
    print(text[:MAX_CHARS] + ('\n...(truncated)' if len(text) > MAX_CHARS else ''))


if __name__ == '__main__':
    main()
    print('\nNEXT: if the code to change is above, write .fixer/edit.txt with write_file and run python3 .fixer/apply_edit.py --file <path>; '
          'otherwise run python3 .fixer/show_function.py --file <path> --name <Class.method>')
