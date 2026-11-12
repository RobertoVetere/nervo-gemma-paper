> **Read first: two corrections apply to everything in this file.**
> 1. **10 Nov 13:45:** until that moment `local/run_local.py` always forced the 31B model in the variant (a leftover from
>    AI Studio), and the bridge picks the model by that name: 913 of 914 bridge calls went to the 31B. Fixed (the variant's
>    model is now used; `--force-31b` restores the old behaviour).
> 2. **12 Nov:** DeepInfra answered requests for `google/gemma-4-E4B-it` with `google/gemma-4-31B-it-turbo` (`replaced_by`
>    on the model page; the `model` field of the response says so; the bill matches 31B-turbo prices), from at least
>    10 Nov. So **every row labelled "E4B" below was answered by a 31B**, even where the bridge log shows requests to E4B.
>    The paper labels these results "31B (API)". Real E4B results: `results/modal_e4b_4bit/` (official 4-bit weights)
>    and the bf16 runs listed in `docs/REPRODUCE.md`.

# Local batches through the API (DeepInfra), 9–10 Nov

Official harness run locally (`local/run_local.py`) + `local/shim_vllm.py --backend deepinfra`. Real 8-minute limit (no
`--minutes`). Total spend on the first night: ~1.6 USD.

## 4 medium tasks (in parallel, 8 processes)
| task | e4b_cmd (no reasoning) | e4b_cmd_t (reasoning) |
|---|---|---|
| python-api-core-821 | ✅ 15 calls 229 s | ✅ 13 calls 159 s |
| traitlets-687 | ✅ 18 calls 196 s | ✅ 12 calls 133 s |
| more-itertools-903 | ✅ 13 calls 197 s | ✅ 10 calls 117 s |
| python-semver-254 | ✅ 11 calls 147 s | ✅ 12 calls 152 s |

## 13 hard tasks (13 processes at once on 2 CPUs: times are inflated)
**e4b_cmd 4/13** (bump-my-version-180, faker-2203, click-2730, jinja-2022) · **e4b_cmd_t 2/13** (click, jinja).
- With reasoning, 8 of 13 hit the 8-minute limit (calls p50 2.6 s, p90 25 s). Confound: 13 processes at once. Not
  conclusive about reasoning, but time is a real risk.
- dynaconf-1184 (issue of 6,428 characters): the model takes 275 s to write the issue with `write_file` and the call comes
  out without `filepath`. **Copying the whole issue does not scale**: median 951 characters, p90 2,694, 7 of 104 above 3,000.

## v13 (`e4b_v13`: cases also run on the original code + a round limit + summarized issue) — STOPPED
8 hard tasks finished: **3/8, same as v12** (faker, click, jinja), winning and losing none, but **3–4 times slower**
(375–427 s, close to the 8-minute limit). Stopped: it gains nothing. v12 stays as the candidate.
Total DeepInfra spend that night: ~2.05 USD.

## Diagnosis of the 9 v12 failures (model patch against the official one)
- **Unfair (the issue does not ask for what the hidden tests require):** markdownify (fix identical to the official one;
  `test_q` fails, another function), pyflakes (fixes the order; TypeVar tests fail), pypika (adds `select`; tests also
  ask for `update`/`insert`), cookiecutter (tests ask for a `hooks_dir` parameter), isort.
- **Ours:** babel (REPLACE == SEARCH, apply_edit said OK → empty patch; **fixed in v12.1**), dynaconf (6,428-character
  issue: not copied), markdown (repeats the same command 10 times without editing), traitlets.

## v12.1 (apply_edit rejects REPLACE == SEARCH) on our 4
traitlets ✅, babel ❌ (now applies a real, wrong fix), markdown ❌, dynaconf ❌ (hangs on the long issue). Cost 0.16 USD.

## e4b_rev (REVIEW step with review.py) on the 4 unfair ones — DISCARDED
0/4. review.py points out what is missing (pypika: Query.into/update; cookiecutter: hooks_dir), but the model reads the
review and submits without extending the fix. Cost 0.14 USD.

**Total DeepInfra spend 9–10 Nov: ~2.35 USD.**

## 31B (DeepInfra), 8 tasks — 10 Nov 00:30
Estimated Kaggle time = tokens written / 33 tok/s + 5 s per call (measured on 31B traces from Kaggle).
```
g31_cmd     callowayproject__bump-my-version-180     OK calls=28 output_tokens= 4193 kaggle_estimate= 267s
g31_cmd     googleapis__python-api-core-821          -- calls=11 output_tokens= 1783 kaggle_estimate= 109s
g31_cmd     ipython__traitlets-687                   OK calls=21 output_tokens= 4178 kaggle_estimate= 232s
g31_cmd     joke2k__faker-2203                       -- calls=11 output_tokens= 1842 kaggle_estimate= 111s
g31_cmd     more-itertools__more-itertools-903       OK calls=10 output_tokens= 2375 kaggle_estimate= 122s
g31_cmd     pallets__click-2730                      OK calls=12 output_tokens= 2988 kaggle_estimate= 151s
g31_cmd     pallets__jinja-2022                      OK calls=28 output_tokens= 5631 kaggle_estimate= 311s
g31_cmd     python-semver__python-semver-254         OK calls=12 output_tokens= 2027 kaggle_estimate= 121s
g31_rapido  callowayproject__bump-my-version-180     OK calls=12 output_tokens=  998 kaggle_estimate=  90s
g31_rapido  googleapis__python-api-core-821          -- calls=10 output_tokens= 1480 kaggle_estimate=  95s
g31_rapido  ipython__traitlets-687                   OK calls= 6 output_tokens=  798 kaggle_estimate=  54s
g31_rapido  joke2k__faker-2203                       -- calls= 5 output_tokens=  546 kaggle_estimate=  42s Agent exceeded session timeout
g31_rapido  more-itertools__more-itertools-903       OK calls= 5 output_tokens=  530 kaggle_estimate=  41s
g31_rapido  pallets__click-2730                      OK calls= 6 output_tokens= 1046 kaggle_estimate=  62s
g31_rapido  pallets__jinja-2022                      OK calls= 6 output_tokens= 1068 kaggle_estimate=  62s
g31_rapido  python-semver__python-semver-254         OK calls= 6 output_tokens=  683 kaggle_estimate=  51s
```
(`g31_rapido` = fast path.)

## g31_example (short path + the issue's example) vs g31_rapido, 31B DeepInfra, 8 tasks — 10 Nov 00:50
```
callowayproject__bump-my-version-180     fast: OK 12 calls ~90s            example: OK 12 calls ~92s
googleapis__python-api-core-821          fast: -- 10 calls ~95s            example: -- 10 calls ~97s
ipython__traitlets-687                   fast: OK 6 calls ~54s             example: OK 6 calls ~53s
joke2k__faker-2203                       fast: -- 5 calls ~42s (timeout)   example: OK 13 calls ~155s
more-itertools__more-itertools-903       fast: OK 5 calls ~41s             example: OK 5 calls ~43s
pallets__click-2730                      fast: OK 6 calls ~62s             example: OK 6 calls ~64s
pallets__jinja-2022                      fast: OK 6 calls ~62s             example: OK 5 calls ~57s
python-semver__python-semver-254         fast: OK 6 calls ~51s             example: OK 6 calls ~49s
fast 6, example 7 of 8; spent 0.098564 USD
```
**g31_example 7/8, wins faker and loses none.** On 40 random tasks it drops to 14/40 (below): the 7/8 had selection bias
(paper, Section 4.6).

## Bridge log showing 217/217 calls requested as gemma-4-e4b, v12.1, subprocess sandbox — 10 Nov 14:00
**5/9**: bump-my-version, more-itertools, click, jinja, semver ✅; api-core, traitlets, faker, babel ❌. 80–190 s per task,
11–28 calls. 0.11 USD. (Answered by a 31B: see correction 2 above.)
On the competition test v12 scored 0.01: the local bench overestimates a great deal.

## Same, in the DOCKER REPLICA of the evaluation sandbox (local/docker/, `--sandbox docker`) — 10 Nov 14:40
The 5 tasks solved with the subprocess sandbox: **4/5 in Docker** (semver, click, more-itertools, jinja ✅;
bump-my-version ❌, 28 calls). 0.05 USD.
**The Docker environment does NOT explain the 0.01 on the test**: scripts, `.fixer/`, tests and times behave the same.

## Batch of 40 tasks (random sample, seed 10, of the 65 scorable locally) — 10 Nov 17:00
DeepInfra, subprocess sandbox, real 8-minute limit. 1,899 calls requested as E4B, 627 as 31B. Spend 2.00 USD.

| Agent | Model requested | Solved | 95% CI (Wilson) | Calls (median) | Seconds (median) |
|---|---|---|---|---|---|
| `community_base` (public agent, reasoning 4096, `edit_file`) | E4B | **20/40 (50%)** | 35–65% | 26 | 162 |
| `e4b_cmd` (v12, no reasoning) | E4B | 16/40 (40%) | 26–55% | 19 | 63 |
| `g31_example` (short path + example) | 31B | 14/40 (35%) | 22–50% | 11 | 85 |

Paired: only v12 1, only public 5, both 15. v12 is 2.5 times faster and uses fewer calls.

## 10 Nov — v12 with reasoning (`e4b_cmd_t`), same 40 tasks (seed 10)
| Agent | Model requested | Solved | Median | Limit hits |
|---|---|---|---|---|
| community_base (public, reasoning 4096) | E4B | 20/40 | 162 s | 0 |
| e4b_cmd v12 (no reasoning) | E4B | 16/40 | 63 s | 2 time |
| e4b_cmd_t v12 + reasoning 4096 | E4B | **10/40** | 150 s | 2 time + 5 at the 80-turn limit |
| g31_example | 31B | 14/40 | 85 s | 2 |

Paired: t vs v12 → only t 1, only v12 7. t vs public → 1 / 11. 1,191 calls; 0.67 USD.

## 10 Nov 20:00 — Public agent without reasoning (`e4b_t0`), same 40 tasks: the 2×2
| Model requested: E4B (answered by 31B-turbo) | No reasoning | Reasoning 4096 |
|---|---|---|
| Public agent (`edit_file`) | 14/40 (`e4b_t0`, 67 s) | **20/40** (`community_base`, 162 s) |
| `fixer` v12 (one field + scripts) | **16/40** (`e4b_cmd`, 63 s) | 10/40 (`e4b_cmd_t`, 150 s) |

Reasoning adds 6 to the public agent and removes 6 from ours. Per-task interaction contrast
[(pub_t − pub_0) − (fixer_t − fixer_0)]: 11 tasks in favour, 1 against, sign test p = 0.006. This is replica 1 of the
three in the paper (Section 4.4); replicas 2 and 3 are `l40_r2` and `l40_r3`.
834 calls; 0.39 USD. Full table: `python3 local/batch_table.py results/local_deepinfra/l40`.

## 10 Nov 20:15 — com_v1 (public + git grep -W + first answer a tool call) on the 14 "edge" tasks — DISCARDED
com_v1 8/14 against public 12/14 (its results in the 40-task batch). Only com_v1 0, only public 4. 0.22 USD.
Reading whole functions does not save calls: it invites more reading.
Note: the edge set was chosen with the public agent's results (12/14 in its favour), so the comparison is biased
against any new variant.

## 10 Nov 20:40 — com_v2 (public + the issue's example before and after) on the edge set
com_v2 7/14 against public 12/14. Only com_v2: faker-2203. Only public: dynaconf-811, traitlets-727, traitlets-773,
more-itertools-926, babel-1196, semver-239.

## 10 Nov 21:00 — Public agent repeated on the edge set: 11/14 (before 12/14)
The public agent is stable (12 and 11): noise of ±1 task in 14. com_v1 (8) and com_v2 (7) are really worse.
Both variants lose traitlets-773 and babel-1196, which the public agent wins both times: they submit a wrong patch.
Lesson: the public prompt is already well tuned; adding instructions takes calls and attention away. 0.21 USD.

## 10 Nov 21:30 — com_v3 (public, "understand before editing": edit by call 18 at the latest) on the edge set
com_v3 11/14, same as the public agent (12 and 11). Wins faker-2203 (never won by the public agent), dynaconf-811 and
pyflakes-675; loses traitlets-773 and semver-239. A tie.

## 10 Nov 22:00 — com_v4 (public + repomap skill as first step) on the edge set — DISCARDED
com_v4 8/14 against public 12 and 11. The agent did NOT install the skill in any task (0/14 calls to run_skill_script):
in 3 calls it tried `python3 .fixer/map.py` directly and failed. The model with reasoning does not follow a two-step
setup instruction, and adding steps to the public prompt costs solved tasks (fourth time: com_v1 8, com_v2 7, com_v3 11,
com_v4 8). 0.31 USD.
