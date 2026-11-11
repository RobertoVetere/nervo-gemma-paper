#!/usr/bin/env python3
"""Prepara el directorio de datos que el kernel lee (NERVO_DATA) para unas tareas concretas y lo empaqueta en un tar.

Tareas oficiales (por defecto): se descargan de la competición con la CLI de Kaggle, igual que las ve el examen:
tasks.jsonl, snapshots/<id>.tgz, los grafos y embeddings de su commit, wheels/ y sandbox/setup.py.
Banco nuevo (--banco): snapshots construidos desde GitHub con local/construir_banco.py.
Uso: python3 local/preparar_datos_modal.py --tareas id1,id2 [--banco] --out datos.tar
"""
import argparse, json, os, subprocess, sys, tarfile, time, zipfile
from pathlib import Path

COMP = 'gemma-4-developer-agent'
RAIZ = Path(__file__).resolve().parent.parent


def kaggle_file(f, dest):
    """Descarga un archivo de la competición. Salta si ya está (caché del workflow) y reintenta si Kaggle limita (429)."""
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
        raise SystemExit(f'no se pudo descargar {f}')
    for z in dest.glob('*.zip'):
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)
        z.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tareas', required=True); ap.add_argument('--banco', action='store_true')
    ap.add_argument('--out', default='datos.tar'); ap.add_argument('--dir', default='datos')
    a = ap.parse_args()
    ids = [x for x in a.tareas.split(',') if x]
    d = Path(a.dir); d.mkdir(exist_ok=True)
    if a.banco:
        subprocess.run([sys.executable, '-I', str(RAIZ / 'local/construir_banco.py'), '--out', str(d), '--tasks', ','.join(ids)],
                       check=True)
        (d / 'wheels').mkdir(exist_ok=True)
    else:
        kaggle_file('tasks.jsonl', d)
        tareas = {json.loads(l)['instance_id']: json.loads(l) for l in open(d / 'tasks.jsonl')}
        faltan = [i for i in ids if i not in tareas]
        assert not faltan, f'tareas desconocidas: {faltan}'
        listado, tok = [], ''
        for _ in range(60):  # la CLI pagina de 200 en 200
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
