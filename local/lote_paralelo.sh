#!/bin/bash
# Lote local en paralelo (un proceso por tarea y variante) contra el puente local.
# Uso: local/lote_paralelo.sh <etiqueta> "<variante1> <variante2>" "<tarea1> <tarea2> ..."
# Resultados: /home/claude/lotes/<etiqueta>/<variante>__<tarea>.json (+ .log)
set -u
ETQ=$1; VARS=$2; TAREAS=$3
OUT=/home/claude/lotes/$ETQ; mkdir -p "$OUT"
cd "$(dirname "$0")/.."
for v in $VARS; do
  for t in $TAREAS; do
    n=$(basename "$v")__$t
    python3 local/correr_local.py --variant "$v" --data /home/claude/banco --tasks "$t" \
      --work "/home/claude/trabajo_lotes/$ETQ/$n" --out "$OUT/$n.json" > "$OUT/$n.log" 2>&1 &
  done
done
wait
echo "lote $ETQ terminado"
