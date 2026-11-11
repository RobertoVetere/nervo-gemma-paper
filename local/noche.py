"""Tanda larga del banco nuevo, a prueba de cortes.

Para cada tarea: oráculo (sin modelo); si pasa, cada variante sobre esa tarea, de una en una
(un solo trabajador: AI Studio limita la velocidad). Cada resultado se guarda en su propio JSON
nada más terminar, y lo ya hecho se salta, así que se puede relanzar y retoma donde iba.

Uso:
  python local/noche.py --tasks a,b,c --variants variantes/x,variantes/y \
      --data /home/claude/banco --out resultados/noche/<etiqueta> --minutos 25
  python local/noche.py --resumen resultados/noche/<etiqueta>
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def correr(args, out, log):
    cmd = [sys.executable, str(RAIZ / 'local/correr_local.py')] + args + ['--out', str(out)]
    t0 = time.time()
    with open(log, 'a') as f:
        f.write(f"\n### {time.strftime('%H:%M:%S')} {' '.join(cmd)}\n")
        f.flush()
        r = subprocess.run(cmd, cwd=RAIZ, stdout=f, stderr=subprocess.STDOUT)
    return r.returncode, round(time.time() - t0)


def leer(p):
    try:
        t = json.loads(Path(p).read_text())['tareas'][0]
        return t
    except Exception:
        return None


def resumen(d):
    d = Path(d)
    filas, variantes = {}, set()
    for p in sorted(d.glob('*.json')):
        if p.name.startswith('_'):
            continue
        tarea, var = p.stem.split('__v__')
        t = leer(p)
        if t is None:
            continue
        variantes.add(var)
        raw = t.get('raw') or {}
        filas.setdefault(tarea, {})[var] = {
            'resuelta': bool(t.get('resolved')),
            'llamadas': t.get('tool_calls'),
            'segundos': round(t.get('duration_s') or 0),
            'parche': t.get('patch_chars', 0),
            'error': (raw.get('error_message') or '')[:60],
        }
    variantes = sorted(variantes)
    lin = [f"# Tanda {d.name}", '', '| tarea | ' + ' | '.join(variantes) + ' |', '|---|' + '---|' * len(variantes)]
    tot = {v: [0, 0] for v in variantes}
    for tarea, r in sorted(filas.items()):
        celdas = []
        for v in variantes:
            x = r.get(v)
            if x is None:
                celdas.append('—')
                continue
            tot[v][0] += x['resuelta']
            tot[v][1] += 1
            celdas.append(f"{'✅' if x['resuelta'] else '❌'} {x['llamadas']}ll {x['segundos']}s"
                          + (f" ({x['error']})" if x['error'] else ''))
        lin.append(f"| {tarea} | " + ' | '.join(celdas) + ' |')
    lin += ['', '**Total:** ' + ', '.join(f"{v} {a}/{n}" for v, (a, n) in tot.items())]
    if len(variantes) == 2:
        a, b = variantes
        gana = [t for t, r in filas.items() if a in r and b in r and r[a]['resuelta'] and not r[b]['resuelta']]
        pierde = [t for t, r in filas.items() if a in r and b in r and r[b]['resuelta'] and not r[a]['resuelta']]
        lin += [f"**Discordantes:** solo {a}: {len(gana)} {gana}; solo {b}: {len(pierde)} {pierde}"]
    (d / 'RESUMEN.md').write_text('\n'.join(lin) + '\n')
    print('\n'.join(lin))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', default='')
    ap.add_argument('--variants', default='')
    ap.add_argument('--data', default='/home/claude/banco')
    ap.add_argument('--out', default='resultados/noche/prueba')
    ap.add_argument('--minutos', type=float, default=25)
    ap.add_argument('--resumen', default=None)
    a = ap.parse_args()
    if a.resumen:
        return resumen(a.resumen)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / '_log.txt'
    work = Path('/tmp/noche_trabajo')
    for tarea in [t for t in a.tasks.split(',') if t]:
        oraculo = out / f'_oraculo__{tarea}.json'
        if not oraculo.exists():
            correr(['--oracle', '--data', a.data, '--tasks', tarea, '--work', str(work / 'oraculo')], oraculo, log)
        o = leer(oraculo)
        if not (o and o.get('resolved')):
            print(f'{tarea}: el oráculo no pasa aquí, se salta', flush=True)
            continue
        for v in [v for v in a.variants.split(',') if v]:
            dest = out / f'{tarea}__v__{Path(v).name}.json'
            if dest.exists():
                continue
            rc, seg = correr(['--variant', v, '--data', a.data, '--tasks', tarea,
                              '--work', str(work / Path(v).name), '--minutos', str(a.minutos)], dest, log)
            t = leer(dest)
            print(f"{tarea} {Path(v).name}: resuelta={t and t.get('resolved')} rc={rc} {seg}s", flush=True)
        resumen(out)


if __name__ == '__main__':
    main()
