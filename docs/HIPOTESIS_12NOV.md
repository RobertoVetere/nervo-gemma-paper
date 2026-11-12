# Pre-registered hypotheses — 12 November 2026, before running these experiments

Written and committed before any of the runs below produced results. The commit timestamp is the record.

## H1 — Nesting long text breaks tool calls in small models generally (format test, `lab/oneshot/formato_llamadas.py`)
Same 80 code blocks × 2 samples × 3 interfaces as Section 4.2, on vLLM 0.19.1, short and long (~10k tokens) context.
Models: Gemma 4 E2B (bf16 and official QAT w4a16), Qwen3-4B (bf16 and official AWQ 4-bit), Qwen3-1.7B (bf16).
- H1a: in every model, the nested interface (`args` object) loses fields in more calls than the flat `edit_file` and
  the single-field interface, in at least one context condition.
- H1b: flat and single-field interfaces lose fields in at most 2% of calls in every model and condition.
- H1c: for each pair of original vs 4-bit weights, long context increases the gap (4-bit loses more) relative to short
  context. Tested per pair with McNemar over blocks (a block fails if any of its 2 samples lost fields).
- Prediction for smaller models (E2B, Qwen3-1.7B): more nested-call failures than E4B / Qwen3-4B.

## H2 — The 2×2 with Gemma 4 E4B 4-bit (Section 4.3 rerun on our vLLM server, same 40 tasks)
- H2a: reasoning helps the free-form agent (more solved tasks with reasoning than without).
- H2b: reasoning does not help `fixer` (solved with reasoning ≤ without), and `fixer` with reasoning hits the 80-turn
  limit more often than without.
- Expected absolute level: lower than the 31B (API), roughly 3–10 of 40 per cell.

## H3 — Interface A/B inside the agent (Gemma 4 E4B 4-bit, same tasks)
`variantes/e4b_steps` (every script called through the three-field skill call) against `variantes/e4b_cmd` (one skill
call to install, then one-field `run_command`). Same skill scripts and steps.
- H3a: the three-field agent has a higher share of tool calls rejected for format than the one-field agent.
- H3b: solved tasks are not lower with the one-field agent.

## Analysis rules fixed in advance
- Report every model and condition run, including those that contradict the hypotheses.
- Block-level McNemar for H1; per-cell counts and paired per-task comparisons for H2 and H3; no new tests added after
  seeing the data without saying so.

---

## Outcomes (added after the runs, 12 November 2026, afternoon)

Numbers from `lab/oneshot/resumen_formato.py resultados/formato_llamadas/*.jsonl`, `local/contar_ab.py` and
`local/tabla_replicas.py resultados/modal_e4b_4bit/q1 resultados/modal_e4b_4bit/q2`. Structural failure = the call
never runs or loses a required field (re-scored from the raw message; content that ignores the SEARCH/REPLACE layout
is counted separately, not as a lost field).

- **H1a — partly held.** Nested failed more than single-field in every model (p ≤ 0.008), but not always more than
  flat: Qwen3-1.7B short context, nested 9 vs flat 30 of 160.
- **H1b — failed.** Flat stayed ≤ 2% only for E4B (E2B bf16 short 10/160; Qwen 74–99/160). Single field stayed ≤ 2%
  except Qwen3-4B AWQ long (8/160) and Qwen3-1.7B long (15/160).
- **H1c — held only for E4B.** E2B 4-bit was worse than bf16 in both contexts (blocks 45 vs 21 short, 55 vs 36 long);
  Qwen3-4B AWQ did not differ from bf16 (59 vs 54, 52 vs 53).
- Smaller models failed more: held for E2B vs E4B; Qwen3-1.7B failed less than Qwen3-4B in short context and more in
  long context.
- **H2a — held in direction.** E4B 4-bit, free-form agent: 12, 12 without reasoning; 13, 14 with reasoning.
- **H2b — failed.** `fixer`: 9, 12 without; 12, 10 with. Turn-limit hits 0 in all `fixer` cells.
- Expected level 3–10 of 40: exceeded (9–14 of 40).
- **H3a — held.** Three-field 286 of 621 calls rejected for format; one-field 0 of 687.
- **H3b — held.** Solved 8 vs 9 of 40 (one task only with one-field).
- Not pre-registered and reported as such: per-model McNemar of single field vs flat, and the re-scoring that
  separates lost fields from layout errors.
