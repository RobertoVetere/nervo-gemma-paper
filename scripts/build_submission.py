"""Validate the submission folder against the competition rules and zip it.

Checks: agent.yaml at the root, allowed extensions only, no symlinks,
total size under 3 GiB, every !include and config_path resolves inside
the folder, and every agent uses the same base model.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
import os
SUB = RAIZ / os.environ.get("NERVO_VARIANT", "submission")
MODEL_OVERRIDE = os.environ.get("NERVO_MODEL", "").strip()
SALIDA = RAIZ / "dist" / "submission.zip"
PERMITIDAS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
MAX_BYTES = 3 * 1024**3
MODELOS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}


def main() -> int:
    errores: list[str] = []
    if not (SUB / "agent.yaml").is_file():
        errores.append("falta submission/agent.yaml")
    total, modelos = 0, set()
    for p in SUB.rglob("*"):
        if p.is_symlink():
            errores.append(f"symlink no permitido: {p.relative_to(SUB)}")
        if not p.is_file():
            continue
        total += p.stat().st_size
        if p.suffix.lower() not in PERMITIDAS:
            errores.append(f"extension not allowed: {p.relative_to(SUB)}")
        if p.suffix in {".yaml", ".yml"}:
            texto = p.read_text(encoding="utf-8")
            # Paths are relative to the YAML file that references them.
            for ref in re.findall(r"!include\s+(\S+)", texto) + re.findall(r"config_path:\s*(\S+)", texto):
                destino = (p.parent / ref).resolve()
                if not (destino.is_file() and SUB.resolve() in destino.parents):
                    errores.append(f"{p.relative_to(SUB)}: {ref} not found")
            modelos |= set(re.findall(r"^\s*model:\s*(\S+)", texto, flags=re.M))
    # Skills: the harness requires a kebab-case name (a-z, 0-9, hyphens) in the frontmatter.
    nombres_agente = set()
    for y in SUB.rglob("*.y*ml"):
        nombres_agente |= set(re.findall(r"^name:\s*(\S+)", y.read_text(encoding="utf-8"), flags=re.M))
    for sk in SUB.rglob("SKILL.md"):
        m = re.search(r"^name:\s*(\S+)", sk.read_text(encoding="utf-8"), flags=re.M)
        nombre = m.group(1) if m else ""
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nombre):
            errores.append(f"{sk.relative_to(SUB)}: skill name '{nombre}' is not kebab-case (a-z, 0-9, hyphens)")
        if nombre and sk.parent.name != nombre:
            errores.append(f"{sk.relative_to(SUB)}: folder '{sk.parent.name}' does not match the name '{nombre}'")
        if nombre and nombres_agente and nombre not in nombres_agente:
            print(f"WARNING {sk.relative_to(SUB)}: skill '{nombre}' is not named like any agent {sorted(nombres_agente)}; "
                  "ADK tells the model the agent's name and the model may call the agent name as a skill")
    if total > MAX_BYTES:
        errores.append(f"size {total} exceeds 3 GiB")
    if len(modelos) != 1:
        errores.append(f"every agent must use the same model, found: {sorted(modelos)}")
    elif not modelos <= MODELOS:
        errores.append(f"modelo no permitido: {modelos}")
    if errores:
        print("\n".join(f"ERROR {e}" for e in errores))
        return 1
    SALIDA.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SUB.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(SUB).as_posix())
    print(f"OK {SALIDA.relative_to(RAIZ)} ({total} bytes, model {modelos.pop()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
