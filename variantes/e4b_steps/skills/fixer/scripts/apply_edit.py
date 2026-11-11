"""APPLY_EDIT: apply SEARCH/REPLACE blocks to a file (tolerant to whitespace and indentation) and show the diff.

args: {"file": "pkg/module.py", "blocks": "<<<<<<< SEARCH\\n...\\n=======\\n...\\n>>>>>>> REPLACE"}
If a block does not match, nothing is changed and the closest lines are shown.
If the result does not compile, the file is restored.
"""
import argparse
import difflib
import os
import py_compile
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import go_to_repo, sh, source_files  # noqa: E402

BLOCK = re.compile(r'<{5,9} ?SEARCH[^\n]*\n(.*?)\n?={5,9}[^\n]*\n(.*?)\n?>{5,9} ?REPLACE', re.S)


def indent(line):
    return len(line) - len(line.lstrip())


def trim(lines):
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def replace(src, search, new):
    if src.count(search) == 1:
        return src.replace(search, new, 1), 'exact'
    lines = src.split('\n')
    s_lines = trim(search.split('\n'))
    if not s_lines:
        return None, 'empty SEARCH'
    stripped = [l.strip() for l in s_lines]
    found = [i for i in range(len(lines) - len(s_lines) + 1)
             if [l.strip() for l in lines[i:i + len(s_lines)]] == stripped]
    if len(found) != 1:
        return None, f'{len(found)} matches'
    i = found[0]
    delta = indent(lines[i]) - indent(s_lines[0])
    n_lines = [(' ' * max(0, indent(r) + delta) + r.lstrip()) if r.strip() else '' for r in trim(new.split('\n'))]
    return '\n'.join(lines[:i] + n_lines + lines[i + len(s_lines):]), 'whitespace-tolerant'


NUM = re.compile(r'^\s*\d+\| ?')


def strip_numbers(text):
    """The model sometimes copies the '  345| ' prefixes of show_function, even with literal \\n between lines."""
    if re.search(r'\\n\s*\d+\| ', text):
        text = re.sub(r'\\n(?=\s*\d+\| )', '\n', text)
    lines = text.split('\n')
    full = [l for l in lines if l.strip()]
    if full and all(NUM.match(l) for l in full):
        lines = [NUM.sub('', l, count=1) for l in lines]
    return '\n'.join(lines)


def find_file(blocks):
    """When "file" is missing: the only source file that contains the first SEARCH block."""
    found = BLOCK.findall(blocks.replace('\r\n', '\n'))
    if not found:
        return ''
    first = [l.strip() for l in strip_numbers(found[0][0]).split('\n') if l.strip()]
    if not first:
        return ''
    hits = []
    for f in source_files():
        try:
            text = [l.strip() for l in open(f, encoding='utf-8').read().split('\n')]
        except (OSError, UnicodeDecodeError):
            continue
        if any(text[i:i + len(first)] == first for i in range(len(text) - len(first) + 1)):
            hits.append(f)
    return hits[0] if len(hits) == 1 else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default='')
    ap.add_argument('--blocks', required=True)
    a = ap.parse_args()
    go_to_repo()
    if not a.file:
        a.file = find_file(a.blocks)
        if not a.file:
            print('ERROR: add "file" to args (the file to edit), e.g. {"file": "pkg/mod.py", "blocks": "..."}')
            return
    try:
        original = open(a.file, encoding='utf-8').read()
    except OSError as e:
        print(f'ERROR: {e}')
        return
    blocks = BLOCK.findall(a.blocks.replace('\r\n', '\n'))
    if not blocks:
        print('ERROR: no SEARCH/REPLACE blocks found. Format:\n<<<<<<< SEARCH\nexact lines\n=======\nnew lines\n>>>>>>> REPLACE')
        return
    src = original
    for n, (search, new) in enumerate(blocks, 1):
        search, new = strip_numbers(search), strip_numbers(new)
        result, mode = replace(src, search, new)
        if result is None:
            lines = src.split('\n')
            first = next((l for l in search.split('\n') if l.strip()), '')
            close = difflib.get_close_matches(first, lines, n=1, cutoff=0.5)
            hint = ''
            if close:
                i = lines.index(close[0])
                hint = '\nClosest place in the file:\n' + '\n'.join(
                    f'{j + 1:5}| {lines[j]}' for j in range(max(0, i - 3), min(len(lines), i + 8)))
            print(f'ERROR: block {n} not applied ({mode}). Nothing was changed.{hint}')
            return
        src = result
    open(a.file, 'w', encoding='utf-8').write(src)
    try:
        py_compile.compile(a.file, doraise=True)
    except py_compile.PyCompileError as e:
        open(a.file, 'w', encoding='utf-8').write(original)
        print(f'ERROR: the change does not compile, the file was restored:\n{str(e)[-800:]}')
        return
    _, diff = sh(f'git diff -- {a.file}')
    print(f'OK: {len(blocks)} block(s) applied to {a.file}.\n{diff[-3500:]}')


if __name__ == '__main__':
    main()
