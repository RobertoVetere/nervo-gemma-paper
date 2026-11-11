"""Cuenta llamadas rechazadas por formato en las trazas de Kaggle (artefactos salida-kaggle).

Uso: python3 -I resultados/formato/contar_formato.py <carpeta_con_un_subdir_por_run>
Formato roto = la llamada la rechaza la validación (SKILL_NOT_FOUND, INVALID_ARGUMENTS, SCRIPT_NOT_FOUND,
errores de validación de argumentos). Edición fallida = el cambio no se aplicó (FileEditError, bloque no aplicado).
"""
import glob
import json
import re
import sys

FMT = re.compile(r'SKILL_NOT_FOUND|INVALID_ARGUMENTS|SCRIPT_NOT_FOUND|validation error|Field required|'
                 r'missing \d+ required|unexpected keyword')
EDIT = re.compile(r'FileEditError|not applied \(|old_string not found')
base = sys.argv[1]
for run in sorted(glob.glob(f'{base}/*/')):
    calls = fmt = ed = tasks = 0
    for f in glob.glob(f'{run}results/*/traces/trace_*.json'):
        tasks += 1
        for s in json.load(open(f))['steps']:
            for c in s.get('tool_calls') or []:
                calls += 1
                o = s.get('observation')
                o = o.get('content', '') if isinstance(o, dict) else str(o)
                if FMT.search(o[:600]):
                    fmt += 1
                elif EDIT.search(o[:600]):
                    ed += 1
    print(run, tasks, calls, fmt, ed)
