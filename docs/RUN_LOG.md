# Log of evaluation runs on Kaggle

All runs were launched with the workflow **"Evaluate on Kaggle (L4)"** (`.github/workflows/evaluate.yml`) from the
development repository. The ID is the GitHub Actions run id. Results are in `results/<label>-<date>.json`.

Times in UTC. Codes such as (E8) refer to entries of an internal lessons log that is not part of this repository; the
row text says what each one was. "Quota" is Kaggle's weekly GPU quota, which counted double in this competition.

| Date (UTC) | ID | Label | What it was | Result | Valid? |
|---|---|---|---|---|---|
| 06-Nov 20:48 | 42291403604 | v0 | Chain v0 (LOCATE→FIX→VERIFY→FINALIZE, `SequentialAgent`), E4B, 12 tasks from a fixed sample | 0/12; 8 empty patches | Partly: the bench still scored requests/httpx wrongly (E6) and several fastapi tasks are not scorable (E7) |
| 06-Nov 23:22 | 42311413061 | v2-smoke | v2 (PARSE→LOCATE→ATOMIZE→EXECUTE→VERIFY→FINALIZE), 2 tasks | 0/2; used up the 30 calls | Yes: too many steps |
| 06-Nov 23:43 | 42313735486 | v3-oracle | v3 (LOCATE + EDIT/CHECK loop + FINALIZE) on requests_6592 and requests_7315, plus oracle | requests_7315: patch identical to the official one but "not resolved" | Exposed E6 (src/ layout imported the system package) |
| 06-Nov 23:57 | 42315236982 | diag | Sandbox diagnostics, no GPU | Dumped the code: venv without pip, `PYTHONPATH=/workspace` | Yes |
| 07-Nov 00:01 | 42315632766 | oracle | Oracle on 4 tasks with the `src/` fix | 2/4 pass (requests_7315 and rich_3454); fastapi_14266 lacks `inline_snapshot`; requests_6592 with 185 errors | Yes |
| 07-Nov 00:07 | 42316310493 | oracle-129 | Oracle on the 129 public tasks | 78/129 pass → `data/scorable_tasks.json` | Yes |
| 07-Nov 00:35 | 42319201522 | (Leaderboard) | Public leaderboard | 1st 0.29; ~10 teams at 0.24; many at 0.22 | Yes |
| 07-Nov 00:39 | 42319504810 | v3-scorable12 | v3 on 12 scorable tasks | 0/12; 9 used up the 80 turns without a patch | Yes (E2, E3, E4: chained agents lose context) |
| 07-Nov 07:56 | 42353370659 | v5-smoke | v5 (v3 + `include_contents: none`), 2 tasks | 0/2; EDIT never calls `edit_file` in 45 calls | Yes (E2) |
| 07-Nov 08:48 | 42357027928 | base-e4b-smoke | Community agent (`variants/community_base`) with E4B, same 2 tasks | **2/2** (41 s and 118 s) | Yes: reference |
| 07-Nov 09:32 | 42360172615 | lab-01 | Probes 01: 15 single calls | Output block 0/3 vs no block 3/3; `tool_choice: required` returns empty; arguments broken by `:` | Yes, except the broken arguments (E9) |
| 07-Nov 09:43 | 42360919449 | battery-01 | Probes 02 + battery of 6 approaches × 8 tasks, E4B | All 0 | **No**: git "dubious ownership" (E8) |
| 07-Nov 09:52 | 42361521280 | battery-01-31b | Same with the 31B | Cancelled (the kernel kept running on Kaggle) | No (E8) |
| 07-Nov 10:05 | 42362476363 | battery-02-e4b | Battery with E8 fixed + capture of the harness kwargs + self-test, E4B | Control solved; harness self-test 3/3. Solved out of 8: localize_and_json 2, the rest 1 | **Yes** |
| 07-Nov 10:06 | 42362495002 | battery-02-31b | Same with the 31B | The workflow downloaded the output of the **old** kernel (battery 01 of the 31B, with the git failure): no `captura` | **No** (E14: same kernel name still running) |
| 07-Nov 10:19 | 42363450091 | battery-03-31b | Battery 02 fixed, with the 31B (capture + self-test + git fixed) | Controls OK (capture solved, harness self-test 3/3 and raw 3/3). Solved out of 8: one_plan_first 2, community 1, rest 0. 111/118 `edit_file` fail with 0 matches | Controls yes; **edit figures no (E15)**: the lab's `edit_file` is stricter than the official one |
| 07-Nov 12:03 | 42370774010 | bat-real-01-e4b | **Real harness**, multi-variant kernel: community_base vs nervo_repro, E4B, 14 scorable tasks (including rich_3454 and requests_7315) | **3/14 each.** nervo_repro: 14/14 with a patch, fewer calls and less time. nervo_repro failures: 8 wrong file, 3 right file but wrong change. Community: 6 and 4. **E4B fails mostly at localization** | **Yes** |
| 07-Nov 12:04 | 42370845784 | bat-real-01-31b | Same with the 31B, 8 tasks | **nervo_repro 6/8, community 5/8.** nervo_repro wins rich_2725 and uses fewer calls on requests. 31B failures: time (8 min) and wrong change, not localization | **Yes** |
| 07-Nov 13:24 | 42376946961 | ladder-01-e4b | e4b_guiado vs nervo_repro, E4B, the 8 easiest tasks of the difficulty ladder | **3/8 each.** e4b_guiado used the skill in 8/8 tasks (verdicts: 6 SUBMIT, 5 FIX, 2 NO_EDIT). On easy tasks the dominant E4B failure is a wrong change in the right file | **Yes** |
| 07-Nov 17:01 | — | **SUBMISSION 1** | `nervo_repro 31B v1, commit 733414e` (variants/nervo_repro_31b) | **0.18 public** (8 Nov). Below the group at 0.24. Our bench said 6/8: **not calibrated** | Yes |
| 08-Nov 16:46 | 42496460738 | e4b-t0-vs-t4096 | E4B: `e4b_t0` (thinking 0) vs `community_base` (thinking 4096), 14 scorable tasks, one vLLM. ~65 min run | **e4b_t0 2/14, community_base 4/14** (earlier control 3/14). Discordant: t0 wins 0, loses 2. Without reasoning edits do not break (13/14 with a patch) but fewer tasks are solved. **Does not confirm** the community's 16 vs 10 | Yes |
| 08-Nov 23:10 | 42528427422 | g31-steps-v4-batch1 | 31B, `g31_steps` v4, validation bench, 18 tasks. ~5 h of quota | **0/18**: the model called the skill `swe_agent` (the agent name ADK injects) instead of `steps` (653 SKILL_NOT_FOUND). See paper, Section 4.1 | No (mechanical failure) |
| 09-Nov 18:12 | 42662123059 | g31-steps-v7-isort | 31B, `g31_steps` v7 (skill `swe_agent`, not kebab-case), isort-891 only | Cancelled in the queue (it would fail loading the skill) | No |
| 09-Nov ~18:30 | 42667645366 | g31-steps-v8-isort | 31B, `g31_steps` prompt v8, isort-891 only | **Not solved**. Scripts OK (evidence, 3× show_function, save_check, verify) and it localizes `should_skip` with the right fix, but the `apply_edit` call arrives broken: the model does not close the long `blocks` text and vLLM's parser merges `file_path` into a garbage key → INVALID_ARGUMENTS in a loop up to 80 turns | Yes (format) |
| 09-Nov 19:03 | 42670592555 | e4b-steps-v9-isort | E4B, `e4b_steps` v9, isort-891 only. ~20 min of quota | **Not solved, but the first complete pipeline on Kaggle without format errors**: show_function ×5, apply_edit OK, verify, submit_patch (61 s, 8 calls). Dropped `skill_name` in the long call to evidence (twice) and skipped it; wrong fix (`import fnmatch`). verify falsely warned about pytest.ini/conftest.py (added by the harness) | Yes |
| 09-Nov ~19:35 | 42673741260 | e4b-steps-v10-isort | E4B, v10 (field order, retry on INVALID_ARGUMENTS, apply_edit infers the file, verify ignores harness files), isort-891 only. ~20 min of quota | **✅ SOLVED on Kaggle** (76 s, 7 useful calls). Lost `skill_name` in evidence and `skill_name`+`file_path` in apply_edit, but **repeated the full call** (v10 rule). Fix `fnmatch(os_path, glob)`. Skipped save_check | Yes |
| 09-Nov ~19:45 | 42676719254 | g31-steps-v10-isort | 31B, v10, isort-891 only (slot b). ~45 min of quota | **Not solved.** Fine up to `should_skip` and the case script; after the **harness compaction** (every 15 events) it asks for the evidence again from a summary, saves the script 6 times and repeats **the same call without `file_path` 64 times** up to 80 turns | Yes |
| 09-Nov ~19:50 | 42677347101 | e4b-steps-v11-dynaconf1184 | E4B, v11, dynaconf-1184 only. ~20 min of quota | **Not solved.** Evidence lost `skill_name`/`file_path`, then put the repository file in `file_path` (SCRIPT_NOT_FOUND); it abandoned the evidence and guessed. Saved an **empty** case script to pass `verify`. The line-number fix in apply_edit did work | Yes |
| 09-Nov ~21:00 | 42687234244 | e4b-cmd-v12-isort | E4B, `e4b_cmd` v12 (one skill call installs `.fixer/`; then run_command + write_file), isort-891 only. ~20 min of quota | **Not solved, but ZERO format failures** (14 calls, 78 s): install, write_file of the issue, evidence, show_function, callers, case script, edit, apply_edit, verify ×3, submit. Fix `check_skip=True` in `sort_imports` (part of the reference idea, not enough). verify found that its case script crashed and then a WRONG; the model submitted anyway | Yes |
| 09-Nov ~23:05 | 42708128706 | e4b-cmd-calibrate4 | E4B, `e4b_cmd` v12, 4 medium tasks (more-itertools-903, semver-254, api-core-821, traitlets-687) to calibrate the local bench (there 4/4). ~25 min of quota | **3/4 solved on Kaggle** (traitlets fails), **0 argument errors** in 65 calls, 60–122 s per task | Yes |
| 10-Nov ~00:50 | 42722453454 | g31-example-3 | 31B, `g31_example` (short path + the issue's example), 3 tasks (faker, jinja, semver), slot b. ~40 min of quota | **1/3 (semver)**, **0 format errors** in 24 calls, **25–65 s of agent time per task** (vLLM starts in 411 s). faker: the issue's example caught the half fix on Kaggle (FIX → corrected → OK) but the hidden test also needs sets; jinja: a different fix from the local run (sorting names), not enough | Yes |

A finding from the invalid 31B run that still holds: in the probes, `edit_file` arguments arrive intact 6 of 6 times with
the 31B (E4B: 0 of 6).

## How to read a battery JSON

```python
import json
d = json.load(open('output/nervo_results.json'))
d['stage']                       # 'done' if it finished
d['lab']['results']              # single probes: tool_calls, content, reasoning, seconds
b = d['bateria']                 # battery
b['captura']                     # capture: kwargs the harness uses to call the model + 'resolved' of the control task
b['autoprueba']                  # self-test: which way of calling keeps edit_file arguments intact; 'elegido' = chosen
b['resumen']                     # summary per approach: resueltas = solved, con_parche = with a patch, total
b['resultados']                  # per (approach, task): patch, resolved, pasos (each model call), notas (notes)
```

What to check first in a battery: `captura.resolved` must be `True` (the community agent solving rich_3454 with the real
harness is the control that the environment works), and `autoprueba.harness` must be `[True, True, True]` (arguments
intact when calling like the harness). Only then is the per-approach summary meaningful.

## 11 Nov 02:53 — E4B reasoning budget 12288 vs 4096, and 31B without reasoning (validation bench)
- Run 42942139772 (kernel `nervo-eval`, E4B): `community_base` (4096) and `com_t16` (12288, max_output 14336) on 6 tasks:
  jinja-1614, jinja-1702, pyflakes-675, click-2730, traitlets-773, babel-1196. Estimated cost ~1 h of kernel (~2 h of quota).
- Run 42942152723 (kernel slot b, 31B): `com31_t0` (public agent without reasoning) on 4 tasks: jinja-1614, pyflakes-675,
  click-2730, traitlets-773. Estimated cost ~30–40 min of kernel (~1–1.3 h of quota).
- **Result:** E4B `community_base` (4096) 1/6 and `com_t16` (12288) 1/6, only click-2730 in both; 31B `com31_t0` 1/4
  (click-2730), the other 3 use up the 28 calls. Kernel: E4B 26 min, 31B 17 min. The reasoning budget changes nothing: on
  Kaggle E4B generates ~200 tokens per call and only 2 of 76 calls exceed 4096.
- **Finding:** the quantized E4B on Kaggle **gives up early**: median 6.5–8.5 calls per task (14 tasks of 8 Nov: 12–18),
  against **26** for the same agent through the API locally. (The API runs were later found to be served by a 31B; see the
  paper, Section 4.6.) On traitlets-773 it edits blindly at call 7 (`Union.__init__`), the existing tests pass, it declares
  the fix correct and submits. The 31B on Kaggle uses 26–28 calls, as locally.

## 11 Nov 10:30 — `dossier` agent (dossier_e4b / dossier_31b) on Kaggle, same tasks as the night before
- **Result:** run 42984368076 `dossier_e4b` 1/6 (click-2730), run 42984383330 `dossier_31b` 1/4 (click-2730; pyflakes-675
  hits the 8-minute limit). Same as the public agent the night before. Kernel ~25 and ~36 min.
  The flow is followed (0 broken calls) and the edit location improves: E4B edits the function of the official fix in
  traitlets-773, babel-1196 and click; the 31B finds `CodeGenerator` in jinja-1614. But the change is wrong. Without a
  runnable example in the issue (traitlets, pyflakes), verification only has the existing tests and says SUBMIT to a wrong
  fix; with an example (jinja-1702) it says FIX and the model fails to correct it. The bottleneck is the content of the
  fix, not the context.

## 11 Nov 11:25 — Determinism on Kaggle (E4B, OFFICIAL development tasks)
- `community_base` (temperature 0.2) vs `com_det_a` and `com_det_b` (identical: temperature 0, top_p 1, seed 1234) on 8
  official tasks: fastapi_15589, fastapi_15800, rich_3777, rich_3894, rich_3905, rich_3942, rich_4006, rich_4077 (seed 11
  over the 72).
- **Result (run 43002548515):** `community_base` (0.2) 1/8, `com_det_a` 2/8, `com_det_b` 1/8. **Temperature 0 + seed does
  NOT give determinism on Kaggle:** 0 of 8 trajectories identical. With the SAME input (identical earlier output, same
  prompt tokens) the model answers differently at call 3–5 (e.g. rich_3894: 3437 vs 1548 generated tokens). Likely cause:
  vLLM is not batch-invariant (concurrent requests change GPU computations and break near-ties). It cannot be controlled
  from the submission. Consequence: measure with replicas, never with one run.
- Run 43001565097 (31B `dossier_31b` + same_change, reasoning 4096): 3/3 (jinja-1614, traitlets-773, click-2730). The
  same tasks gave 1/4 in the morning with the same variant without same_change: 31B results vary a lot between runs.

## 11 Nov 11:50 — 31B dossier at temperature 0 on OFFICIAL tasks (run 43006548634, slot b)
- `dossier_31b_t0` (temperature 0, seed 1234, reasoning 4096) on the same 8 official tasks as the E4B determinism test.
- **Result: 4/8** (rich_3777, 3894, 3905, 4077), against 1–2/8 for E4B on the same tasks. Failures: 2 hit the 8-minute
  limit (fastapi_15589, rich_4006), 1 the 80-turn limit (fastapi_15800), rich_3942 with a wrong fix.

## 11 Nov 12:45 — Public 31B reference and repetition of the 31B dossier, same 8 official tasks
- **11 Nov 12:35: WEEKLY GPU QUOTA USED UP** ("Maximum weekly GPU quota of 30.00 hours reached"). The two runs of 12:45
  did NOT execute. The workflow did not fail and saved as `31b-publico-oficiales` the PREVIOUS output of the kernel (the
  dossier t0 run): a false result, deleted. Fixed: the workflow now stops if the push fails.

## 11 Nov 16:20 — Submission: 31B `dossier_31b_t0` (commit 321b5e4)
- Same variant as run 43006548634 (4/8 on official tasks on Kaggle).
- Reference: 31B `nervo_repro` 0.18 (11/58) on 7 Nov. Noise of one submission: ±1.5 tasks; only a difference of 4+
  tasks says something.
- Public score: **0.17**, within the noise of the 0.18 of 7 Nov.
