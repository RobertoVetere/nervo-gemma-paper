#!/usr/bin/env python3
"""Prepare the data folder the kernel reads (NERVO_DATA) for given tasks and pack it into a tar.

Official tasks (default): downloaded from the competition with the Kaggle CLI, as the evaluation sees them:
tasks.jsonl, snapshots/<id>.tgz, the graphs and embeddings of their commit, wheels/ and sandbox/setup.py.
Validation bench (--bench): snapshots built from GitHub with local/build_bench.py.
Usage: python3 local/prepare_modal_data.py --tasks id1,id2 [--bench] --out data.tar
"""
import argparse, json, os, subprocess, sys, tarfile, time, zipfile
from pathlib import Path

COMP = 'gemma-4-developer-agent'
RAIZ = Path(__file__).resolve().parent.parent


def kaggle_file(f, dest):
    """Download a competition file. Skip it if present (workflow cache) and retry if Kaggle rate-limits (429)."""
    dest.mkdir(parents=True, exist_ok=True)
    nombre = f.split('/')[-1]
    if (dest / nombre).exists():
        return
    for intento in range(8):
        r = subprocess.run(['kaggle', 'competitions', 'download', COMP, '-f', f, '-p', str(dest), '-q'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            break
        print(f'[reintento {intento + 1}] {f}: {(r.stdout + r.stderr).strip()[-200:]}', flush=True)
        time.sleep(30 * (intento + 1))
    else:
        raise SystemExit(f'could not download {f}')
    for z in dest.glob('*.zip'):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)
        z.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', '--tareas', dest='tareas', required=True); ap.add_argument('--bench', '--banco', dest='banco', action='store_true')
    ap.add_argument('--out', default='data.tar'); ap.add_argument('--dir', default='comp_data')
    a = ap.parse_args()
    ids = [x for x in a.tareas.split(',') if x]
    d = Path(a.dir); d.mkdir(exist_ok=True)
    if a.banco:
        subprocess.run([sys.executable, '-I', str(RAIZ / 'local/build_bench.py'), '--out', str(d), '--tasks', ','.join(ids)],
                       check=True)
        (d / 'wheels').mkdir(exist_ok=True)
    else:
        kaggle_file('tasks.jsonl', d)
        tareas = {json.loads(l)['instance_id']: json.loads(l) for l in open(d / 'tasks.jsonl')}
        faltan = [i for i in ids if i not in tareas]
        assert not faltan, f'unknown tasks: {faltan}'
        listado, tok = [], ''
        for _ in range(60):  # the CLI pages 200 at a time
            cmd = ['kaggle', 'competitions', 'files', COMP, '--page-size', '200'] + (['--page-token', tok] if tok else [])
            out = subprocess.run(cmd, capture_output=True, text=True).stdout
            listado += [l.split()[0] for l in out.splitlines() if l.strip() and not l.startswith(('name', '---', 'Next Page'))]
            m = [l for l in out.splitlines() if l.startswith('Next Page Token')]
            tok = m[0].split('=', 1)[1].strip() if m else ''
            if not tok:
                break
        for i in ids:
            kaggle_file(f'snapshots/{i}.tgz', d / 'snapshots')
            commit = tareas[i]['base_commit']
            for f in listado:
                if f.startswith(('graphs/', 'embeddings/')) and commit in f:
                    kaggle_file(f, d / f.split('/')[0])
        for f in [x for x in listado if x.startswith('wheels/') and x.endswith('.whl')]:
            kaggle_file(f, d / 'wheels')
        kaggle_file('sandbox/setup.py', d / 'sandbox')
    with tarfile.open(a.out, 'w') as tf:
        tf.add(d, arcname='.')
    print('datos:', a.out, round(os.path.getsize(a.out) / 1e6), 'MB')


if __name__ == '__main__':
    main()
