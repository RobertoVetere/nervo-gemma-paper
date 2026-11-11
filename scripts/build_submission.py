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
            errores.append(f"extensión no permitida: {p.relative_to(SUB)}")
        if p.suffix in {".yaml", ".yml"}:
            texto = p.read_text(encoding="utf-8")
            # Las rutas son relativas al YAML que las referencia.
            for ref in re.findall(r"!include\s+(\S+)", texto) + re.findall(r"config_path:\s*(\S+)", texto):
                destino = (p.parent / ref).resolve()
                if not (destino.is_file() and SUB.resolve() in destino.parents):
                    errores.append(f"{p.relative_to(SUB)}: no se encuentra {ref}")
            modelos |= set(re.findall(r"^\s*model:\s*(\S+)", texto, flags=re.M))
    # Skills: el harness exige nombre kebab-case (a-z, 0-9, guiones) en el frontmatter (E21).
    nombres_agente = set()
    for y in SUB.rglob("*.y*ml"):
        nombres_agente |= set(re.findall(r"^name:\s*(\S+)", y.read_text(encoding="utf-8"), flags=re.M))
    for sk in SUB.rglob("SKILL.md"):
        m = re.search(r"^name:\s*(\S+)", sk.read_text(encoding="utf-8"), flags=re.M)
        nombre = m.group(1) if m else ""
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nombre):
            errores.append(f"{sk.relative_to(SUB)}: nombre de skill '{nombre}' no es kebab-case (a-z, 0-9, guiones)")
        if nombre and sk.parent.name != nombre:
            errores.append(f"{sk.relative_to(SUB)}: la carpeta '{sk.parent.name}' no coincide con el nombre '{nombre}'")
        if nombre and nombres_agente and nombre not in nombres_agente:
            print(f"AVISO {sk.relative_to(SUB)}: la skill '{nombre}' no se llama como ningún agente {sorted(nombres_agente)}; "
                  "ADK le dice al modelo el nombre del agente y puede confundirlos (E21)")
    if total > MAX_BYTES:
        errores.append(f"tamaño {total} supera 3 GiB")
    if len(modelos) != 1:
        errores.append(f"todos los agentes deben usar el mismo modelo, hay: {sorted(modelos)}")
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
    print(f"OK {SALIDA.relative_to(RAIZ)} ({total} bytes, modelo {modelos.pop()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
