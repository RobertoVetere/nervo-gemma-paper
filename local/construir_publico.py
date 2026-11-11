"""Banco local con las tareas PÚBLICAS de la competición (rich, httpx, fastapi, requests).

Lee las tareas de descarga/comp/tasks.jsonl (artefacto `descarga`) y construye snapshots desde GitHub
con el mismo formato que construir_banco.py. Solo las de datos/tareas_medibles.json (validadas con oráculo en Kaggle).

Uso: python -I local/construir_publico.py --tasks fastapi_11194,rich_3454 [--out /home/claude/banco_pub]
"""
import argparse
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'local'))
from construir_banco import CAMPOS, empaquetar  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/home/claude/banco_pub')
    ap.add_argument('--tasks', default='')
    ap.add_argument('--fuente', default='/home/claude/descarga/comp/tasks.jsonl')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / 'snapshots').mkdir(parents=True, exist_ok=True)
    medibles = set(json.loads((RAIZ / 'datos/tareas_medibles.json').read_text()))
    tareas = [json.loads(l) for l in open(a.fuente)]
    tareas = [t for t in tareas if t['instance_id'] in medibles]
    if a.tasks:
        quiero = set(a.tasks.split(','))
        tareas = [t for t in tareas if t['instance_id'] in quiero]
    with open(out / 'tasks.jsonl', 'w') as f:
        for t in tareas:
            f.write(json.dumps({k: t.get(k, '') or '' for k in CAMPOS}) + '\n')
    for t in tareas:
        tgz = out / 'snapshots' / f"{t['instance_id']}.tgz"
        if tgz.exists():
            continue
        d = out / '_repos' / t['instance_id']
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
