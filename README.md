<div align="center">

# The Prompt Proposes, the Code Decides

**Interface Design for Small Quantized Code Agents**

Roberto Vetere · Independent researcher

[Paper (EN)](docs/paper/paper_en.md) · [Paper (ES)](docs/paper/paper_es.md) · [Reproduce](docs/REPRODUCE.md) · [Data](datos/banco_nuevo/) · [Results](resultados/)

</div>

---

Small language models with 4-bit weights can run coding agents on modest hardware, but the design rules for large models
do not carry over. This repository contains the agents, data, infrastructure and per-task results behind a study of
**Gemma 4 E4B and 31B (w4a16)** as repository-repair agents: given an issue and a repository, produce a patch that
passes hidden tests, under hard limits of 8 minutes, 28 tool calls and 80 turns.

The design stance is simple: **the model proposes what to change; deterministic scripts locate code, apply edits and
run checks, and their verdict decides what happens next.**

## Results at a glance

| Question | Result | Evidence |
|---|---|---|
| Can a quantized model drive scripted tools reliably? | With one-field calls and long text passed through files, **0 of 105** calls were rejected, against **81–88%** with a three-field call | Successive agent versions, evaluation traces |
| Does reasoning help? | It depends on the agent: **+6 tasks** for a free-form agent, **−6** for a script-guided one | Exploratory: 40 random tasks, one run per cell, sign test **p = 0.006** |
| Does quantization change behaviour? | In single-call probes the quantized model generates **a third as many tokens** when reasoning and fails **twice as many edits** by miscopying code (24 vs 11 of 88, p = 0.02) | Same pipeline; localization not held fixed |
| Is localization the bottleneck? | No. With the right file in hand, **55 of 64** repair attempts still fail; rewriting whole functions removes copy errors but not wrong changes | Single-call probes, hidden tests |
| Can single runs be trusted? | No. At temperature 0 with a fixed seed, **0 of 8** trajectories repeated | Two runs on the same tasks |

<p align="center">
  <img src="docs/paper/fig_interaction.png" width="460" alt="Solved tasks out of 40: reasoning helps the free-form agent and hurts the script-guided one">
</p>

## What is in this repository

| Path | Contents |
|---|---|
| [`docs/paper/`](docs/paper/) | The paper, in English and Spanish, and its figure |
| [`variantes/`](variantes/) | Every agent compared in the paper, in the competition's submission format (`agent.yaml`, prompts, skills with scripts) |
| [`datos/banco_nuevo/`](datos/banco_nuevo/) | 104 repair tasks from 24 repositories, each validated with the official oracle (65 also run locally), derived from a CC BY 4.0 dataset |
| [`local/shim_vllm.py`](local/shim_vllm.py) | A bridge that poses as the vLLM server to the official evaluator and forwards to any OpenAI-compatible API, with a spending cap |
| [`local/correr_local.py`](local/correr_local.py) | Runs the official evaluator locally, with a subprocess sandbox or a Docker replica of the evaluation sandbox ([`local/docker/`](local/docker/)) |
| [`local/modal_vllm.py`](local/modal_vllm.py) | Serves the exact quantized weights (vLLM 0.19.1, Gemma 4 parsers) on [Modal](https://modal.com), scaling to zero when idle |
| [`local/modal_eval.py`](local/modal_eval.py) | Runs a full evaluation on four L4 GPUs on Modal, matching the competition environment |
| [`lab/oneshot/`](lab/oneshot/) | Single-call probes: localization and repair with full-precision vs quantized weights |
| [`resultados/`](resultados/) | Per-task JSON results of every run cited in the paper |
| [`scripts/`](scripts/) | Submission builder and validator, and the evaluation kernel |
| [`docs/REPRODUCE.md`](docs/REPRODUCE.md) | Where every number in the paper comes from, and how to regenerate it |
| [`docs/HISTORIAL_EJECUCIONES.md`](docs/HISTORIAL_EJECUCIONES.md) | Log of every evaluation run (Spanish) |

## Reproduce

Check the main table from the saved results, at no cost:

```bash
python3 local/tabla_lote.py resultados/local_deepinfra/l40   # 2x2 table, Wilson intervals, McNemar tests
python3 local/interaccion.py                                   # interaction sign test
python3 lab/oneshot/resumen_cuantizacion.py                    # single-call probes, quantized vs unquantized
```

Re-running agents requires the official evaluator wheels (`swegemma`, `adk_eval_core`, `adk_submission`,
`google-adk==1.36.1`) and an OpenAI-compatible endpoint serving Gemma 4. [`docs/REPRODUCE.md`](docs/REPRODUCE.md)
maps every number in the paper to the file and command that produce it.

## Citation

```bibtex
@misc{vetere2026promptproposes,
  author       = {Roberto Vetere},
  title        = {The Prompt Proposes, the Code Decides: Interface Design for Small Quantized Code Agents},
  year         = {2026},
  howpublished = {\url{https://github.com/RobertoVetere/nervo-gemma-paper}},
  note         = {Paper Track, Google -- The Gemma 4 Developer Agent Competition}
}
```

## Acknowledgements

The evaluation harness, tasks and quantized models are from the
[Gemma 4 Developer Agent Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent) (Markowitz et al., 2026).
The free-form baseline is the public community single agent published as a Kaggle sample notebook (`gemma-4-harness-fixed-single-agent`). The task bank
derives from D. Gluzdov's *gemma-4-task-soundness-and-local-results* dataset (CC BY 4.0).

## License

Code: [Apache 2.0](LICENSE). The task data in `datos/banco_nuevo/` keeps its original CC BY 4.0 license.
