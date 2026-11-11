# Cómo reproducir las cifras del paper

Cada cifra del paper sale de un archivo de este repositorio. Esta guía dice cuál y cómo regenerarlo.

| Cifra del paper | Dónde está | Cómo se recalcula |
|---|---|---|
| Cruce 2×2 del lote de 40 (sección 7), IC y p-valores | `resultados/local_deepinfra/l40/` (un JSON por agente y tarea) | `python3 local/tabla_lote.py resultados/local_deepinfra/l40` |
| Contraste de interacción (p = 0,006) | mismos JSON (`base_comunidad`, `e4b_t0`, `e4b_cmd`, `e4b_cmd_t`) | `resultados/local_deepinfra/RESUMEN.md`, sección del cruce 2×2; test de signo sobre (pub_t − pub_0) − (fixer_t − fixer_0) por tarea |
| Variantes del prompt público en el filo (7, 8, 8, 11 frente a 12 y 11) | `resultados/local_deepinfra/filo14*/`, `datos/filo14.txt` | `RESUMEN.md` |
| Dossier sin modelo (sección 5: 28/40, 38/72, ejemplos 7/40 y 0/72) | `lab/oneshot/dossier.py` | `python3 local/muestra.py --semilla 10 --n 40 > l40.txt; python3 lab/oneshot/eval_dossier.py l40.txt`; oficiales: `eval_dossier.py <72 ids de datos/oficiales_medibles_local.json> --oficial` (necesita `tasks.jsonl` y snapshots de la competición) |
| Longitud de los enunciados (78 frente a 112 palabras) | `tasks.jsonl` de la competición y `datos/banco_nuevo/validation_tasks.jsonl` | palabras = `re.findall('[A-Za-z]{2,}', problem_statement)` |
| Llamadas sueltas, cuantizado frente a sin cuantizar (sección 8) | `lab/oneshot/cadena3.jsonl` y `cadena3_cuantizado.jsonl` (arreglo), `loc.jsonl` y `loc_cuantizado.jsonl` (localización) | `lab/oneshot/sonda3.py` y `lab/oneshot/loc.py` (función entera frente a SEARCH: `cadena_funcion_cuantizado.jsonl`, `SONDA_CONDS=A,F`); con `NERVO_SONDA_MODAL=<url>/v1` usan el servidor `local/modal_vllm.py` (pesos oficiales cuantizados) |
| Determinismo (0 de 8), 31B dossier 4/8, E4B 1-2/8 en oficiales, llamadas por tarea en Kaggle | `docs/HISTORIAL_EJECUCIONES.md` (11-nov) y `resultados/*-20261111*.json` | workflow `Evaluar en Kaggle (L4)` |
| Las 40 tareas | `resultados/local_deepinfra/l40/tareas.txt` | `python3 local/muestra.py --semilla 10 --n 40` |
| Llamadas rechazadas por formato (sección 4) | `resultados/formato/RESUMEN.md`, con el identificador de cada run | `gh run download <run> -n salida-kaggle -D trazas/<run>` y `python3 -I resultados/formato/contar_formato.py trazas` |
| Ejecuciones en Kaggle (3/4, tiempos) | `docs/HISTORIAL_EJECUCIONES.md` y `resultados/*.json` | workflow `Evaluar en Kaggle (L4)` |
| Tareas de ajuste del 31B (6/8, 7/8), Docker (4/5) | `resultados/local_deepinfra/RESUMEN.md` y sus subcarpetas | igual que el lote, con esas tareas |
| Nervo-Core (25 % → 62,5 %) | repositorio `nervo-core`, rama `feature/deepseek-api`, `docs/lab-results/` | `POST /v1/lab/eval` de ese repositorio |
| Notas del examen | página de envíos de la competición | no reproducible fuera de Kaggle |

## Repetir un lote local

Requisitos: Python 3.12+, los wheels del harness oficial (`swegemma`, `adk_eval_core`, `adk_submission`, `google_adk` 1.36.1; están en los datos de la competición) y una clave de un proveedor compatible con OpenAI que sirva Gemma 4 (usamos DeepInfra: `google/gemma-4-E4B-it` y `google/gemma-4-31B-it`, sin cuantizar).

```bash
export NERVO_BASE=$HOME/nervo                      # carpeta de trabajo
pip install --no-deps wheels/{swegemma,adk_eval_core,adk_submission}-*.whl
pip install wheels/google_adk-1.36.1-py3-none-any.whl "litellm==1.99.4" rich docker
pip install -r local/entorno_local.txt             # dependencias de los repositorios del banco
python3 -I local/construir_banco.py --out $NERVO_BASE/banco    # snapshots de las 104 tareas desde GitHub

umask 077; printf '%s' "$CLAVE" > ~/.deepinfra_key
python3 local/shim_vllm.py --port 8000 --backend deepinfra --tope-usd 2 --log $NERVO_BASE/shim.jsonl &
python3 local/muestra.py --semilla 10 --n 40 > lote40.txt
for v in base_comunidad e4b_cmd e4b_cmd_t g31_ejemplo; do
  local/lote_limitado.sh l40 variantes/$v 6 $(cat lote40.txt)
done
python3 local/tabla_lote.py $NERVO_BASE/lotes/l40
```

Coste: unos 0,7 USD por agente. Cada línea del registro del puente (`shim.jsonl`) guarda el modelo pedido y el coste: sirve para comprobar que cada agente habló con el modelo que declara.

Avisos:
- El muestreo es a temperatura 0,2 y hay una ejecución por agente: al repetir, cada cifra puede moverse unas tareas (ver los intervalos).
- Estos lotes usan modelos sin cuantizar tras una API. No reproducen los fallos de formato del modelo cuantizado con vLLM: esos solo se ven en Kaggle.
- Réplica Docker: `docker build -t swebench-sandbox:latest local/docker` (quitar las dos líneas del certificado del proxy) y añadir `--sandbox docker` a `local/correr_local.py`.
- Servidor con el modelo del examen: workflow `Servidor vLLM en Modal` (`local/modal_vllm.py`), con los secretos `MODAL_TOKEN_ID` y `MODAL_TOKEN_SECRET`. Se apaga solo a los 5 minutos sin peticiones.
