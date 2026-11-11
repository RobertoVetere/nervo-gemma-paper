# The Prompt Proposes, the Code Decides: Interface Design for Small Quantized Code Agents

## Abstract

Small language models served with 4-bit weights are attractive for local coding agents, but how they should be wired into an agent is poorly understood. We study Gemma 4 E4B and 31B (w4a16) as repository-repair agents under hard limits on time, tool calls and turns, scored by hidden tests. We report four results, of uneven strength. (1) Tool calls break in five recurring ways; an interface in which every call has a single field and long text travels through files reduces rejected calls from 88% to 0 of 105. (2) Reasoning is not a fixed gain: on 40 random tasks it adds six solved tasks to a free-form agent and removes six from a script-guided one (interaction, sign test p = 0.006, one run per cell). (3) Quantization is not neutral: with identical inputs, the quantized E4B miscopies the code to replace twice as often (24 vs 12 of 88 attempts, p = 0.04), and the reasoning gain seen at full precision on single-call fixes (5 → 9 of 22) does not appear (5 → 5), a small-sample observation consistent with agent-level runs. (4) Common evaluation practices mislead: tuning sets inflate success (7/8 vs 14/40 on random tasks), runs are not reproducible even at temperature 0, and issue-based benchmarks differ from terse pull-request descriptions in ways that disable execution-based checks. We release the agents, a 104-task oracle-validated benchmark, a bridge that runs the official evaluator against any API, and a server for the exact quantized weights.

## 1. Introduction

Coding agents are usually built for large models behind commercial APIs. A small model running locally, quantized to fit modest hardware, changes the problem: it formats tool calls less reliably, edits less precisely, and its time budget is consumed by the tokens it writes. Which design choices transfer to this regime is largely untested.

We take a design stance we call *the prompt proposes, the code decides*. The model chooses what to change; deterministic scripts locate code, apply edits and run checks, and their verdicts, not the model's self-assessment, decide what happens next. The stance comes from an earlier prompt-chaining harness in which validating each step raised a 0.5B model from 25% to 62.5% on 16 arithmetic problems, without helping on the five hardest.

We evaluate this stance on repository repair: given an issue and a repository snapshot, produce a patch that passes hidden tests. Our contributions are measurements rather than a leaderboard result:

1. A taxonomy of tool-call failures of quantized models and an interface rule that removes them (Section 4.1).
2. Evidence that reasoning interacts with agent structure (Section 4.2).
3. A comparison of quantized and full-precision weights on identical inputs (Section 4.3), small but matched.
4. A model-free retriever and an analysis of where the remaining failures lie (Section 4.4), and three evaluation pitfalls (Section 5).

## 2. Setting

**Task.** Each instance is a real Python repository at a fixed commit, an issue text, and hidden fail-to-pass and pass-to-pass tests. An instance is solved if the agent's patch makes all of them pass. Agents run in a network-less sandbox with limits of 8 minutes, 28 tool calls and 80 model turns.

**Models and serving.** Gemma 4 E4B and Gemma 4 31B, with 4-bit weights and 16-bit activations (w4a16), served by vLLM 0.19.1 on four NVIDIA L4 GPUs with the Gemma 4 tool-call and reasoning parsers and a 32k context.

**Agent framework.** Agents are declared in YAML on Google's Agent Development Kit and may only use a closed set of nine tools (shell command, file read/write/edit, patch submission and code-graph queries). The only custom code allowed is the scripts of a *skill*, invoked through a three-field call. The framework summarizes the conversation every 15 events. This is the setup of the Kaggle *Gemma 4 Developer Agent* competition, whose official evaluator we use unmodified.

**Data.** *Bank*: 104 instances from 24 repositories, drawn from a public CC BY 4.0 collection [4] and kept only if the official oracle solves them with the reference patch; 65 are also solvable in our local environment. *Official*: 72 locally measurable development instances from three repositories. Unless stated otherwise, comparisons use the same instances for every condition and are paired.

## 3. Design

The `fixer` agent has three tools (`run_command`, `write_file`, `submit_patch`) and one skill. Its single skill call copies the scripts into a git-ignored folder inside the repository; from then on every step is a one-field shell command:

- `evidence.py` reads the issue from a file and lists candidate functions (from tracebacks, the entry point of any quoted command, and issue strings found in the code);
- `show_function.py` and `callers.py` show a function, what it calls and who calls it;
- `apply_edit.py` applies whitespace-tolerant search/replace blocks and, on a mismatch, shows the closest real lines;
- `verify.py` runs the issue's own example before and after the change and returns `SUBMIT`, `FIX` or `NO_EDIT`.

Every script ends with a `NEXT:` line naming the exact next command, because after a summary the model no longer sees its instructions but always sees the last tool output.

[FIGURE 1: the fixer flow — install, issue to file, evidence, edit, verify, decide]

Execution replaces judgement where possible. In one instance the 31B guarded the first failing line of an issue's example and missed the second; `verify.py` reported `original → TypeError`, `with your fix → AttributeError`, `VERDICT: FIX`, and the model completed the fix.

## 4. Results

### 4.1 Tool calls break in predictable ways

We observed all five in runs with the quantized model. The first two stem from framework conventions; the last three from how the model writes calls when vLLM parses them out of free text, and they did not appear when the same agents ran against a commercial API that returns structured calls.

| Failure | Cause | Remedy |
|---|---|---|
| Skill called by the agent's name (653 errors, 0 of 18 tasks) | The framework injects "your internal name is X" into every request | Same name for agent and skill |
| Skill not loaded | Only *kebab-case* names are accepted | Validate names before running |
| Call written as text and never executed | The model imitated code-like call notation in the prompt | Describe calls as field lists |
| Fields lost when an argument is long | The model does not close the string; the parser merges fields | Long text through files |
| The same incomplete call repeated 64 times | Summarization erases the prompt | One-field commands and `NEXT` lines |

| Interface | Model | Calls | Rejected for format | Edits not applied |
|---|---|---|---|---|
| Flat tools (`edit_file`) | E4B | 810 | 12 (1.5%) | 57 |
| Flat tools | 31B | 459 | 3 (0.7%) | 2 |
| Skill, three-field call | 31B | 930 | 819 (88%) | 0 |
| Skill, three-field call (three prompt versions) | E4B | 43 | 12 (28%) | 1 |
| **One-time install + one-field commands** | E4B, 31B | 105 | **0** (95% upper bound 2.8%) | 4 |

Flat tools rarely fail on format, but the small model loses edits because it does not reproduce the text to replace. Scripts fix the edits, yet the call that invokes them collapses. The one-field interface keeps the scripts and removes format failures, without reasoning.

### 4.2 Reasoning interacts with agent structure

We crossed two agents with two reasoning settings on 40 bank instances sampled with a fixed seed, using unquantized E4B through an API and the official evaluator (one run per cell).

| E4B, 40 tasks | No reasoning | Reasoning (4,096 tokens) |
|---|---|---|
| Free-form agent (`edit_file`) | 14 (67 s) | **20** (162 s) |
| `fixer` (scripts, one-field calls) | **16** (63 s) | 10 (150 s) |

*Solved tasks; median seconds per task. Wilson 95% intervals span 14–40% (10/40) to 35–65% (20/40).*

The best cells do not differ significantly (5 tasks solved only by the free-form agent, 1 only by `fixer`; exact McNemar p = 0.22), but `fixer` is 2.5 times faster. Reasoning moves the two agents in opposite directions: in the per-task contrast (gain of the free-form agent minus gain of `fixer`), 11 tasks favour the interaction and 1 opposes it (sign test, p = 0.006). With reasoning, `fixer` hit the turn limit on five tasks (none without it): when the steps are already fixed by scripts, thinking adds loops rather than judgement.

![Figure 2: solved tasks out of 40 by agent and reasoning setting. The lines cross: reasoning helps the free-form agent and hurts the script-guided one.](fig_interaction.png) A shortened `fixer` driving the 31B solves 14, all within the 16 of the small model: on these instances model size did not substitute for interface.

Prompting changes did not help the free-form agent: four variants (reading whole functions, running the issue example, "understand before editing", a repository map) solved 7, 8, 8 and 11 of 14 discriminating instances, against 12 and 11 for the original in two repeats (the instances were chosen using the original's results, which favours it).

### 4.3 What quantization changes

To separate model from agent, we made single calls in which we supply the context, the model answers once, and the hidden tests score the answer. We asked identical questions to the full-precision E4B and to the official w4a16 weights served with the same vLLM version.

| Single call, E4B | Full precision | w4a16 |
|---|---|---|
| Fix, no reasoning (22 attempts, 11 instances) | 5 | 5 |
| Fix, with reasoning | **9** | **5** |
| Fix, existing tests added to the context | 5 | 6 |
| Attempts lost because the search text does not match the code | 12 of 88 | **24 of 88** |
| Localization over 40 tasks, symbol correct: file list / repository map | 28 / 31 | 24 / 29 |

With 22 attempts per cell, the difference in reasoning gain (+4 vs 0) is not significant on its own (9/22 vs 5/22, Fisher p = 0.33); the copy failures are (24/88 vs 12/88, p = 0.04), and localization differences are not. Two agent-level observations point the same way as the reasoning result. Raising the reasoning budget to 12,288 tokens inside the free-form agent changed nothing (1 of 6 tasks in both settings): the quantized model wrote about 200 tokens per call and only 2 of 76 calls exceeded 4,096. And the quantized E4B inside the free-form agent used a median of 6.5 to 18 calls per task in four runs, against 26 at full precision on the 40-task sample; the task sets differ, but on the one instance present in both, the quantized model edited blindly at call 7, saw the existing tests pass and submitted a wrong patch, while the full-precision model solved it in both runs with 27 calls.

Conclusions about reasoning drawn on full-precision weights should therefore be re-checked on the deployed weights before they are trusted.

### 4.4 Where the remaining failures are

**Localization is not the bottleneck.** A model-free retriever (`dossier.py`) builds a sectioned report from the issue: functions in the execution trace of the issue's example, BM25 over function bodies, exact identifier matches, the candidates' code, sibling implementations in the same file, and the existing tests that touch them, each section preceded by an instruction (for tests: passing them does not prove the fix). Against the reference patches, it ranks the changed function in its top three for 28 of 40 bank instances and 38 of 72 official ones, at zero model cost. With the right file in hand, 55 of 64 single-call fix attempts of the quantized E4B still fail.

**Nor is the edit format.** Since the quantized model miscopies search text twice as often, we let it rewrite the whole function and replaced it by name in code. Copy failures vanished, but solved attempts stayed level (6 vs 5 of the 18 attempts where the target was a function). What fails is the content of the change.

**Model size helps there.** With the 31B, an agent built on the retriever solved 4 of 8 official instances in a single run, against 1–2 of 8 for the small model with the free-form agent over three runs. These are single small runs; we report them as a direction, not a result.

## 5. Evaluation pitfalls

**Tuning sets inflate.** The 31B agent solved 7 of the 8 instances used to design it and 14 of 40 random ones.

**Runs are not reproducible.** With temperature 0, `top_p` 1 and a fixed seed, 0 of 8 trajectories were identical across two runs on the same instances; identical inputs diverged at call 3–5. vLLM's batched kernels are not batch-invariant, and no client setting controls this. Single runs must be read as samples.

**Benchmarks differ from deployment.** The official instances are pull-request descriptions, not issues: median 78 words against 112 in the bank, 23 of 72 under 30 words (2 of 40 in the bank), and none with an example our extractor can run (7 of 40 in the bank). Execution-based checks such as `verify.py` therefore never trigger on them. With full-precision weights, the small model solved 40–50% of the bank; with the deployed weights, the same agents scored 0.01 and 0.03 on a held-out set of 58 instances (roughly 1–2 solved). The environment did not explain the gap (a Docker replica of the sandbox reproduced 4 of 5 bank results), which leaves the statements and the weights. A local benchmark ranks versions; it does not predict deployment.

## 6. Related work

SWE-bench [1] defined repository repair with hidden tests; SWE-agent [2] showed that the agent–computer interface matters as much as the model. Our work shares that thesis but targets the opposite end: an interface designed so that a small quantized model cannot write it wrong, measured with the deployed weights. Our reasoning results add to evidence that test-time thinking helps tool formatting in small models [3], and show that its value depends on the agent's structure and on quantization.

## 7. Limitations

Most comparisons use one run per condition on 40 or fewer instances, so only large effects are detectable, and runs are not reproducible (Section 5). The 2×2 cross used full-precision weights; Section 4.3 suggests its reasoning effect would shrink with the deployed model. The two agents in the cross differ in more than reasoning. The single-call probes cover 11 instances with two samples each, too few for the reasoning difference to be significant. All results are for one model family and one agent framework.

## 8. Conclusion

For small quantized models, the interface decides whether an agent works, not how much it solves. Single-field calls with text in files make tool use reliable; scripts make localization and verification cheap; neither fixes the content of the change, which is where the remaining failures are. Reasoning and quantization interact with these choices, so agent designs should be validated with the deployed weights, on random samples, with paired comparisons and repeated runs.

## Reproducibility

Code, agents, data and per-task results: https://github.com/RobertoVetere/nervo-gemma-paper (tag `paper-v1`). `docs/REPRODUCIR.md` maps every number to a file and a command; the 2×2 table regenerates at no cost with `python3 local/tabla_lote.py resultados/local_deepinfra/l40`.

## References

[1] C. E. Jimenez et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.
[2] J. Yang et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 2024.
[3] usp787. Gemma4_paper_track. https://github.com/usp787/Gemma4_paper_track
[4] D. Gluzdov. gemma-4-task-soundness-and-local-results (dataset, CC BY 4.0). Kaggle.
