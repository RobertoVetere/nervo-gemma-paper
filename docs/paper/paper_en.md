# The Prompt Proposes, the Code Decides

*A one-field interface makes a quantized Gemma 4 a reliable, fast coding agent. It does not make it smarter. We measure both, and what the quantized model fails to inherit from the original.*

## Abstract

Giving a small quantized model tools backed by its own code has a hidden cost: the model stops writing its calls correctly. In the competition's official harness, moving from flat tools to *skills* with scripts took Gemma 4 from 1 % to **88 % of calls rejected for format**.

We propose the **Nervo** protocol: *the prompt proposes, the code decides*. The model only writes one-line commands and puts long text in files; deterministic scripts locate, edit and verify by running code. With this interface, quantized (w4a16) E4B and 31B wrote **0 malformed calls out of 105 on Kaggle**, without reasoning.

We also measure what it does not achieve. On 40 random tasks, our E4B agent solves 16 in a 63 s median; a public agent with reasoning solves 20 in 162 s (p = 0.22). A 2×2 cross shows a clear interaction (p = 0.006): reasoning adds 6 tasks to the public agent and removes 6 from ours. The interface buys reliability and speed, not capability.

Using the exact exam weights, we measure what quantization changes: quantized E4B miscopies the text to replace twice as often, gives up after 6-8 calls instead of 26, and **loses the whole gain from reasoning** (9 → 5 fixes out of 22 in single calls). Conclusions drawn on the unquantized model do not transfer to the exam.

We release a 104-task bank validated by oracle, a bridge between the official harness and any API, a server for the official quantized model that costs cents, and a model-free context retriever.

## 1. Introduction

The *Gemma 4 Developer Agent* competition scores agents that fix real issues in Python repositories. Each task runs in a sandbox without network, with an 8-minute limit, 28 tool calls and 80 turns, and only counts if hidden tests pass. The model is quantized to 4 bits and served with vLLM on 4 L4 GPUs. The agent is declared in YAML over a closed registry of nine tools; the only custom code allowed is a *skill*'s scripts.

That is the tension. A 4B model edits poorly with flat tools: in our traces, 57 of its edits were not applied because it did not copy the text to replace exactly. Scripts fix that, but the call that invokes them has three fields and the quantized model breaks it. Another team measured the same symptom: without reasoning, 24 % of their calls were malformed, against 2.2 % with reasoning [usp787].

Our answer was to ask less of the model. Contributions:

1. **An interface rule** for small quantized models, with the taxonomy of the five format failures that motivated it (sections 3-4).
2. **An honest evaluation:** random sample, paired comparison, a 2×2 cross with reasoning, and negative results (section 7).
3. **A measurement of what is lost by quantizing**, with single calls to the official weights (section 8).
4. **Open infrastructure** to measure outside Kaggle with the official harness (section 6).

## 2. Origin: the Nervo protocol

Nervo predates this competition. It comes from **Nervo-Core**, a Go orchestrator for prompt chains. Each step is a *one-shot* call with a short, distinct prompt, and between steps sit **deterministic validators** (JSON contracts, imports, `py_compile`). A failed step is retried with the validator's error in front. Its lab compares a single call with the chain on **Qwen2.5-0.5B-Instruct**, over 16 arithmetic problems:

| Profile | Single call | Nervo chain | Won / lost |
|---|---|---|---|
| `math_short` | 25 % | **62.5 %** | 6 / 0 |
| `math_reasoning` (5 steps) | 31.25 % | **62.5 %** | 6 / 1 |
| Hard items only (5) | 20 % | 0-20 % | no gain |

Sixteen items are a hint, not proof, but they set the hypothesis: decomposing and validating doubles accuracy on what the model almost knows how to do, and adds no capability on what is hard. This competition tests it in a foreign environment, and the same pattern appears.

## 3. Method: the `fixer` agent

The agent is a single `LlmAgent`, without reasoning, with three tools from the official registry (`run_command`, `write_file`, `submit_patch`) and a skill of Python scripts.

**One-time install.** The only skill call (`run_skill_script`, empty `args`) copies the scripts to `.fixer/` inside the repository and adds that folder to `.git/info/exclude`, so it never enters the patch. From then on, every step is a one-field `run_command`.

**The scripts** do what a small model does badly:

- `evidence.py` reads the issue from `.fixer/issue.txt` and returns candidate functions: those in the traceback, the entry point of the quoted command, and the issue's strings found in the code.
- `show_function.py` and `callers.py` show a function, what it calls and who calls it.
- `apply_edit.py` applies whitespace-tolerant SEARCH/REPLACE blocks; on a mismatch it shows the closest real lines. It rejects edits whose REPLACE equals the SEARCH.
- `verify.py` runs the issue's example before and after the change, plus the model's cases, and returns a verdict: `SUBMIT`, `FIX` or `NO_EDIT`.

**`NEXT` lines.** Every script ends with the exact command for the next step. The harness summarizes the conversation every 15 events, and after the summary the model loses the prompt; the latest tool output is always present.

[DIAGRAM: fixer agent flow]

In *faker-2203*, the 31B guarded the first failing line and left the second; `verify.py` returned `original -> TypeError` / `with your fix -> AttributeError` / `VERDICT: FIX`, and the model corrected it. The model proposes sensible cases and judges them badly in its head; so whatever can be executed, the code executes.

## 4. Five ways to break a call, and one rule to avoid them

Every failure appeared on Kaggle with the quantized model, and none against commercial APIs: vLLM lets the model write the call as text and parses it afterwards, and that is where it breaks.

| Observed failure | Cause | Fix |
|---|---|---|
| Calls a skill by the agent's name: 653 `SKILL_NOT_FOUND`, 0 of 18 tasks | ADK injects "your internal name is X" in every request | Same name for agent and skill |
| The skill does not load | ADK only accepts *kebab-case* names | Validate the name before submitting |
| E4B writes the call as text and never runs it | It imitated the prompt's `run_skill_script(...)` notation | Describe each call as a list of fields |
| `skill_name` or `file_path` lost when an argument is long | The model does not close the string and the parser merges fields | **Long text through files**, with `write_file` |
| After ~7 calls, the 31B repeats the same incomplete call 64 times | Compaction erases the prompt | **One-field commands** and `NEXT` lines |

The rule: **each call, as few fields as possible and no long text inside.** Calls rejected for format in the Kaggle traces:

| Interface | Model | Calls | Rejected for format | Edits not applied |
|---|---|---|---|---|
| Flat tools (`edit_file`), reference agents | E4B | 810 | 12 (1.5 %) | 57 |
| Flat tools, reference agents | 31B | 459 | 3 (0.7 %) | 2 |
| Skill with a 3-field call | 31B | 930 | 819 (88 %) | 0 |
| Skill with a 3-field call and retry | E4B | 43 | 12 (28 %) | 1 |
| **One-time install + one-field commands** | E4B and 31B | 105 | **0** | 4 |

The one-field interface keeps the scripts and leaves **0 of 105** calls rejected, without reasoning (95 % upper bound: 2.8 %).

**Latency.** The quantized 31B generates about 33 tokens/s on 4 L4s: a call that runs a script (60 tokens) takes 4-5 s even when it reads 16,000; one that writes a change (950 tokens) takes 30 s. Time is set by what the model writes. Hence a **short path** for the 31B (no mandatory case script, `apply_edit.py` triggers verification): 25-65 s per task on Kaggle.

## 5. Model-free retrieval: the *dossier*

If locating is expensive for the model, let the code do it. `dossier.py` takes the issue and, without calling the model, builds a sectioned report, each section preceded by an instruction: where to look (functions in the execution trace of the issue's example, BM25 over function bodies, exact names), the candidates' code, sibling patterns in the same file, and the existing tests that touch them, with an explicit warning that passing them does not prove the fix. `mapa.py` gives a repository map of classes and methods; if the model names a symbol that does not exist, it gets the closest real ones back.

Against the official patch, with no model:

| Set | Fixed function in top 3 | File in top 3 | Issues with a runnable example |
|---|---|---|---|
| Bank, 40 random | 28 / 40 | 34 / 40 | 7 / 40 |
| Official dev tasks | 38 / 72 | 41 / 72 | **0 / 72** |

Official statements are pull-request descriptions, not issues: median 78 words against 112 in the bank, and 23 of 72 under 30 words (2 of 40 in the bank). None carries an example our extractor can run, so section 3's execution check never fires in the exam. It is a distribution shift that an issue bank does not measure.

## 6. A test bench outside Kaggle

With 30 GPU hours a week (ours ran out on 11 November) and one submission a day, iterating is impossible. We built four pieces that use the **unmodified official harness**:

1. **A 104-task bank** from 35 repositories other than the development ones, built from a public set (CC BY 4.0, [dmitriigluzdov]); we keep the tasks the official oracle solves on Kaggle (65 also locally).
2. **An inference bridge** (`shim_vllm.py`) that poses as vLLM to the harness and forwards to any OpenAI-compatible API, with a spending cap. A 40-task batch costs about 0.7 dollars.
3. **A Docker replica of the sandbox** (no network, 2 CPUs, 4 GB) rebuilt from the harness code.
4. **A server with the exam model** on Modal: the official `qat-w4a16-ct` weights, vLLM 0.19.1 and the Gemma 4 parsers, at the competition wheelhouse's versions. It shuts down after 5 idle minutes; section 8's probes cost cents.

**Noise.** With 58 public tasks, one task is worth 0.017 points; the most-submitted public agent varies by ±1.5 tasks across identical submissions [Afshar]. And runs are not reproducible: on Kaggle, with temperature 0 and a fixed seed, **0 of 8 trajectories** were identical; with the same input, the model diverges at call 3-5. vLLM is not batch-invariant and the zip cannot control it. Measure with samples, never with one run.

## 7. Results

**2×2 cross on 40 random tasks** (fixed seed over the 65 locally measurable; official harness; unquantized E4B through an API; one run per cell):

| E4B | No reasoning | Reasoning 4096 |
|---|---|---|
| Public agent (`edit_file`) | 14 / 40, 67 s | **20 / 40**, 162 s |
| `fixer` (one field + scripts) | **16 / 40**, 63 s | 10 / 40, 150 s |

95 % Wilson intervals range from 14-40 % (10/40) to 35-65 % (20/40). Three readings:

- **The interface does not solve more than the public agent.** Paired against the best public cell: 5 tasks only it solves, 1 only `fixer` solves (exact McNemar, p = 0.22). It is 2.5 times faster.
- **Reasoning interacts with structure.** It adds 6 tasks to the public agent and removes 6 from ours; in the per-task contrast, 11 favour the interaction and 1 goes against it (sign test, p = 0.006). With the steps already fixed by scripts, thinking adds loops (five tasks exhaust the 80 turns), not judgement.
- **The 31B on the short path solves 14**, all within E4B's 16. On the tasks we tuned it on it solved 7 of 8: tuning sets deceive.

Editing the public agent's prompt did not improve it: four variants on the 14 discriminating tasks scored 7, 8, 8 and 11, against 12 and 11 for the original in two repeats.

**Kaggle and exam**, with the quantized model:

| Where | Model | Agent | Result |
|---|---|---|---|
| Kaggle, bank (4 medium tasks) | E4B | `fixer` | 3 / 4 |
| Kaggle, 8 official tasks | E4B | public (3 runs) | 1, 2 and 1 of 8 |
| Kaggle, 8 official tasks | 31B | dossier, temperature 0 | **4 / 8** |
| Exam, public leaderboard (58) | E4B | public | 0.03 (2 tasks) |
| Exam, public leaderboard | E4B | `fixer` | 0.01 (1 task) |
| Exam, public leaderboard | 31B | earlier agent, no scripts | 0.18 (11 tasks) |

The 4/8 is a single run: its failures were two time-outs, one turn limit and one wrong fix. The 31B dossier variant at temperature 0.2 scored 1 of 4 and 3 of 3 in two runs on nearly the same bank tasks, hours apart.

**The bank-exam gap.** E4B solves 40-50 % of the local bank and 2-3 % of the exam. We ruled out the environment (Docker, call format, Python version). Three measured causes remain: official statements are poorer (section 5), quantized E4B gives up early and writes worse (section 8), and the bank used an unquantized model. A local bank compares versions with each other; it does not predict the score.

**What did not work**, besides reasoning in `fixer`: a final review step flagging what was missing (the model read it and submitted unchanged, 0 of 4); requiring cases to fail before the change (same successes, 3-4 times slower); and, on Kaggle, the dossier with E4B: it lands on the right function more often, but the change it writes is still wrong.

## 8. What the quantized model does not inherit

To separate the model from the agent, we made single calls to E4B: we supply the context, the model answers once, and the code scores with the hidden tests. Same questions, with unquantized weights (API) and the official quantized ones (our server):

| Single call, E4B | Unquantized | Quantized |
|---|---|---|
| Fix without reasoning (22 attempts, 11 hard tasks) | 5 | 5 |
| Fix with reasoning | **9** | **5** |
| Fix with existing tests as context, no reasoning | 5 | 6 |
| Attempts lost because SEARCH does not match the code | 12 of 88 | **24 of 88** |
| Symbol localization, 40 tasks: file list / map | 28 / 31 | 24 / 29 |

On Kaggle, the same public agent with quantized E4B uses a median of **6.5-8.5 calls per task, against 26** unquantized. In *traitlets-773* it edits blind at call 7, sees the existing tests pass and submits; unquantized, the same task is solved 2 of 2 with 27 calls.

Four conclusions. First, **reasoning no longer helps fixing** on the quantized model, and raising the budget to 12,288 tokens on Kaggle changed nothing (it generates about 200 per call). Second, the quantized model **miscopies the text to replace** twice as often, but that is not what costs it tasks: when it rewrites the whole function and the code swaps it by name, copy failures vanish and it solves the same (6 vs 5 of 18 attempts). What fails is the content of the change. Third, **the map still helps** (+5 symbols) and localization is not the bottleneck: with the right file, 55 of 64 attempts still fail. Fourth, existing tests add nothing. Everything we measured about reasoning on the unquantized model must be read next to this table.

## 9. Related work

**SWE-bench** [Jimenez et al.] set this evaluation's format: a real issue, a patch, hidden tests. **SWE-agent** [Yang et al.] showed that the agent-computer interface matters as much as the model. SWE-agent designs the interface so the model works comfortably; we design it so a small quantized model cannot write it wrong, and measure the effect in a foreign harness with the quantized weights.

### References

- [Jimenez et al.] C. E. Jimenez et al. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024.
- [Yang et al.] J. Yang et al. *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering.* NeurIPS 2024.
- [usp787] [Gemma4_paper_track](https://github.com/usp787/Gemma4_paper_track), a participant's repository: reasoning and malformed calls.
- [Afshar] D. Afshar, [Gemma 4: most-run public config averages 10/58](https://www.kaggle.com/code/dariushafshar/gemma-4-most-run-public-config-averages-10-58), Kaggle notebook.
- [dmitriigluzdov] [gemma-4-task-soundness-and-local-results](https://www.kaggle.com/datasets/dmitriigluzdov/gemma-4-task-soundness-and-local-results), Kaggle dataset, CC BY 4.0.

## 10. Conclusion

With a small quantized model, the interface decides whether the agent works; it does not decide how much it solves. Four rules hold beyond this competition:

1. **One field per call; long text through files.** From 88 % of calls rejected to none.
2. **Whatever can be executed, let the code execute it**, and whatever can be searched, let the code search: the dossier puts the right function in the top three for half the official tasks without spending a call.
3. **Do not treat reasoning as a fixed gain.** It interacts with the agent's structure and vanishes when quantized.
4. **Measure with random, paired samples and the exam's weights.** Our tuning tasks said 7 of 8; chance said 14 of 40; the quantized model, something else.

It is the pattern we saw in Nervo-Core with a 0.5B model: structure and validation make reliable what the model already knows how to do, and do not give it what it lacks.

## Reproduce

Everything is in the [repository](https://github.com/RobertoVetere/nervo-gemma-paper) (tag `paper-v1`): agents in `variantes/`, per-task results in `resultados/`, every Kaggle run in `docs/HISTORIAL_EJECUCIONES.md`, and the single-call probes in `lab/oneshot/`. The 2×2 cross is regenerated at no cost from the saved results with `python3 local/tabla_lote.py resultados/local_deepinfra/l40`; `docs/REPRODUCIR.md` details the setup and each figure.
