#!/bin/bash
# Like batch_parallel.sh but with at most N processes at a time.
# Usage: local/batch_limited.sh <label> <variant> <max_parallel> <task1> <task2> ...
set -u
LABEL=$1; V=$2; N=$3; shift 3
BASE=${NERVO_BASE:-.}   # folder with bench/ (snapshots); results go to batches/
OUT=$BASE/batches/$LABEL; mkdir -p "$OUT"
cd "$(dirname "$0")/.."
printf '%s\n' "$@" | xargs -P "$N" -I{} sh -c '
  n=$(basename '"$V"')__{}
  [ -f '"$OUT"'/$n.json ] && exit 0
  python3 local/run_local.py --variant '"$V"' --data '"$BASE"'/bench --tasks {} \
    --work '"$BASE"'/work_batches/'"$LABEL"'/$n --out '"$OUT"'/$n.json > '"$OUT"'/$n.log 2>&1'
echo "batch $LABEL $V finished"
