"""VERIFY: hard validation. The code decides whether the patch is ready, not the model.

Checks, in order:
  1. a source file changed (otherwise NO_EDIT);
  2. tests and config are untouched and there are no scratch files in the repo;
  3. changed .py files compile;
  4. the reproduction script /tmp/check.py, if present (it must print CHECK_PASS or CHECK_FAIL);
  5. one related test file (or --test), with -x.
Ends with VERDICT: SUBMIT | FIX | NO_EDIT and the next action.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import go_to_repo, sh, tail  # noqa: E402

TEST_RE = re.compile(r'(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$')
CONFIG = {'pytest.ini', 'pyproject.toml', 'setup.cfg', 'tox.ini', 'sitecustomize.py', 'setup.py'}
HARNESS_FILES = {'pytest.ini', 'conftest.py'}
SCRATCH = re.compile(r'(^|/)(repro|reproduce|check|debug|scratch|tmp|temp|try|example)[^/]*\.py$|(^|/)[^/]+\.(log|txt|out)$', re.I)


def check_script():
    """The model's /tmp is TMPDIR in the subprocess sandbox and /tmp in Docker."""
    if os.path.isfile('.fixer/check.py'):
        return os.path.abspath('.fixer/check.py')
    for d in (os.environ.get('TMPDIR', ''), '/tmp'):
        if d and os.path.isfile(os.path.join(d, 'check.py')):
            return os.path.join(d, 'check.py')
    return None


def changes():
    rc, out = sh('git status --porcelain --untracked-files=all')
    if rc != 0:
        raise RuntimeError(f'git status failed: {tail(out, 300)}')
    modified, new = [], []
    for line in out.splitlines():
        if len(line) < 4 or not re.match(r'^[ MADRCU?!]{2} ', line):
            continue
        state, path = line[:2], line[3:].strip().strip('"')
        if ' -> ' in path:
            path = path.split(' -> ')[-1]
        if path.startswith('.adk_exec_') or '__pycache__' in path or path.endswith('.pyc'):
            continue
        if path in HARNESS_FILES:  # written by the harness itself; the grader ignores them
            continue
        (new if state == '??' else modified).append(path)
    return modified, new


def related_test(sources):
    for f in sources:
        base = os.path.splitext(os.path.basename(f))[0].lstrip('_')
        _, out = sh(f"git ls-files | grep -E '(^|/)tests?/.*test_{re.escape(base)}[^/]*\\.py$' | head -3")
        cands = [c for c in out.split() if c]
        if cands:
            return cands[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', default='', help='test file to run (optional)')
    ap.add_argument('-k', '--keyword', default='', help='pytest -k filter (optional)')
    a, _ = ap.parse_known_args()
    if go_to_repo() is None:
        print('VERDICT: ERROR')
        print('NEXT: repository not found; call submit_patch if you already applied your fix.')
        return
    try:
        modified, new = changes()
    except RuntimeError as e:
        print('VERDICT: ERROR', e)
        print('NEXT: call submit_patch if apply_edit.py printed OK.')
        return
    problems, warnings = [], []
    touched_tests = [f for f in modified + new if TEST_RE.search(f)]
    touched_config = [f for f in modified + new if os.path.basename(f) in CONFIG]
    if touched_tests:
        warnings.append(f'Test files changed (the grader discards them): {touched_tests}. Revert: git checkout -- <file>')
    if touched_config:
        problems.append(f'Config files changed: {touched_config}. Revert: git checkout -- <file>')
    scratch = [f for f in new if SCRATCH.search(f) or not f.endswith('.py')]
    if scratch:
        problems.append(f'Scratch files in the repo will enter the patch: {scratch}. Delete them with rm.')
    sources = [f for f in modified + new if f.endswith('.py') and not TEST_RE.search(f)
               and os.path.basename(f) not in CONFIG and f not in scratch]

    print('CHANGED SOURCE FILES:', sources or 'none')
    if not sources:
        print('VERDICT: NO_EDIT')
        print('NEXT: no source file changed. Write .fixer/edit.txt with write_file and run python3 .fixer/apply_edit.py --file <path> now; '
              'an unchanged repository always scores zero.')
        return
    for f in sources:
        if os.path.exists(f):
            rc, out = sh(f'{sys.executable} -m py_compile {f!r}')
            if rc != 0:
                problems.append(f'Syntax error in {f}:\n{tail(out, 600)}')
    _, diff = sh('git diff --stat')
    print('DIFF:', tail(diff, 400))

    check = None
    path = check_script()
    if path and 'CASE' not in open(path, encoding='utf-8', errors='replace').read():
        print('CHECK SCRIPT: .fixer/check.py has no CASE lines (it tests nothing)')
        path = None
    if path:
        rc, out = sh(f'PYTHONPATH="$PWD:$PYTHONPATH" {sys.executable} {path!r}', timeout=120)
        if 'CHECK_PASS' in out and 'CHECK_FAIL' not in out:
            check = True
        elif 'CHECK_FAIL' in out:
            check = False
        wrong = [l for l in out.splitlines() if 'WRONG' in l]
        if wrong:
            check = False
        print(f'CHECK SCRIPT (.fixer/check.py): {"PASS" if check else "FAIL" if check is False else "no verdict"}')
        if wrong:
            print(f'WRONG CASES ({len(wrong)}), real results from running your cases:')
            print('\n'.join(wrong[:30]))
        elif check is not True:
            print(tail(out, 900))
            if check is None:
                check = False
                problems.append('The cases script printed neither CHECK_PASS nor CHECK_FAIL (it crashed?). '
                                'Fix .fixer/check.py with write_file, then run python3 .fixer/verify.py again.')
    else:
        print('CHECK SCRIPT: .fixer/check.py does not exist')
        marker = '.fixer/.asked_check'
        if not os.path.exists(marker):
            open(marker, 'w').close()
            print('VERDICT: FIX')
            print('NEXT: you skipped STEP 4. Use the tool write_file with filepath .fixer/check.py and content = '
                  'your cases script (CASE lines), then run_command with: python3 .fixer/verify.py')
            return

    test = a.test or related_test(sources)
    tests_ok = None
    if test and os.path.exists(test):
        k = f' -k {a.keyword!r}' if a.keyword else ''
        rc, out = sh(f'timeout 150 {sys.executable} -m pytest {test!r} -x -q -p no:cacheprovider{k}', timeout=170)
        tests_ok = rc == 0
        summary = [l for l in out.splitlines() if re.search(r'passed|failed|error', l)][-3:]
        print(f'TEST {test}: {"PASS" if tests_ok else "FAIL"} | ' + ' | '.join(summary))
        if not tests_ok:
            print(tail(out, 1200))

    for p in problems:
        print('PROBLEM:', p)
    for w in warnings:
        print('WARNING:', w)
    if problems or check is False:
        print('VERDICT: FIX')
        print('NEXT: decide which WRONG cases are real bugs (some may be mistakes in your own cases); fix the real '
              'ones (write .fixer/edit.txt, run python3 .fixer/apply_edit.py --file <path>), then python3 .fixer/verify.py again.')
    elif tests_ok is False and check is not True:
        print('VERDICT: FIX')
        print('NEXT: the related test fails. If your change causes it, fix it; '
              'if it is unrelated (missing fixture, import error elsewhere), call submit_patch.')
    else:
        print('VERDICT: SUBMIT')
        print('NEXT: call submit_patch now. Do not run more checks.')


if __name__ == '__main__':
    main()
