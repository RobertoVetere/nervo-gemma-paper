# The Prompt Proposes, the Code Decides

Code, data and results for the paper submitted to the Paper Track of Kaggle's
*Google – The Gemma 4 Developer Agent Competition* (`docs/paper/paper_en.md`; Spanish version in `paper_es.md`).

Every figure in the paper maps to a file in this repository; `docs/REPRODUCIR.md` lists which file and which command
regenerates it.

## What is here

| Path | What it is |
|---|---|
| `docs/paper/` | The paper (English and Spanish) |
| `docs/REPRODUCIR.md` | Figure-by-figure reproduction guide |
| `docs/HISTORIAL_EJECUCIONES.md` | Log of every Kaggle run: what it was, its run id, and whether it is valid |
| `variantes/` | The agents compared in the paper, in the official submission format (`agent.yaml`, prompts, skills) |
| `datos/banco_nuevo/` | 104-task bank validated with the official oracle (65 measurable locally), from a public CC BY 4.0 dataset (see `FUENTE.md`) |
| `local/shim_vllm.py` | Bridge that poses as the vLLM server to the official harness and forwards to any OpenAI-compatible API, with a spending cap |
| `local/correr_local.py` | Runs the official `swegemma` Evaluator locally (subprocess or `--sandbox docker`) |
| `local/docker/` | Docker replica of the exam sandbox (no network, 2 CPUs, 4 GB) |
| `local/modal_vllm.py`, `local/modal_eval.py` | The exam model (official `qat-w4a16-ct` weights, vLLM 0.19.1, Gemma 4 parsers) served on Modal, and a full evaluation run there |
| `lab/oneshot/` | Single-call probes (section 8): localization and fixing with unquantized vs quantized E4B |
| `resultados/` | Per-task JSON results of every run cited |
| `scripts/` | Submission builder/validator and the Kaggle kernel used for evaluation |
| `.github/workflows/` | The workflows that launched the Kaggle and Modal runs (they need the owner's secrets) |

## Quick check without spending anything

```bash
python3 local/tabla_lote.py resultados/local_deepinfra/l40      # the 2x2 cross of section 7, from saved results
python3 local/muestra.py --semilla 10 --n 40                      # the 40 random tasks
```

## License

Code: Apache 2.0 (`LICENSE`). The task bank in `datos/banco_nuevo/` keeps its original CC BY 4.0 license.
