"""Build the validation bench locally: tasks.jsonl + snapshots/<id>.tgz.

Only the 104 tasks the official oracle scores (data/new_bench/scorable_kaggle.json).
Snapshots are `git archive` of the base commit (no history), like the official snapshots.
Needs access to github.com.

Usage: python -I local/build_bench.py [--out bench]
"""
import argparse
import json
import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CAMPOS = ['instance_id', 'repo', 'base_commit', 'patch', 'test_patch',
          'problem_statement', 'created_at', 'hints_text']


def empaquetar(d, commit, tgz):
    """Tree of the base commit + a new git repository with a single commit (no history of the original).

    Official snapshots include .git; without it, submit_patch fails with "Not a git repository".
    """
    limpio = d.parent / (d.name + '_limpio')
    subprocess.run(['rm', '-rf', str(limpio)])
    limpio.mkdir(parents=True)
    p = subprocess.Popen(['git', 'archive', '--format=tar', commit], cwd=d, stdout=subprocess.PIPE)
    subprocess.run(['tar', 'xf', '-'], stdin=p.stdout, cwd=limpio, check=True)
    assert p.wait() == 0
    env = {'GIT_AUTHOR_NAME': 'base', 'GIT_AUTHOR_EMAIL': 'base@local', 'GIT_COMMITTER_NAME': 'base',
           'GIT_COMMITTER_EMAIL': 'base@local', 'GIT_AUTHOR_DATE': '2000-01-01T00:00:00Z',
           'GIT_COMMITTER_DATE': '2000-01-01T00:00:00Z', 'PATH': '/usr/bin:/bin:/usr/local/bin'}
    for c in (['git', 'init', '-q'], ['git', 'add', '-A'], ['git', 'commit', '-q', '-m', 'base', '--no-gpg-sign']):
        subprocess.run(c, cwd=limpio, check=True, capture_output=True, env=env)
    subprocess.run(['tar', 'czf', str(tgz.resolve()), '.'], cwd=limpio, check=True)
    subprocess.run(['rm', '-rf', str(limpio)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='bench')
    ap.add_argument('--redo', '--rehacer', dest='rehacer', action='store_true', help='delete existing snapshots')
    ap.add_argument('--tasks', default='', help='only these tasks (comma-separated ids)')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    if a.rehacer:
        subprocess.run(['rm', '-rf', str(out / 'snapshots')])
    (out / 'snapshots').mkdir(parents=True, exist_ok=True)
    ok = set(json.loads((RAIZ / 'data/new_bench/scorable_kaggle.json').read_text())['tasks'])
    tareas = [json.loads(l) for l in (RAIZ / 'data/new_bench/validation_tasks.jsonl').read_text().splitlines()]
    tareas = [t for t in tareas if t['instance_id'] in ok]
    if a.tasks:
        quiero = set(a.tasks.split(','))
        tareas = [t for t in tareas if t['instance_id'] in quiero]
    with open(out / 'tasks.jsonl', 'w') as f:
        for t in tareas:
            f.write(json.dumps({k: t.get(k, '') or '' for k in CAMPOS}) + '\n')
    tmp = out / '_repos'
    for t in tareas:
        tgz = out / 'snapshots' / f"{t['instance_id']}.tgz"
        if tgz.exists():
            continue
        d = tmp / t['instance_id']
        d.mkdir(parents=True, exist_ok=True)
        run = lambda *c: subprocess.run(c, cwd=d, check=True, capture_output=True)
        try:
            run('git', 'init', '-q')
            run('git', 'remote', 'add', 'origin', f"https://github.com/{t['repo']}.git")
            run('git', 'fetch', '-q', '--depth=1', 'origin', t['base_commit'])
            empaquetar(d, t['base_commit'], tgz)
        except Exception as e:
            print('FALLO', t['instance_id'], e)
            tgz.unlink(missing_ok=True)
        subprocess.run(['rm', '-rf', str(d)])
    print('snapshots:', len(list((out / 'snapshots').glob('*.tgz'))), 'of', len(tareas))


if __name__ == '__main__':
    main()
