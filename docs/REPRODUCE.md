# Reproducing the paper

Every number in the paper comes from a file in this repository. This guide lists, section by section, where each number
lives and how to regenerate it. Commands run from the repository root with Python 3.12+.

## Numbers you can check at no cost

These commands read saved results only; they need no model, no GPU and no API key.

```bash
python3 local/tabla_lote.py resultados/local_deepinfra/l40     # 4.2: 2x2 table, Wilson intervals, McNemar tests, cut-offs
python3 local/interaccion.py                                     # 4.2: interaction sign test (11 vs 1, p = 0.006)
python3 lab/oneshot/resumen_cuantizacion.py                      # 4.3-4.4: single-call probes, Fisher tests, whole-function rewrite
python3 local/muestra.py --semilla 10 --n 40                     # 4.2: the 40 sampled validation tasks
```

## Section by section

| Paper | Number | Source | How |
|---|---|---|---|
| 2 | Validation set: 104 tasks, 24 repositories, 65 local | `datos/banco_nuevo/medibles_kaggle.json`, `medibles_local.json`, `validation_tasks.jsonl` | count ids and repositories |
| 2 | Development set: 72 tasks, 3 repositories | `datos/oficiales_medibles_local.json` | count ids |
| 4.1 | Failure taxonomy and rejected-call table | `resultados/formato/RESUMEN.md` (one row per evaluation run, with run id) | rows summed per interface; counted by `resultados/formato/contar_formato.py` over the run traces |
| 4.2 | 2×2 table, McNemar, Wilson, turn-limit cut-offs | `resultados/local_deepinfra/l40/` | `local/tabla_lote.py` |
| 4.2 | Interaction 11 vs 1, p = 0.006 | same files | `local/interaccion.py` |
| 4.2 | Prompt variants 8, 7, 11 vs 12 and 11 | `resultados/local_deepinfra/filo14/`, `filo14_pub2/`, `RESUMEN.md`; tasks in `datos/filo14.txt` | per-task JSON |
| 4.3 | Single-call table, location mismatch, Fisher tests | `lab/oneshot/cadena3.jsonl`, `cadena3_cuantizado.jsonl`, `loc.jsonl`, `loc_cuantizado.jsonl` | `lab/oneshot/resumen_cuantizacion.py`; regenerate with `lab/oneshot/sonda3.py` and `lab/oneshot/loc.py` |
| 4.3 | Reasoning budget 12,288 vs 4,096 (1 of 6 each); calls per task | `resultados/e4b-t16-vs-4096-*.json`, `e4b-t0-vs-t4096-*.json`, `e4b-determinismo-*.json`, `bat-real-01-e4b-*.json` | per-variant medians of `tool_calls` |
| 4.4 | Whole-function rewrite 6 vs 5 of 18 | `lab/oneshot/cadena_funcion_cuantizado.jsonl` | `resumen_cuantizacion.py`; regenerate with `SONDA_CONDS=A,F` |
| 4.4 | Retriever top-3 (28/40, 38/72; strict 23, 28) and 31B runs | `resultados/dossier-*.json` (31B runs) | the retriever is released after the competition closes (2 Dec 2026) |
| 4.5 | Tuning 7/8 vs 14/40 | `resultados/local_deepinfra/RESUMEN.md`, `l40/g31_ejemplo__*.json` | per-task JSON |
| 4.5 | Non-repeating runs (0 of 8) | `resultados/e4b-determinismo-*.json`, `docs/HISTORIAL_EJECUCIONES.md` (11 Nov) | two identical configurations on the same tasks |
| 4.5 | Statement length and runnable examples | competition `tasks.jsonl` (download from Kaggle) and `datos/banco_nuevo/validation_tasks.jsonl` | words = `re.findall('[A-Za-z]{2,}', problem_statement)` |
| 4.5 | Docker replica 4 of 5 | `resultados/local_deepinfra/e4b_docker/` | `local/correr_local.py --sandbox docker` |
| 4.5 | Test-set scores 0.01 and 0.03 | competition leaderboard | not reproducible outside Kaggle |

## Re-running agents

Requirements: the official evaluator wheels (`swegemma`, `adk_eval_core`, `adk_submission`, `google-adk==1.36.1`; they
ship with the competition data) and an OpenAI-compatible endpoint serving Gemma 4.

```bash
pip install --no-deps wheels/{swegemma,adk_eval_core,adk_submission}-*.whl
pip install wheels/google_adk-1.36.1-py3-none-any.whl "litellm==1.99.4" rich docker
pip install -r local/entorno_local.txt                 # dependencies of the validation repositories
python3 -I local/construir_banco.py --out banco        # build the 104 validation snapshots from GitHub

# bridge: poses as vLLM to the evaluator and forwards to the API, with a spending cap
python3 local/shim_vllm.py --port 8000 --backend deepinfra --tope-usd 2 --log shim.jsonl &
python3 local/correr_local.py --variant variantes/e4b_cmd --data banco --tasks "$(python3 local/muestra.py --semilla 10 --n 40 | tr ' ' ,)"
```

A 40-task batch costs about 0.7 USD with E4B. Each line of `shim.jsonl` records the model requested and the cost, which
lets you check that each agent talked to the model it declares.

**Quantized weights.** `local/modal_vllm.py` serves the official `qat-w4a16-ct` weights with vLLM 0.19.1 on Modal;
`local/modal_eval.py` runs a full evaluation on four L4 GPUs there. Both need a Modal account.

**Caveats.** Sampling uses temperature 0.2 and runs do not repeat exactly (Section 4.5), so re-runs move by a few tasks.
Runs with unquantized weights through an API do not reproduce the tool-call failures of the quantized model served by
vLLM; those were measured in the competition environment.

## Agent names

| Paper | Folder |
|---|---|
| Free-form agent, with / without reasoning | `variantes/base_comunidad`, `variantes/e4b_t0` |
| `fixer` (E4B), without / with reasoning | `variantes/e4b_cmd`, `variantes/e4b_cmd_t` |
| `fixer`, shorter 31B version | `variantes/g31_ejemplo` |
| Prompt variants of the free-form agent | `variantes/com_v1` … `com_v4` |
