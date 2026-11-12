# Reproducing the paper

Every number in the paper comes from a file in this repository. This guide lists, section by section, where each number
lives and how to regenerate it. Commands run from the repository root with Python 3.12+.

## Numbers you can check at no cost

These commands read saved results only; they need no model, no GPU and no API key. `notebooks/reproduce_paper.ipynb`
runs them all (CPU only; it clones this repository).

```bash
python3 lab/oneshot/resumen_formato.py resultados/formato_llamadas/e4b_*.jsonl   # 4.2: controlled format test (1,920 calls)
python3 local/tabla_replicas.py resultados/local_deepinfra/l40 resultados/local_deepinfra/l40_r2 resultados/local_deepinfra/l40_r3   # 4.3: three replicas
python3 local/fig_replicas.py fig.png resultados/local_deepinfra/l40 resultados/local_deepinfra/l40_r2 resultados/local_deepinfra/l40_r3   # Figure 1 (needs matplotlib)
python3 local/tabla_lote.py resultados/local_deepinfra/l40     # 4.3: 2x2 table, Wilson intervals, McNemar tests, cut-offs
python3 local/interaccion.py                                     # 4.3: interaction sign test (11 vs 1, p = 0.006)
python3 lab/oneshot/resumen_cuantizacion.py                      # 4.4-4.5: single-call probes, Fisher tests, whole-function rewrite
python3 local/muestra.py --semilla 10 --n 40                     # 4.3: the 40 sampled validation tasks
```

## Section by section

| Paper | Number | Source | How |
|---|---|---|---|
| 2 | Validation set: 104 tasks, 24 repositories, 65 local | `datos/banco_nuevo/medibles_kaggle.json`, `medibles_local.json`, `validation_tasks.jsonl` | count ids and repositories |
| 2 | Development set: 72 tasks, 3 repositories | `datos/oficiales_medibles_local.json` | count ids |
| 4.1 | Failure taxonomy and rejected-call table | `resultados/formato/RESUMEN.md` (one row per evaluation run, with run id) | rows summed per interface; counted by `resultados/formato/contar_formato.py` over the run traces |
| 4.2 | Controlled format test: lost fields per interface, bf16 vs 4-bit E4B on one server, with/without context; Fisher tests; quote endings | `resultados/formato_llamadas/e4b_bf16{,_ctx}.jsonl` (bf16), `e4b_q{,_ctx}.jsonl` (4-bit), `e4b_di{,_ctx}.jsonl` (API, served by a 31B) | `lab/oneshot/resumen_formato.py`; regenerate with `lab/oneshot/formato_llamadas.py --items 80 --muestras 2 [--contexto 36000] --backend modal --modelo e4b\|e4b-bf16` |
| 4.3 | Three replicas (per-replica counts, means, interaction 8 vs 4 in new replicas, turn-limit hits) | `resultados/local_deepinfra/l40`, `l40_r2`, `l40_r3` | `local/tabla_replicas.py`; Figure 1 with `local/fig_replicas.py` |
| 4.3 | 2×2 table, McNemar, Wilson, turn-limit cut-offs | `resultados/local_deepinfra/l40/` | `local/tabla_lote.py` |
| 4.3 | Interaction 11 vs 1, p = 0.006 | same files | `local/interaccion.py` |
| 4.4 | Single-call table (bf16 vs 4-bit E4B vs 31B API), localization, Fisher tests | `lab/oneshot/cadena3_bf16.jsonl`, `cadena3_cuantizado.jsonl`, `cadena3.jsonl` (API, 31B); `loc_bf16.jsonl`, `loc_cuantizado.jsonl`, `loc.jsonl` | `lab/oneshot/resumen_cuantizacion.py`; regenerate with `NERVO_SONDA_MODAL=<url> NERVO_SONDA_SERVIDO=gemma-4-e4b-it SONDA_CONFIGS=e4b,e4b_t python3 lab/oneshot/sonda3.py` and `lab/oneshot/loc.py` |
| 4.5 | Whole-function rewrite 6 vs 5 of 18 | `lab/oneshot/cadena_funcion_cuantizado.jsonl` | `resumen_cuantizacion.py`; regenerate with `SONDA_CONDS=A,F` |
| 4.5 | Retriever top-3 (28/40, 38/72; strict 23, 28) and 31B runs | `resultados/dossier-*.json` (31B runs) | the retriever is released after the competition closes (2 Dec 2026) |
| 4.6 | Tuning 7/8 vs 14/40 | `resultados/local_deepinfra/RESUMEN.md`, `l40/g31_ejemplo__*.json` | per-task JSON |
| 4.6 | Non-repeating runs (0 of 8) | `resultados/e4b-determinismo-*.json`, `docs/HISTORIAL_EJECUCIONES.md` (11 Nov) | two identical configurations on the same tasks |
| 4.6 | Statement length and runnable examples | competition `tasks.jsonl` (download from Kaggle) and `datos/banco_nuevo/validation_tasks.jsonl` | words = `re.findall('[A-Za-z]{2,}', problem_statement)` |
| 4.6 | API served a 31B for E4B requests | DeepInfra model page for `google/gemma-4-E4B-it` (`replaced_by: google/gemma-4-31B-it-turbo`); response `model` field; bridge logs: billed cost equals 31B-turbo prices | `curl` the model page and one chat completion; compare `usage` × prices |
| 4.6 | Docker replica 4 of 5 | `resultados/local_deepinfra/e4b_docker/` | `local/correr_local.py --sandbox docker` |
| 4.6 | Test-set scores 0.01 and 0.03 | competition leaderboard | not reproducible outside Kaggle |

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

**Which model answered.** In November 2026 DeepInfra answered `google/gemma-4-E4B-it` with `google/gemma-4-31B-it-turbo`;
every result labelled *API* or *31B (API)* in the paper comes from that model. Check the `model` field of responses.

**Quantized weights.** `local/modal_vllm.py` serves the official `qat-w4a16-ct` weights (and, with
`NERVO_VLLM_MODELO=gemma-4-e4b-it`, the original bf16 E4B weights) with vLLM 0.19.1 on Modal;
`local/modal_eval.py` runs a full evaluation on four L4 GPUs there. Both need a Modal account.

**Caveats.** Sampling uses temperature 0.2 and runs do not repeat exactly (Section 4.6), so re-runs move by a few tasks.
Runs through an API do not reproduce the tool-call failures of the quantized model served by
vLLM; those were measured in the competition environment.

## Agent names

| Paper | Folder |
|---|---|
| Free-form agent, with / without reasoning | `variantes/base_comunidad`, `variantes/e4b_t0` |
| `fixer` (E4B), without / with reasoning | `variantes/e4b_cmd`, `variantes/e4b_cmd_t` |
| `fixer`, shorter 31B version | `variantes/g31_ejemplo` |
| Prompt variants of the free-form agent | `variantes/com_v1` … `com_v4` |
