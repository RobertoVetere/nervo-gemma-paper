"""Long run over the validation bench that survives interruptions.

For each task: oracle (no model); if it passes, each variant on that task, one at a time
(a single worker: AI Studio rate-limits). Each result is saved to its own JSON as soon as it
finishes and finished work is skipped, so the run can be relaunched and resumes where it stopped.

Usage:
  python local/overnight.py --tasks a,b,c --variants variants/x,variants/y \
      --data bench --out results/overnight/<label> --minutes 25
  python local/overnight.py --summary results/overnight/<label>
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def correr(args, out, log):
    cmd = [sys.executable, str(RAIZ / 'local/run_local.py')] + args + ['--out', str(out)]
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
    lin = [f"# Run {d.name}", '', '| task | ' + ' | '.join(variantes) + ' |', '|---|' + '---|' * len(variantes)]
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
            celdas.append(f"{'✅' if x['resuelta'] else '❌'} {x['llamadas']} calls {x['segundos']}s"
                          + (f" ({x['error']})" if x['error'] else ''))
        lin.append(f"| {tarea} | " + ' | '.join(celdas) + ' |')
    lin += ['', '**Total:** ' + ', '.join(f"{v} {a}/{n}" for v, (a, n) in tot.items())]
    if len(variantes) == 2:
        a, b = variantes
        gana = [t for t, r in filas.items() if a in r and b in r and r[a]['resuelta'] and not r[b]['resuelta']]
        pierde = [t for t, r in filas.items() if a in r and b in r and r[b]['resuelta'] and not r[a]['resuelta']]
        lin += [f"**Discordant:** only {a}: {len(gana)} {gana}; only {b}: {len(pierde)} {pierde}"]
    (d / 'SUMMARY.md').write_text('\n'.join(lin) + '\n')
    print('\n'.join(lin))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', default='')
    ap.add_argument('--variants', default='')
    ap.add_argument('--data', default='bench')
    ap.add_argument('--out', default='results/overnight/test')
    ap.add_argument('--minutes', '--minutos', dest='minutos', type=float, default=25)
    ap.add_argument('--summary', '--resumen', dest='resumen', default=None)
    a = ap.parse_args()
    if a.resumen:
        return resumen(a.resumen)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = out / '_log.txt'
    work = Path('/tmp/overnight_work')
    for tarea in [t for t in a.tasks.split(',') if t]:
        oraculo = out / f'_oracle__{tarea}.json'
        if not oraculo.exists():
            correr(['--oracle', '--data', a.data, '--tasks', tarea, '--work', str(work / 'oraculo')], oraculo, log)
        o = leer(oraculo)
        if not (o and o.get('resolved')):
            print(f'{tarea}: the oracle does not pass here, skipped', flush=True)
            continue
        for v in [v for v in a.variants.split(',') if v]:
            dest = out / f'{tarea}__v__{Path(v).name}.json'
            if dest.exists():
                continue
            rc, seg = correr(['--variant', v, '--data', a.data, '--tasks', tarea,
                              '--work', str(work / Path(v).name), '--minutos', str(a.minutos)], dest, log)
            t = leer(dest)
            print(f"{tarea} {Path(v).name}: solved={t and t.get('resolved')} rc={rc} {seg}s", flush=True)
        resumen(out)


if __name__ == '__main__':
    main()
