> **CORRECCIÓN (10-nov 13:45): todo lo de este archivo marcado como "E4B" se ejecutó en realidad con el 31B.**
> `local/correr_local.py` forzaba siempre el modelo 31B en la variante (herencia de AI Studio), y el puente elige
> el modelo por ese nombre. Los registros del puente lo confirman: 913 de 914 llamadas fueron al 31B.
> Así que estas cifras son del **31B (sin cuantizar)** con las pipelines de E4B. Arreglado: ahora se usa el modelo
> de la variante (`--forzar-31b` para el comportamiento viejo). La única medida real de E4B es la de Kaggle (3/4).

# Lotes locales con E4B real (DeepInfra, sin cuantizar), 9-nov noche

Harness oficial en local (`local/correr_local.py`) + `local/shim_vllm.py --backend deepinfra`. Límite real de 8 min (sin `--minutos`).
Gasto total de la noche: ~1,6 USD.

## 4 tareas medias (en paralelo, 8 procesos)
| tarea | e4b_cmd (sin razonar) | e4b_cmd_t (razonando) |
|---|---|---|
| python-api-core-821 | ✅ 15 ll 229 s | ✅ 13 ll 159 s |
| traitlets-687 | ✅ 18 ll 196 s | ✅ 12 ll 133 s |
| more-itertools-903 | ✅ 13 ll 197 s | ✅ 10 ll 117 s |
| python-semver-254 | ✅ 11 ll 147 s | ✅ 12 ll 152 s |

## 13 tareas difíciles (13 procesos a la vez en 2 CPU: los tiempos están inflados)
**e4b_cmd 4/13** (bump-my-version-180, faker-2203, click-2730, jinja-2022) · **e4b_cmd_t 2/13** (click, jinja).
- Con razonamiento, 8 de 13 se cortan por las 8 min (llamadas p50 2,6 s, p90 25 s). Confusión: 13 procesos a la vez. No concluyente sobre razonar, pero el tiempo es un riesgo real.
- dynaconf-1184 (issue de 6.428 caracteres): E4B tarda 275 s en escribir el issue con `write_file` y la llamada sale sin `filepath`. **Copiar el issue entero no escala**: mediana 951 caracteres, p90 2.694, 7 de 104 pasan de 3.000.

## v13 (`e4b_v13`: casos ejecutados también sobre el código original + límite de rondas + issue resumido) — PARADA
8 tareas difíciles terminadas: **3/8, igual que la v12** (faker, click, jinja), sin ganar ni perder ninguna, pero **3-4 veces más lenta** (375-427 s, cerca del límite de 8 min). Roberto la paró: no gana nada. Se queda la v12 como candidata.
Nota: los procesos lanzados con `nohup ... &` se cortan al terminar la respuesta de la sesión; lanzar los lotes con `run_in_background` del Bash.
Gasto total de la noche en DeepInfra: ~2,05 USD.

## Diagnóstico de los 9 fallos de la v12 (parche de E4B contra el oficial)
- **Injustas (el issue no pide lo que exigen los tests ocultos):** markdownify (arreglo idéntico al oficial; falla `test_q`, otra función), pyflakes (arregla el orden; fallan tests de TypeVar), pypika (añade `select`; tests piden también `update`/`insert`), cookiecutter (tests piden parámetro `hooks_dir`), isort.
- **Nuestras:** babel (REPLACE == SEARCH, apply_edit decía OK → parche vacío; **arreglado en v12.1**), dynaconf (issue de 6.428 caracteres: no lo copia), markdown (repite el mismo comando 10 veces sin editar), traitlets (local sí, Kaggle no).

## v12.1 (apply_edit rechaza REPLACE == SEARCH) en las 4 nuestras
traitlets ✅, babel ❌ (ya aplica un arreglo real, equivocado), markdown ❌, dynaconf ❌ (cuelgue con el issue largo). Coste 0,16 USD.

## e4b_rev (paso REVIEW con review.py) en las 4 injustas — DESCARTADA
0/4. review.py señala bien lo que falta (pypika: Query.into/update; cookiecutter: hooks_dir), pero E4B lee la revisión y envía sin ampliar. Resultado negativo útil para el paper. Coste 0,14 USD.

**Gasto total DeepInfra 9-10 nov: ~2,35 USD.**
**Decisión:** el envío E4B es la **v12** (`envios/e4b_cmd_v12_7375466.zip`, 3/4 en Kaggle).

## 31B (DeepInfra, sin cuantizar), 8 tareas — 10-nov 00:30
Tiempo Kaggle estimado = tokens escritos / 33 tok/s + 5 s por llamada (medido en trazas 31B de Kaggle).
```
g31_cmd     callowayproject__bump-my-version-180     OK llamadas=28 tokens_salida= 4193 kaggle_estimado= 267s 
g31_cmd     googleapis__python-api-core-821          -- llamadas=11 tokens_salida= 1783 kaggle_estimado= 109s 
g31_cmd     ipython__traitlets-687                   OK llamadas=21 tokens_salida= 4178 kaggle_estimado= 232s 
g31_cmd     joke2k__faker-2203                       -- llamadas=11 tokens_salida= 1842 kaggle_estimado= 111s 
g31_cmd     more-itertools__more-itertools-903       OK llamadas=10 tokens_salida= 2375 kaggle_estimado= 122s 
g31_cmd     pallets__click-2730                      OK llamadas=12 tokens_salida= 2988 kaggle_estimado= 151s 
g31_cmd     pallets__jinja-2022                      OK llamadas=28 tokens_salida= 5631 kaggle_estimado= 311s 
g31_cmd     python-semver__python-semver-254         OK llamadas=12 tokens_salida= 2027 kaggle_estimado= 121s 
g31_rapido  callowayproject__bump-my-version-180     OK llamadas=12 tokens_salida=  998 kaggle_estimado=  90s 
g31_rapido  googleapis__python-api-core-821          -- llamadas=10 tokens_salida= 1480 kaggle_estimado=  95s 
g31_rapido  ipython__traitlets-687                   OK llamadas= 6 tokens_salida=  798 kaggle_estimado=  54s 
g31_rapido  joke2k__faker-2203                       -- llamadas= 5 tokens_salida=  546 kaggle_estimado=  42s Agent exceeded session timeout
g31_rapido  more-itertools__more-itertools-903       OK llamadas= 5 tokens_salida=  530 kaggle_estimado=  41s 
g31_rapido  pallets__click-2730                      OK llamadas= 6 tokens_salida= 1046 kaggle_estimado=  62s 
g31_rapido  pallets__jinja-2022                      OK llamadas= 6 tokens_salida= 1068 kaggle_estimado=  62s 
g31_rapido  python-semver__python-semver-254         OK llamadas= 6 tokens_salida=  683 kaggle_estimado=  51s 
```

## g31_ejemplo (vía corta + ejemplo del issue) vs g31_rapido, 31B DeepInfra, 8 tareas — 10-nov 00:50
```
callowayproject__bump-my-version-180     rapido: OK 12ll ~90s               ejemplo: OK 12ll ~92s 
googleapis__python-api-core-821          rapido: -- 10ll ~95s               ejemplo: -- 10ll ~97s 
ipython__traitlets-687                   rapido: OK 6ll ~54s                ejemplo: OK 6ll ~53s 
joke2k__faker-2203                       rapido: -- 5ll ~42s Agent exceeded session ti ejemplo: OK 13ll ~155s 
more-itertools__more-itertools-903       rapido: OK 5ll ~41s                ejemplo: OK 5ll ~43s 
pallets__click-2730                      rapido: OK 6ll ~62s                ejemplo: OK 6ll ~64s 
pallets__jinja-2022                      rapido: OK 6ll ~62s                ejemplo: OK 5ll ~57s 
python-semver__python-semver-254         rapido: OK 6ll ~51s                ejemplo: OK 6ll ~49s 
rapido 6 ejemplo 7 de 8
gastado 0.098564

[exited with code 0]
```
**g31_ejemplo 7/8, gana faker y no pierde ninguna.** Elegida para Kaggle.

## E4B DE VERDAD (comprobado en el registro del puente: 217/217 llamadas a gemma-4-e4b), v12.1, sandbox subprocess — 10-nov 14:00
**5/9**: bump-my-version, more-itertools, click, jinja, semver ✅; api-core, traitlets, faker, babel ❌. 80-190 s por tarea, 11-28 llamadas. 0,11 USD.
En el examen la v12 sacó 0,01: incluso con E4B real, el banco local sobreestima muchísimo. Siguiente hipótesis a probar: el entorno Docker del examen.

## E4B real en la RÉPLICA DOCKER del examen (local/docker/, harness con --sandbox docker) — 10-nov 14:40
Las 5 que E4B resolvió en subprocess: **4/5 en Docker** (semver, click, more-itertools, jinja ✅; bump-my-version ❌, 28 llamadas). 104/104 llamadas a E4B. 0,05 USD.
**El entorno Docker NO explica el 0,01 del examen**: los scripts, `.fixer/`, los tests y los tiempos funcionan igual. Lo que queda: las tareas privadas del examen (más difíciles o de otro tipo) y la cuantización de Kaggle (que en las 4 medias dio 3/4).

## Lote de 40 tareas (muestra aleatoria, semilla 10, de las 65 medibles en local) — 10-nov 17:00
DeepInfra, sandbox subprocess, límite real de 8 min. Modelos comprobados en el registro (1.899 llamadas a E4B, 627 al 31B). Gasto 2,00 USD.

| Agente | Modelo | Resueltas | IC 95 % (Wilson) | Llamadas (mediana) | Segundos (mediana) |
|---|---|---|---|---|---|
| `base_comunidad` (agente público, razonamiento 4096, `edit_file`) | E4B | **20/40 (50 %)** | 35-65 % | 26 | 162 |
| `e4b_cmd` (v12, sin razonamiento) | E4B | 16/40 (40 %) | 26-55 % | 19 | 63 |
| `g31_ejemplo` (vía corta + ejemplo) | 31B | 14/40 (35 %) | 22-50 % | 11 | 85 |

Emparejado E4B: solo v12 1, solo público 5, ambos 15. **El agente público con razonamiento resuelve algo más que la v12** (diferencia no significativa con 40 tareas, pero en la misma dirección que el examen: 0,03 frente a 0,01). La v12 es 2,5 veces más rápida y usa menos llamadas. La vía corta del 31B, que dio 7/8 en las tareas elegidas, baja a 14/40 en una muestra aleatoria: el 7/8 tenía sesgo de selección.

## 10-nov — E4B v12 con razonamiento (`e4b_cmd_t`), mismas 40 tareas (semilla 10), E4B real en DeepInfra
| Agente | Modelo | Resueltas | Mediana | Cortes |
|---|---|---|---|---|
| base_comunidad (público, razonamiento 4096) | E4B | 20/40 | 162 s | 0 |
| e4b_cmd v12 (sin razonamiento) | E4B | 16/40 | 63 s | 2 tiempo |
| e4b_cmd_t v12 + razonamiento 4096 | E4B | **10/40** | 150 s | 2 tiempo + 5 límite de 80 turnos |
| g31_ejemplo | 31B | 14/40 | 85 s | 2 |

Emparejado: t frente a v12 → solo t 1, solo v12 7. t frente a público → 1 / 11. 1191 llamadas, todas E4B con razonamiento; 0,67 $.
Conclusión: con la interfaz v12 el razonamiento **empeora** (más llamadas, 5 tareas agotan los 80 turnos). Descartado. El razonamiento ayuda al agente público, no al nuestro.

## 10-nov 20:00 — Agente público sin razonamiento (`e4b_t0`), mismas 40 tareas: cruce 2×2
| E4B | Sin razonamiento | Razonamiento 4096 |
|---|---|---|
| Agente público (`edit_file`) | 14/40 (`e4b_t0`, 67 s) | **20/40** (`base_comunidad`, 162 s) |
| `fixer` v12 (un campo + scripts) | **16/40** (`e4b_cmd`, 63 s) | 10/40 (`e4b_cmd_t`, 150 s) |

El razonamiento suma 6 al público y resta 6 al nuestro. Contraste de interacción por tarea [(pub_t − pub_0) − (fixer_t − fixer_0)]: 11 tareas a favor, 1 en contra, test de signo p = 0,006.
834 llamadas, todas E4B sin razonamiento; 0,39 USD. Tabla completa: `python3 local/tabla_lote.py resultados/local_deepinfra/l40`.

## 10-nov 20:15 — com_v1 (público + git grep -W + primera respuesta herramienta) en las 14 del filo — DESCARTADA
com_v1 8/14 frente a público 12/14 (sus resultados del lote de 40). Solo com_v1 0, solo público 4. 0,22 USD.
En dynaconf-811 leyó más que antes (10 git grep -W) y no llegó a editar. Leer funciones enteras no ahorra llamadas: invita a leer más.
Ojo: el filo se eligió con resultados del público (12/14 a favor), así que la comparación tiene sesgo contra cualquier variante nueva.

## 10-nov 20:40 — com_v2 (público + ejemplo del issue antes y después) en las 14 del filo
com_v2 7/14 frente a público 12/14. Solo com_v2: faker-2203. Solo público: dynaconf-811, traitlets-727, traitlets-773, more-itertools-926, babel-1196, semver-239.
com_v1 y com_v2 pierden las mismas 4 tareas: sospecha de que el 12/14 del público fue con suerte. Se repite el público en las 14 para medir su ruido.

## 10-nov 21:00 — Público repetido en las 14 del filo: 11/14 (antes 12/14)
El público es estable (12 y 11): ruido de ±1 tarea en las 14. com_v1 (8) y com_v2 (7) son peores de verdad.
Las dos variantes pierden traitlets-773 y babel-1196, que el público gana las dos veces: envían un parche, pero equivocado.
Lección: el prompt público ya está muy afinado; añadir instrucciones le quita llamadas y atención. 0,21 USD.

## 10-nov 21:30 — com_v3 (público, "entender antes de editar": editar a más tardar en la llamada 18) en el filo
com_v3 11/14, igual que el público (12 y 11). Gana faker-2203 (el público nunca), dynaconf-811 y pyflakes-675; pierde traitlets-773 y semver-239. Empate: no cumple la regla de ganar por 2.

## 10-nov 22:00 — com_v4 (público + skill repomap como primer paso) en el filo — DESCARTADA
com_v4 8/14 frente a público 12 y 11. El agente NO instaló la skill en ninguna tarea (0/14 llamadas a run_skill_script):
en 3 llamadas intentó `python3 .fixer/map.py` directamente y falló. E4B con razonamiento no sigue una instrucción de
preparación en dos pasos, y añadir pasos al prompt público le quita aciertos (cuarta vez: com_v1 8, com_v2 7, com_v3 11, com_v4 8).
0,31 USD.
