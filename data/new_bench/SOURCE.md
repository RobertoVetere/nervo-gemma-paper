# Validation bench (new repositories)

`validation_tasks.jsonl`: 165 verified tasks (they fail without the fix and pass with it, repeated in a clean sandbox)
from 35 repositories that are not the competition's 4 public repositories.

- Source: Kaggle dataset `dmitriigluzdov/gemma-4-task-soundness-and-local-results` (Dmitrii Gluzdov), version of 7 Nov 2026.
- License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Copied unchanged.
- The reference patches (`patch`) and test patches (`test_patch`) are only for scoring: they are never shown to the agent.
- `scorable_kaggle.json`: the 104 tasks the official oracle scores as solved with the reference patch (24 repositories).
  `scorable_local.json`: the 65 of them that also pass locally (`local/run_local.py --oracle`). `batch_1.json`: the first
  batch of 16 tasks used for the overnight run in `results/overnight/batch1/`.

`local/build_bench.py` builds the snapshots (`git archive` of the base commit, no history, plus a one-commit git
repository) for use with `local/run_local.py --data`.
