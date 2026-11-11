# Historial de ejecuciones en Kaggle

Todas se lanzan con el workflow **"Evaluar en Kaggle (L4)"** (`.github/workflows/evaluar.yml`). El ID es el de la ejecución de GitHub Actions. Los resultados están en `resultados/<label>-<fecha>.json`, o se descargan con:

```bash
gh run download <ID> -R RobertoVetere/nervo-kaggle -n salida-kaggle -D /tmp/salida
```

Horas en UTC (Madrid = UTC+1).

| Fecha (UTC) | ID | Label | Qué era | Resultado | ¿Válido? |
|---|---|---|---|---|---|
| 06-nov 20:48 | 42291403604 | v0 | Cadena v0 (LOCATE→FIX→VERIFY→FINALIZE, `SequentialAgent`), E4B, 12 tareas de muestra fija | 0/12; 8 parches vacíos | Parcial: el banco aún puntuaba mal requests/httpx (E6) y varias de fastapi no son medibles (E7) |
| 06-nov 23:22 | 42311413061 | v2-smoke | v2 (PARSE→LOCATE→ATOMIZE→EXECUTE→VERIFY→FINALIZE), 2 tareas | 0/2; agotó las 30 llamadas | Sí: demasiados pasos |
| 06-nov 23:43 | 42313735486 | v3-oracle | v3 (LOCATE + bucle EDIT/CHECK + FINALIZE) en requests_6592 y requests_7315, más oráculo | requests_7315: parche idéntico al oficial pero "no resuelto" | Destapó E6 |
| 06-nov 23:57 | 42315236982 | diag | Diagnóstico del sandbox, sin GPU | Volcó el código: venv sin pip, `PYTHONPATH=/workspace` | Sí |
| 07-nov 00:01 | 42315632766 | oraculo | Oráculo en 4 tareas con el arreglo de `src/` | 2/4 pasan (requests_7315 y rich_3454); fastapi_14266 sin `inline_snapshot`; requests_6592 con 185 errores | Sí |
| 07-nov 00:07 | 42316310493 | oraculo-129 | Oráculo en las 129 tareas | 78/129 pasan → `datos/tareas_medibles.json` | Sí |
| 07-nov 00:35 | 42319201522 | (Leaderboard) | Leaderboard público | 1.º 0,29 (Yurnero); ~10 equipos en 0,24; muchos en 0,22 | Sí |
| 07-nov 00:39 | 42319504810 | v3-medibles12 | v3 en 12 tareas medibles | 0/12; 9 agotaron los 80 turnos sin parche | Sí (E2, E3, E4) |
| 07-nov 07:56 | 42353370659 | v5-smoke | v5 (v3 + `include_contents: none`), 2 tareas | 0/2; EDIT nunca llama a `edit_file` en 45 llamadas | Sí (E2) |
| 07-nov 08:48 | 42357027928 | base-e4b-smoke | Agente de la comunidad (`variantes/base_comunidad`) con E4B, mismas 2 tareas | **2/2** (41 s y 118 s) | Sí: referencia |
| 07-nov 09:32 | 42360172615 | lab-01 | Sondas 01: 15 llamadas sueltas | Bloque de salida 0/3 frente a sin bloque 3/3; `tool_choice: required` devuelve vacío; argumentos rotos con `:` | Sí, salvo los argumentos rotos (E9) |
| 07-nov 09:43 | 42360919449 | bateria-01 | Sondas 02 + batería de 6 enfoques × 8 tareas, E4B | Todo 0 | **No**: git "dubious ownership" (E8) |
| 07-nov 09:52 | 42361521280 | bateria-01-31b | Igual con 31B | Cancelado (el kernel siguió en Kaggle) | No (E8) |
| 07-nov 10:05 | 42362476363 | bateria-02-e4b | Batería con E8 arreglado + captura de kwargs del harness + autoprueba, E4B | Control resuelto; autoprueba del harness 3/3. Resueltas de 8: localiza_y_json 2, el resto 1 | **Sí** |
| 07-nov 10:06 | 42362495002 | bateria-02-31b | Igual con 31B | El workflow descargó la salida del kernel **viejo** (batería 01 del 31B, con el fallo de git): no tiene `captura` | **No** (E14). Hay que relanzarla cuando no quede nada corriendo con ese nombre |

| 07-nov 10:19 | 42363450091 | bateria-03-31b | Batería 02 corregida con 31B (captura + autoprueba + git arreglado) | Controles OK (captura resuelta, autoprueba harness 3/3 y cruda 3/3). Resueltas de 8: uno_plan_primero 2, comunidad 1, resto 0. 111/118 `edit_file` fallan por 0 coincidencias | Controles sí; **las cifras de edición no (E15)**: el `edit_file` del lab es más estricto que el oficial |
| 07-nov 12:03 | 42370774010 | bat-real-01-e4b | **Harness real**, kernel multi-variante: base_comunidad vs nervo_repro, E4B, 14 tareas medibles (incluye rich_3454 y requests_7315) | **3/14 cada una.** nervo_repro: 14/14 con parche, menos llamadas y tiempo. Fallos de nervo_repro: 8 archivo equivocado, 3 archivo correcto pero cambio mal. Comunidad: 6 y 4. **E4B falla sobre todo localizando** | **Sí** |
| 07-nov 12:04 | 42370845784 | bat-real-01-31b | Igual con 31B, 8 tareas | **nervo_repro 6/8, comunidad 5/8.** nervo_repro gana rich_2725 y usa menos llamadas en requests. Fallos 31B: tiempo (8 min) y cambio mal, no localización | **Sí** |
| 07-nov 13:24 | 42376946961 | escalera-01-e4b | e4b_guiado vs nervo_repro, E4B, las 8 tareas más fáciles de la escalera | **3/8 cada una.** e4b_guiado usó la skill en 8/8 tareas (veredictos: 6 SUBMIT, 5 FIX, 2 NO_EDIT). En las fáciles, el fallo dominante de E4B es cambio mal en el archivo correcto | **Sí** |
| 07-nov 17:01 | — | **ENVÍO REAL 1** | `nervo_repro 31B v1 | commit 733414e` (variantes/nervo_repro_31b, File Upload) | **0,18 público** (8-nov). Por debajo del pelotón de 0,24 (probablemente la comunidad con E4B). Nuestro banco decía 6/8: **no está calibrado** | Sí |
| 08-nov 16:46 | 42496460738 | e4b-t0-vs-t4096 | E4B: `e4b_t0` (thinking 0) contra `base_comunidad` (thinking 4096), 14 medibles, un vLLM. Run de ~65 min | **e4b_t0 2/14, base_comunidad 4/14** (control previo 3/14). Discordantes: t0 gana 0, pierde 2. Sin razonamiento no rompe ediciones (13/14 con parche) pero resuelve menos. **No confirma** el 16 vs 10 de la comunidad | Sí |

Dato del archivo inválido del 31B que sí vale: en las sondas, los argumentos de `edit_file` llegan intactos 6 de 6 con 31B (E4B: 0 de 6).

## Cómo leer el JSON de una batería

```python
import json
d = json.load(open('/tmp/salida/nervo_results.json'))
d['stage']                       # 'done' si terminó
d['lab']['results']              # sondas sueltas: tool_calls, content, reasoning, seconds
b = d['bateria']
b['captura']                     # kwargs con los que el harness llama al modelo + resolved de la tarea de control
b['autoprueba']                  # qué forma de llamar deja intactos los argumentos de edit_file; 'elegido'
b['resumen']                     # por enfoque: resueltas, con_parche, total
b['resultados']                  # por (enfoque, tarea): patch, resolved, pasos (cada llamada al modelo), notas
```

**Lo primero que hay que mirar en la batería 02:**
1. `captura.resolved` debe ser `True`: el agente de la comunidad resolviendo rich_3454 con el harness real es el control de que el entorno funciona.
2. `autoprueba.harness` debe ser `[True, True, True]`: argumentos intactos llamando como el harness.
3. Solo si ambas cosas se cumplen, el `resumen` por enfoque tiene sentido.
| 08-nov 23:10 | 42528427422 | g31-steps-v4-lote1 | 31B, `g31_steps` v4, banco nuevo, 18 tareas. ~5 h de cuota | **0/18**: el modelo llamaba a la skill `swe_agent` en vez de `steps` (653 SKILL_NOT_FOUND). Ver E21 | No (fallo mecánico) |
| 09-nov 18:12 | 42662123059 | g31-steps-v7-isort | 31B, `g31_steps` v7 (skill `swe_agent`, no es kebab-case), solo isort-891 | Cancelado por Roberto en cola (fallaría al cargar la skill) | No |
| 09-nov ~18:30 | 42667645366 | g31-steps-v8-isort | 31B, `g31_steps` prompt v8, solo isort-891 | **No resuelta**. Scripts OK (evidence, 3× show_function, save_check, verify) y localiza `should_skip` con el arreglo correcto, pero la llamada a `apply_edit` llega rota: el modelo no cierra el texto largo de `blocks` y el parser de vLLM mezcla `file_path` en una clave basura → INVALID_ARGUMENTS en bucle hasta 80 turnos | Sí (formato) |
| 09-nov 19:03 | 42670592555 | e4b-steps-v9-isort | E4B, `e4b_steps` v9, solo isort-891. ~20 min de cuota | **No resuelta, pero primera pipeline completa en Kaggle sin errores de formato**: show_function ×5, apply_edit OK, verify, submit_patch (61 s, 8 llamadas). Omitió `skill_name` en la llamada larga a evidence (2 veces) y se la saltó; arreglo equivocado (`import fnmatch`). verify avisaba en falso de pytest.ini/conftest.py (los pone el harness) | Sí |
| 09-nov ~19:35 | 42673741260 | e4b-steps-v10-isort | E4B, v10 (orden de campos, reintento ante INVALID_ARGUMENTS, apply_edit deduce el archivo, verify ignora archivos del harness), solo isort-891. ~20 min de cuota (el 1.er intento no arrancó en GitHub, 0 jobs; relanzado) | **✅ RESUELTA en Kaggle** (76 s, 7 llamadas útiles). Perdió `skill_name` en evidence y `skill_name`+`file_path` en apply_edit, pero **repitió la llamada completa** (regla v10). Arreglo `fnmatch(os_path, glob)`. Se saltó save_check. Zip candidato: `e4b_steps` commit d4054d5, sha256 c758d821… | Sí |
| 09-nov ~19:45 | 42676719254 | g31-steps-v10-isort | 31B, v10, solo isort-891 (slot b). ~45 min de cuota | **No resuelta.** Bien hasta `should_skip` y el script de casos; tras la **compactación del harness** (cada 15 eventos) re-pide la evidencia con un resumen, guarda el script 6 veces y repite **64 veces la misma llamada sin `file_path`** hasta 80 turnos | Sí |
| 09-nov ~19:50 | 42677347101 | e4b-steps-v11-dynaconf1184 | E4B, v11, solo dynaconf-1184. ~20 min de cuota | **No resuelta.** Evidence perdió `skill_name`/`file_path` y luego metió el archivo del repo en `file_path` (SCRIPT_NOT_FOUND); abandonó la evidencia y adivinó. Guardó un script de casos **vacío** para pasar `verify`. El arreglo de números de línea en apply_edit sí funcionó | Sí |
| 09-nov ~21:00 | 42687234244 | e4b-cmd-v12-isort | E4B, `e4b_cmd` v12 (una llamada a la skill instala `.fixer/`; luego run_command + write_file), solo isort-891. ~20 min de cuota | **No resuelta, pero CERO fallos de formato** (14 llamadas, 78 s): install, write_file del issue, evidence, show_function, callers, script de casos, edit, apply_edit, verify ×3, submit. Arreglo `check_skip=True` en `sort_imports` (parte de la idea del parche de referencia, no basta). verify detectó que su script de casos petaba y luego un WRONG; el modelo envió igual | Sí |
| 09-nov ~23:05 | 42708128706 | e4b-cmd-calibra4 | E4B, `e4b_cmd` v12, 4 tareas medias (more-itertools-903, semver-254, api-core-821, traitlets-687) para calibrar el banco local con DeepInfra (allí 4/4). ~25 min de cuota | **3/4 resueltas en Kaggle** (falla traitlets), **0 errores de argumentos** en 65 llamadas, 60-122 s por tarea. Lo local (DeepInfra) predice bien Kaggle. Zip `envios/e4b_cmd_v12_7375466.zip` | Sí |
| 10-nov ~00:50 | 42722453454 | g31-ejemplo-3 | 31B, `g31_ejemplo` (vía corta + ejemplo del issue), 3 tareas (faker, jinja, semver), slot b. ~40 min de cuota | **1/3 (semver)**, **0 errores de formato** en 24 llamadas, **25-65 s de agente por tarea** (vLLM arranca en 411 s). faker: el ejemplo del issue detectó el arreglo a medias en Kaggle (FIX → corregido → OK) pero el test oculto exige también conjuntos; jinja: arreglo distinto al de local (ordenar nombres), no basta. Zip `envios/g31_ejemplo_22fa3c9.zip` | Sí |

## 11-nov 02:53 — E4B razonamiento 12288 frente a 4096, y 31B sin razonar (banco nuevo)
- Run 42942139772 (kernel `nervo-eval`, E4B): `base_comunidad` (4096) y `com_t16` (12288, max_output 14336) en 6 tareas:
  jinja-1614, jinja-1702, pyflakes-675, click-2730, traitlets-773, babel-1196. Coste estimado ~1 h de kernel (~2 h de cuota).
- Run 42942152723 (kernel slot b, 31B): `com31_t0` (agente público sin razonar) en 4 tareas: jinja-1614, pyflakes-675,
  click-2730, traitlets-773. Coste estimado ~30-40 min de kernel (~1-1,3 h de cuota).
- Prueba local previa (DeepInfra, click-2730): las dos resuelven; el puente recibió thinking_token_budget 12288 en E4B y
  razonamiento apagado en el 31B. Sin probar: tiempo real de pensar 12k tokens en L4 y que entrada+salida quepa en 32768.
- **Resultado (11-nov 03:20):** E4B `base_comunidad` (4096) 1/6 y `com_t16` (12288) 1/6, solo click-2730 en ambas; 31B `com31_t0` 1/4 (click-2730), las otras 3 agotan las 28 llamadas.
  Kernel: E4B 26 min, 31B 17 min (~1,4 h de cuota). El presupuesto de razonamiento no cambia nada: en Kaggle E4B genera ~200 tokens por llamada y solo 2 de 76 pasan de 4096.
- **Hallazgo:** E4B cuantizado en Kaggle **abandona pronto**: mediana de 6,5-8,5 llamadas por tarea (14 tareas del 8-nov: 12-18), frente a **26** del mismo agente con E4B sin cuantizar en local. En traitlets-773 edita a ciegas en la llamada 7 (`Union.__init__`), los tests existentes pasan, declara el arreglo correcto y envía. En local la misma tarea se resuelve 2/2 con 27 llamadas. El 31B en Kaggle usa 26-28 llamadas, como en local.
  Explica buena parte de la brecha local/examen de E4B, y el banco local (DeepInfra, sin cuantizar) no lo reproduce.

## 11-nov 10:30 — Agente dossier (dossier_e4b / dossier_31b) en Kaggle, mismas tareas que la noche anterior
- Prueba local previa (DeepInfra, E4B real): 4/6 (banco: more-itertools-1028 y click-2730 sí, traitlets-773 no;
  oficiales: fastapi_13537 y rich_3067 sí, fastapi_11194 no, agota 28 llamadas explorando). 0 llamadas rotas; sigue el flujo
  instalar → issue → dossier → editar → apply (verifica) → enviar en 5-6 llamadas cuando acierta. 0,05 USD.
- **Resultado:** run 42984368076 `dossier_e4b` 1/6 (click-2730), run 42984383330 `dossier_31b` 1/4 (click-2730; pyflakes-675 se corta a los 8 min).
  Igual que el agente público la noche anterior. Kernel ~25 y ~36 min (~2 h de cuota).
  El flujo se cumple (0 llamadas rotas) y el sitio mejora: E4B edita la función del arreglo oficial en traitlets-773, babel-1196 y click;
  el 31B encuentra `CodeGenerator` en jinja-1614 (anoche no editó nada). Pero el cambio es incorrecto. Sin ejemplo ejecutable en el
  issue (traitlets, pyflakes), la verificación solo tiene los tests existentes y dice SUBMIT a un arreglo equivocado; con ejemplo
  (jinja-1702) dice FIX y el modelo no acierta a corregirlo. El cuello de botella es el contenido del arreglo, no el contexto.

## 11-nov 11:25 — Determinismo en Kaggle (E4B, tareas OFICIALES de desarrollo)
- `base_comunidad` (temperatura 0,2) frente a `com_det_a` y `com_det_b` (idénticas: temperatura 0, top_p 1, seed 1234) en 8 tareas
  oficiales: fastapi_15589, fastapi_15800, rich_3777, rich_3894, rich_3905, rich_3942, rich_4006, rich_4077 (semilla 11 sobre las 72).
  Mide: (1) si det_a y det_b hacen lo mismo (mismas llamadas y parche), (2) si temperatura 0 pierde aciertos.
- **Run 43001565097 (31B `dossier_31b` + same_change, razonamiento 4096): 3/3** (jinja-1614, traitlets-773, click-2730).
  Ojo: el aviso de copias gemelas no llegó a dispararse; el 31B escribió esta vez el arreglo completo por sí mismo. Las mismas
  tareas dieron 1/4 por la mañana con la misma variante sin same_change: el resultado del 31B varía mucho de una ejecución a otra.

## 11-nov 11:50 — 31B dossier con temperatura 0 en tareas OFICIALES (run 43006548634, slot b)
- `dossier_31b_t0` (temperatura 0, seed 1234, razonamiento 4096) en las mismas 8 tareas oficiales que la prueba de determinismo de E4B.
- **Resultado determinismo (run 43002548515, E4B, 8 oficiales):** `base_comunidad` (0,2) 1/8, `com_det_a` 2/8, `com_det_b` 1/8.
  **Temperatura 0 + seed NO da determinismo en Kaggle:** 0 de 8 trayectorias idénticas. Con la MISMA entrada (salida previa idéntica,
  mismos tokens de prompt) el modelo responde distinto en la llamada 3-5 (p. ej. rich_3894: 3437 frente a 1548 tokens generados).
  Causa probable: vLLM no es invariante al lote (las peticiones concurrentes cambian los cálculos en GPU y se rompen empates casi
  exactos). No se puede controlar desde el zip: en el examen pasará igual. Consecuencia: medir con repeticiones, nunca con una ejecución.
- **Resultado 31B dossier t0 (run 43006548634): 4/8** en las 8 oficiales (rich_3777, 3894, 3905, 4077), frente a 1-2/8 de E4B en las mismas.
  Fallos: 2 cortes por 8 min (fastapi_15589, rich_4006), 1 por 80 turnos (fastapi_15800), rich_3942 con arreglo equivocado.

## 11-nov 12:45 — Referencia 31B público y repetición del 31B dossier, mismas 8 oficiales
- slot b: `comunidad_31b` (agente público, 31B, razonamiento 4096). slot a: `dossier_31b_t0` otra vez (medir varianza).
- **11-nov 12:35: CUOTA SEMANAL DE GPU AGOTADA** ("Maximum weekly GPU quota of 30.00 hours reached"). Las dos pruebas de 12:45
  (31B público y repetición del dossier) NO se ejecutaron. El workflow no falló y guardó como `31b-publico-oficiales` la salida
  ANTERIOR del kernel `nervo-eval-31b-b` (la del dossier t0): resultado falso, borrado. Arreglado: el workflow para si el push falla.

## 11-nov 16:20 — Envío propuesto: 31B `dossier_31b_t0` (commit 321b5e4)
- Zip `dist/dossier_31b_t0_321b5e4.zip` (`NERVO_VARIANT=variantes/dossier_31b_t0`), idéntico a la variante del run 43006548634 (4/8 en oficiales en Kaggle). Cumple la regla de ≥1 tarea resuelta en Kaggle.
- Referencia: 31B `nervo_repro` 0,18 (11/58) el 7-nov. Ruido de un envío: ±1,5 tareas; solo una diferencia de 4+ tareas dice algo.
- Nota: *pendiente* (la sube Roberto).

