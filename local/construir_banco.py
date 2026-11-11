"""Construye en local el banco de repos nuevos: tasks.jsonl + snapshots/<id>.tgz.

Solo las 104 tareas puntuables en Kaggle (datos/banco_nuevo/medibles_kaggle.json).
Los snapshots son `git archive` del commit base (sin historial), igual que el dataset
de Kaggle nervo-banco-nuevo. Necesita llegar a github.com.

Uso: python -I local/construir_banco.py [--out /home/claude/banco]
"""
import argparse
import json
import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CAMPOS = ['instance_id', 'repo', 'base_commit', 'patch', 'test_patch',
          'problem_statement', 'created_at', 'hints_text']


def empaquetar(d, commit, tgz):
    """Árbol del commit base + un repo git nuevo con un solo commit (sin historial del original).

    Las snapshots oficiales traen .git; sin él, submit_patch falla con "Not a git repository".
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
    ap.add_argument('--out', default='/home/claude/banco')
    ap.add_argument('--rehacer', action='store_true', help='borrar snapshots existentes')
    ap.add_argument('--tasks', default='', help='solo estas tareas (ids separados por comas)')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    if a.rehacer:
        subprocess.run(['rm', '-rf', str(out / 'snapshots')])
    (out / 'snapshots').mkdir(parents=True, exist_ok=True)
    ok = set(json.loads((RAIZ / 'datos/banco_nuevo/medibles_kaggle.json').read_text())['tareas'])
    tareas = [json.loads(l) for l in (RAIZ / 'datos/banco_nuevo/validation_tasks.jsonl').read_text().splitlines()]
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
    print('snapshots:', len(list((out / 'snapshots').glob('*.tgz'))), 'de', len(tareas))


if __name__ == '__main__':
    main()
