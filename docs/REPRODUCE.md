# Reproducing the paper

Every number in the paper comes from a file in this repository. This guide lists, section by section, where each number
lives and how to regenerate it. Commands run from the repository root with Python 3.12+.

## Numbers you can check at no cost

These commands read saved results only; they need no model, no GPU and no API key. `notebooks/reproduce_paper.ipynb`
runs them all (CPU only; it clones this repository).

```bash
python3 lab/oneshot/summary_format.py results/call_format/*.jsonl          # 4.2: four small models (seven weight variants), 6,720 calls (+ API)
python3 local/count_ab.py results/modal_e4b_4bit/ab_calls.jsonl results/modal_e4b_4bit/ab   # 4.3: interface A/B
python3 local/replica_table.py results/local_deepinfra/l40 results/local_deepinfra/l40_r2 results/local_deepinfra/l40_r3   # 4.4: 31B (API)
python3 local/replica_table.py results/modal_e4b_4bit/q1 results/modal_e4b_4bit/q2         # 4.4: E4B 4-bit
python3 local/interaction.py                                     # 4.4: first-run interaction (11 vs 1, p = 0.006)
python3 local/fig_replicas.py fig.png results/local_deepinfra/l40 results/local_deepinfra/l40_r2 results/local_deepinfra/l40_r3   # Figure 2
python3 local/fig_format.py fig1.png results/call_format/*.jsonl   # Figure 1
python3 lab/oneshot/summary_quantization.py                      # 4.5: single calls, bf16 vs 4-bit vs 31B (API)
python3 local/sample.py --seed 10 --n 40                         # the 40 sampled validation tasks
```

## Section by section

| Paper | Number | Source | How |
|---|---|---|---|
| 2 | Validation set: 104 tasks, 24 repositories, 65 local | `data/new_bench/scorable_kaggle.json`, `scorable_local.json`, `validation_tasks.jsonl` | count ids and repositories |
| 2 | Development set: 72 tasks, 3 repositories | `data/official_scorable_local.json` | count ids |
| 4.1 | Failure taxonomy; 819 of 930 three-field calls rejected (653 naming) | `results/format_agents/SUMMARY.md` (one row per run, with run id) | `results/format_agents/count_format.py` over the run traces |
| 4.2 | Structural failures per model, interface and context; McNemar (single field vs nested/flat; 4-bit vs original); layout errors | `results/call_format/<model>{,_ctx}.jsonl` (one line per call, with the raw model message): `e4b_bf16`, `e4b_4bit`, `e2b-bf16`, `e2b` (4-bit), `qwen3-4b-bf16`, `qwen3-4b-awq`, `qwen3-1.7b-bf16`; `api31b_asked_e4b` = API (requested E4B, served by a 31B) | `lab/oneshot/summary_format.py results/call_format/*.jsonl`; regenerate with `lab/oneshot/call_format.py --items 80 --samples 2 [--context 36000] --backend modal --model <key> --modal <url>/v1` and `local/modal_vllm.py` |
| 4.2 | Pre-registered hypotheses and outcomes | `docs/HYPOTHESES_12NOV.md` (hypotheses committed before the runs; outcomes appended after) | `git log --follow docs/HYPOTHESES_12NOV.md` (the file was renamed from `docs/HIPOTESIS_12NOV.md` when the repository was translated) |
| 4.3 | Interface A/B: 286 of 621 vs 0 of 687 rejected; solved 8 vs 9 | `results/modal_e4b_4bit/ab_calls.jsonl` (one line per tool call), `results/modal_e4b_4bit/ab/*.json` (per task) | `local/count_ab.py results/modal_e4b_4bit/ab_calls.jsonl results/modal_e4b_4bit/ab` |
| 4.4 | 2×2, 31B (API), three replicas; interaction 11 vs 1 (p = 0.006) and 8 vs 4; turn-limit hits; Figure 2 | `results/local_deepinfra/l40`, `l40_r2`, `l40_r3` | `local/replica_table.py`, `local/interaction.py`, `local/batch_table.py`, `local/fig_replicas.py` |
| 4.4 | 2×2, E4B 4-bit, two replicas | `results/modal_e4b_4bit/q1`, `q2` | `local/replica_table.py results/modal_e4b_4bit/q1 results/modal_e4b_4bit/q2` |
| 4.5 | Single calls: E4B bf16 vs 4-bit vs 31B (API); localization; 55 of 64 | `lab/oneshot/chain3_bf16.jsonl`, `chain3_quantized.jsonl`, `chain3.jsonl`; `loc_bf16.jsonl`, `loc_quantized.jsonl`, `loc.jsonl` | `lab/oneshot/summary_quantization.py` |
| 4.5 | Retriever top-3 (28 of 40) | released after the competition closes (2 Dec 2026) | — |
| 4.6 | API served a 31B for E4B requests | DeepInfra model page for `google/gemma-4-E4B-it` (`replaced_by`); response `model` field; billed cost = 31B-turbo prices | one chat completion and the model page |
| 4.6 | Tuning 7/8 vs 14/40 | `results/local_deepinfra/SUMMARY.md`, `l40/g31_example__*.json` | per-task JSON |
| 4.6 | Non-repeating runs (0 of 8) | `results/e4b-determinism-*.json` | two identical configurations |
| 4.6 | Local 23–35% vs test 0.01 and 0.03; statement length | `results/modal_e4b_4bit/q1`, `q2`; competition `tasks.jsonl` and `data/new_bench/validation_tasks.jsonl` | `local/replica_table.py`; words = `re.findall('[A-Za-z]{2,}', problem_statement)` |

## Re-running agents

Requirements: the official evaluator wheels (`swegemma`, `adk_eval_core`, `adk_submission`, `google-adk==1.36.1`; they
ship with the competition data) and an OpenAI-compatible endpoint serving Gemma 4.

```bash
pip install --no-deps wheels/{swegemma,adk_eval_core,adk_submission}-*.whl
pip install wheels/google_adk-1.36.1-py3-none-any.whl "litellm==1.99.4" rich docker
pip install -r local/local_env.txt                 # dependencies of the validation repositories
python3 -I local/build_bench.py --out bench        # build the 104 validation snapshots from GitHub

# bridge: poses as vLLM to the evaluator and forwards to the API, with a spending cap
python3 local/shim_vllm.py --port 8000 --backend deepinfra --cap-usd 2 --log shim.jsonl &
python3 local/run_local.py --variant variants/e4b_cmd --data bench --tasks "$(python3 local/sample.py --seed 10 --n 40 | tr ' ' ,)"
```

A 40-task batch costs about 0.7 USD with E4B. Each line of `shim.jsonl` records the model requested and the cost, which
lets you check that each agent talked to the model it declares.

**Which model answered.** In November 2026 DeepInfra answered `google/gemma-4-E4B-it` with `google/gemma-4-31B-it-turbo`;
every result labelled *API* or *31B (API)* in the paper comes from that model. Check the `model` field of responses.

**Quantized weights.** `local/modal_vllm.py` serves the official `qat-w4a16-ct` weights (and, with
`NERVO_VLLM_MODELO=gemma-4-e4b-it`, the original bf16 E4B weights; other keys serve E2B and Qwen3) with vLLM 0.19.1 on Modal;
`local/modal_eval.py` runs a full evaluation on four L4 GPUs there. Both need a Modal account.

**Caveats.** Sampling uses temperature 0.2 and runs do not repeat exactly (Section 4.6), so re-runs move by a few tasks.
Runs through an API do not reproduce the tool-call failures of the quantized model served by
vLLM; those were measured in the competition environment.

## Agent names

| Paper | Folder |
|---|---|
| Free-form agent, with / without reasoning | `variants/community_base`, `variants/e4b_t0` |
| `fixer` (E4B), without / with reasoning | `variants/e4b_cmd`, `variants/e4b_cmd_t` |
| `fixer`, shorter 31B version | `variants/g31_example` |
| Prompt variants of the free-form agent | `variants/com_v1` … `com_v4` |

## Single-call probes (Section 4.5)

The probe scripts in `lab/oneshot/` read task snapshots from `$NERVO_BENCH/snapshots/` (default `./bench`, built with
`local/build_bench.py`) and write scratch copies under `$NERVO_WORK` (default `/tmp/nervo_probes`). They call DeepInfra
(`~/.deepinfra_key`) or, with `NERVO_SONDA_MODAL=<url>/v1`, a server from `local/modal_vllm.py` (`~/.modal_vllm_key`;
`NERVO_SONDA_SERVIDO` = served model name). Main entry points: `probe3.py` (localize with the map, then repair;
`SONDA_CONDS=F` rewrites the whole function) and `loc.py` (localization only).
