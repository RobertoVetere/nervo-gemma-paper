"""Render the Kaggle evaluation kernel: embeds submission/ into the template."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCKER = "gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="kernel")
    p.add_argument("--n-tasks", type=int, default=12)
    p.add_argument("--label", default="dev")
    p.add_argument("--oracle", action="store_true")
    p.add_argument("--tasks", default="")
    p.add_argument("--diag", action="store_true")
    p.add_argument("--variant", default="submission")
    p.add_argument("--model", default="")
    p.add_argument("--lab", default="", help="JSON with single-call probes (lab mode)")
    p.add_argument("--battery", "--bateria", dest="bateria", default="", help="JSON battery of approaches (lab/motor.py, not included)")
    p.add_argument("--slot", default="", help="kernel suffix (a-z0-9) so as not to overwrite a running kernel")
    p.add_argument("--bench", "--banco", dest="banco", action="store_true", help="use the validation bench (Kaggle dataset <user>/nervo-banco-nuevo)")
    a = p.parse_args()

    user = os.environ["KAGGLE_USERNAME"].strip()
    import re
    variantes = [v.strip() for v in (a.variant or "submission").split(",") if v.strip()]
    bundle = {}
    for v in variantes:
        sub = RAIZ / v
        files = {f.relative_to(sub).as_posix(): f.read_text(encoding="utf-8")
                 for f in sorted(sub.rglob("*")) if f.is_file() and "__pycache__" not in f.parts}
        if a.model:
            files = {k: (re.sub(r"(model:\s*)gemma-4-[\w.-]+", r"\g<1>" + a.model, t) if k.endswith(".yaml") else t)
                     for k, t in files.items()}
        bundle[Path(v).name] = files
    modelos = {line.split(":", 1)[1].strip() for files in bundle.values() for f, t in files.items()
               if f.endswith(".yaml") for line in t.splitlines() if line.strip().startswith("model:")}
    assert len(modelos) == 1, f"every variant must use the same model: {modelos}"
    model = modelos.pop()
    payload = base64.b64encode(json.dumps(bundle).encode()).decode()

    tpl = (RAIZ / "scripts" / "kernel_template.py").read_text(encoding="utf-8")
    code = (tpl.replace("__SUBMISSION_PAYLOAD_B64__", payload)
               .replace("__N_TASKS__", str(a.n_tasks))
               .replace("__RUN_LABEL__", a.label)
               .replace("__ORACLE__", "1" if a.oracle else "0")
               .replace("__TASK_IDS__", a.tasks.replace(" ", ""))
               .replace("__DIAG__", "1" if a.diag else "0")
               .replace("__BANCO__", "1" if a.banco else "0")
               .replace("__BATERIA_B64__", base64.b64encode((RAIZ / a.bateria).read_bytes()).decode() if a.bateria else "")
               .replace("__MOTOR_B64__", base64.b64encode((RAIZ / "lab" / "motor.py").read_bytes()).decode())
               .replace("__LAB_PROBES_B64__", base64.b64encode((RAIZ / a.lab).read_bytes()).decode() if a.lab else ""))
    out = RAIZ / a.out
    out.mkdir(exist_ok=True)
    (out / "nervo_eval.py").write_text(code, encoding="utf-8")
    # one kernel per model, so they can run at the same time without overwriting each other
    slug = "nervo-eval" if not a.model else "nervo-eval-" + a.model.split("-")[2]
    if a.slot:
        slug += "-" + a.slot  # another kernel, so as not to overwrite one still running
    meta = {
        "id": f"{user}/{slug}",
        "title": slug,
        "code_file": "nervo_eval.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": "NvidiaL4",
        "docker_image": DOCKER,
        "dataset_sources": ["metric/gemma-4-developer-agent-wheelhouse"] + ([f"{user}/nervo-banco-nuevo"] if a.banco else []),
        "competition_sources": ["gemma-4-developer-agent"],
        "kernel_sources": [],
        "model_sources": [f"google/gemma-4/Other/{model}/2"],
    }
    if a.oracle and a.n_tasks == 0 and not a.tasks:
        # oracle only: no GPU needed, so no quota is spent
        meta["enable_gpu"] = False
        meta.pop("machine_shape", None)
        meta["model_sources"] = []
        meta["id"] = f"{user}/nervo-oraculo"
        meta["title"] = "nervo-oraculo"
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"kernel {meta['id']} | variants {list(bundle)} | model {model} | {a.n_tasks} tasks")


if __name__ == "__main__":
    main()
