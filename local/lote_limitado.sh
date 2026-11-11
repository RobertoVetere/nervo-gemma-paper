#!/bin/bash
# Como lote_paralelo.sh pero con un máximo de procesos a la vez (la máquina tiene 2 CPU).
# Uso: local/lote_limitado.sh <etiqueta> <variante> <max_paralelo> <tarea1> <tarea2> ...
set -u
ETQ=$1; V=$2; N=$3; shift 3
BASE=${NERVO_BASE:-/home/claude}   # carpeta con banco/ (snapshots) y donde se dejan lotes/
OUT=$BASE/lotes/$ETQ; mkdir -p "$OUT"
cd "$(dirname "$0")/.."
printf '%s\n' "$@" | xargs -P "$N" -I{} sh -c '
  n=$(basename '"$V"')__{}
  [ -f '"$OUT"'/$n.json ] && exit 0
  python3 local/correr_local.py --variant '"$V"' --data '"$BASE"'/banco --tasks {} \
    --work '"$BASE"'/trabajo_lotes/'"$ETQ"'/$n --out '"$OUT"'/$n.json > '"$OUT"'/$n.log 2>&1'
echo "lote $ETQ $V terminado"
