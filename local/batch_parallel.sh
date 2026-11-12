#!/bin/bash
# Local batch in parallel (one process per task and variant) against the local bridge (local/shim_vllm.py).
# Usage: local/batch_parallel.sh <label> "<variant1> <variant2>" "<task1> <task2> ..."
# Results: $NERVO_BASE/batches/<label>/<variant>__<task>.json (+ .log). NERVO_BASE holds bench/ (snapshots).
set -u
LABEL=$1; VARS=$2; TASKS=$3
BASE=${NERVO_BASE:-.}
OUT=$BASE/batches/$LABEL; mkdir -p "$OUT"
cd "$(dirname "$0")/.."
for v in $VARS; do
  for t in $TASKS; do
    n=$(basename "$v")__$t
    python3 local/run_local.py --variant "$v" --data "$BASE/bench" --tasks "$t" \
      --work "$BASE/work_batches/$LABEL/$n" --out "$OUT/$n.json" > "$OUT/$n.log" 2>&1 &
  done
done
wait
echo "batch $LABEL finished"
