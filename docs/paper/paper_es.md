# El prompt propone, el código decide

*Una interfaz de un solo campo hace fiable y rápido a un Gemma 4 cuantizado como agente de código. No lo hace más listo. Medimos las dos cosas, y lo que el modelo cuantizado no hereda del original.*

## Resumen

Dar herramientas con código propio a un modelo pequeño y cuantizado tiene un coste oculto: el modelo deja de escribir bien las llamadas. En el harness oficial de la competición, al pasar de herramientas planas a *skills* con scripts, Gemma 4 pasó del 1 % al **88 % de llamadas rechazadas por formato**.

Proponemos el protocolo **Nervo**: *el prompt propone, el código decide*. El modelo solo escribe órdenes de una línea y deja los textos largos en archivos; scripts deterministas localizan, editan y verifican ejecutando código. Con esta interfaz, E4B y 31B cuantizados (w4a16) escribieron **0 llamadas mal formadas de 105 en Kaggle**, sin razonamiento.

Medimos también lo que no consigue. En 40 tareas al azar, nuestro agente con E4B resuelve 16 en 63 s de mediana; un agente público con razonamiento, 20 en 162 s (p = 0,22). El cruce 2×2 muestra una interacción clara (p = 0,006): el razonamiento suma 6 tareas al agente público y resta 6 al nuestro. La interfaz compra fiabilidad y velocidad, no capacidad.

Y medimos con los pesos exactos del examen qué cambia al cuantizar: el E4B cuantizado copia mal el código a sustituir el doble de veces, abandona las tareas tras 6-8 llamadas en lugar de 26 y **pierde por completo la ganancia del razonamiento** (de 9 a 5 arreglos de 22 en llamadas sueltas). Las conclusiones sacadas con el modelo sin cuantizar no se trasladan al examen.

Publicamos un banco de 104 tareas validadas con oráculo, un puente entre el harness oficial y cualquier API, un servidor con el modelo cuantizado oficial por céntimos, y un recuperador de contexto que no usa el modelo.

## 1. Introducción

La competición *Gemma 4 Developer Agent* evalúa agentes que arreglan issues reales de repositorios Python. Cada tarea corre en un contenedor sin red, con un límite de 8 minutos, 28 llamadas a herramientas y 80 turnos, y solo cuenta si pasan tests ocultos. El modelo está cuantizado a 4 bits y se sirve con vLLM en 4 GPU L4. El agente se declara en YAML sobre un registro cerrado de nueve herramientas; el único código propio permitido son los scripts de una *skill*.

Ahí está la tensión. Un modelo de 4B edita mal con las herramientas planas: en nuestras trazas, 57 de sus ediciones no se aplicaron porque no copiaba bien el texto a sustituir. Los scripts lo arreglan, pero la llamada que los invoca tiene tres campos y el modelo cuantizado la rompe. Otro equipo midió el mismo síntoma: sin razonamiento, el 24 % de sus llamadas salían mal formadas, frente al 2,2 % con razonamiento [usp787].

Nuestra respuesta fue pedirle menos al modelo. Contribuciones:

1. **Una regla de interfaz** para modelos pequeños cuantizados, con la taxonomía de los cinco fallos de formato que la motivaron (secciones 3 y 4).
2. **Una evaluación honesta:** muestra aleatoria, comparación emparejada, un cruce 2×2 con razonamiento y resultados negativos (sección 7).
3. **Una medida de lo que se pierde al cuantizar**, con llamadas sueltas a los pesos oficiales (sección 8).
4. **Infraestructura abierta** para medir fuera de Kaggle con el harness oficial (sección 6).

## 2. Origen: el protocolo Nervo

Nervo nació antes de esta competición, en **Nervo-Core**, un orquestador en Go de cadenas de prompts. Cada paso es una llamada *one shot* con un prompt corto y distinto, y entre pasos hay **validadores deterministas** (contratos JSON, imports, `py_compile`). Si un paso falla, se reintenta con el error del validador delante. Su laboratorio compara una sola llamada con la cadena sobre **Qwen2.5-0.5B-Instruct**, en 16 problemas de aritmética:

| Perfil | Una llamada | Cadena Nervo | Ganadas / perdidas |
|---|---|---|---|
| `math_short` | 25 % | **62,5 %** | 6 / 0 |
| `math_reasoning` (5 pasos) | 31,25 % | **62,5 %** | 6 / 1 |
| Solo ítems difíciles (5) | 20 % | 0-20 % | sin mejora |

Con 16 ítems es un indicio, no una prueba, pero fijó la hipótesis: descomponer y validar dobla el acierto en lo que el modelo casi sabe hacer y no añade capacidad en lo difícil. Esta competición la pone a prueba en un entorno ajeno, y aparece el mismo patrón.

## 3. Método: el agente `fixer`

El agente es un único `LlmAgent`, sin razonamiento, con tres herramientas del registro oficial (`run_command`, `write_file`, `submit_patch`) y una skill con scripts en Python.

**Instalación única.** La única llamada a la skill (`run_skill_script`, con `args` vacío) copia los scripts a `.fixer/` dentro del repositorio y añade la carpeta a `.git/info/exclude`, así que nunca entra en el parche. Desde ahí, cada paso es un `run_command` de un solo campo.

**Los scripts** hacen lo que un modelo pequeño hace mal:

- `evidence.py` lee el issue de `.fixer/issue.txt` y devuelve funciones candidatas: las de la traza, el punto de entrada del comando citado, los textos del issue que aparecen en el código.
- `show_function.py` y `callers.py` enseñan una función, lo que llama y quién la llama.
- `apply_edit.py` aplica bloques SEARCH/REPLACE tolerantes a espacios; si no encajan, enseña las líneas reales más cercanas. Rechaza cambios cuyo REPLACE es idéntico al SEARCH.
- `verify.py` ejecuta el ejemplo del issue antes y después del cambio, y los casos del modelo, y da un veredicto: `SUBMIT`, `FIX` o `NO_EDIT`.

**Líneas `NEXT`.** Cada script termina con la orden exacta del paso siguiente. El harness resume la conversación cada 15 eventos y, tras el resumen, el modelo pierde el prompt; la última salida de herramienta siempre está presente.

[DIAGRAMA: flujo del agente fixer]

En *faker-2203*, el 31B protegió la primera línea que fallaba y dejó la segunda; `verify.py` devolvió `original -> TypeError` / `con tu arreglo -> AttributeError` / `VERDICT: FIX`, y el modelo corrigió. El modelo propone casos razonables y los evalúa mal de cabeza; por eso, lo que se puede ejecutar lo ejecuta el código.

## 4. Cinco formas de romper una llamada y una regla para evitarlas

Cada fallo apareció en Kaggle, con el modelo cuantizado, y ninguno en pruebas contra APIs comerciales: vLLM deja que el modelo escriba la llamada como texto y después la trocea, y ahí se rompe.

| Fallo observado | Causa | Arreglo |
|---|---|---|
| Llama a una skill con el nombre del agente: 653 errores `SKILL_NOT_FOUND`, 0 de 18 tareas | ADK inyecta "tu nombre interno es X" en cada petición | Mismo nombre para agente y skill |
| La skill no carga | ADK solo admite nombres en *kebab-case* | Validar el nombre antes de enviar |
| E4B escribe la llamada como texto y no la ejecuta | Imitaba la notación `run_skill_script(...)` del prompt | Describir cada llamada como lista de campos |
| Se pierden `skill_name` o `file_path` cuando un argumento es largo | El modelo no cierra la cadena y el parser mezcla los campos | **Textos largos por archivo**, con `write_file` |
| Tras unas 7 llamadas, el 31B repite 64 veces la misma llamada incompleta | La compactación borra el prompt | **Órdenes de un solo campo** y líneas `NEXT` |

La regla: **cada llamada, los menos campos posibles y ningún texto largo dentro.** Llamadas rechazadas por formato en las trazas de Kaggle:

| Interfaz | Modelo | Llamadas | Rechazadas por formato | Ediciones no aplicadas |
|---|---|---|---|---|
| Herramientas planas (`edit_file`), agentes de referencia | E4B | 810 | 12 (1,5 %) | 57 |
| Herramientas planas, agentes de referencia | 31B | 459 | 3 (0,7 %) | 2 |
| Skill con llamada de 3 campos | 31B | 930 | 819 (88 %) | 0 |
| Skill con llamada de 3 campos y reintento | E4B | 43 | 12 (28 %) | 1 |
| **Instalación única + órdenes de un campo** | E4B y 31B | 105 | **0** | 4 |

La interfaz de un campo conserva los scripts y deja **0 de 105** llamadas rechazadas, sin razonamiento (cota superior al 95 %: 2,8 %).

**Latencia.** El 31B cuantizado genera unos 33 tokens/s en 4 L4: una llamada que ejecuta un script (60 tokens) tarda 4-5 s aunque lea 16.000; una que escribe un cambio (950 tokens), 30 s. El tiempo lo decide lo que el modelo escribe. De ahí una **vía corta** para el 31B (sin script de casos obligatorio, con `apply_edit.py` lanzando la verificación): 25-65 s por tarea en Kaggle.

## 5. Recuperación sin modelo: el *dossier*

Si localizar es caro para el modelo, que lo haga el código. `dossier.py` recibe el issue y, sin llamar al modelo, construye un informe por secciones, cada una con una instrucción delante: dónde mirar (funciones de la traza de ejecución del ejemplo del issue, BM25 sobre cuerpos de función y nombres exactos), el código de las candidatas, patrones hermanos en el mismo archivo y los tests existentes que las tocan, con el aviso explícito de que pasarlos no prueba el arreglo. `mapa.py` da un mapa del repositorio con clases y métodos, y si el modelo nombra un símbolo que no existe, se le devuelven los reales más cercanos.

Medido contra el parche oficial, sin modelo:

| Conjunto | Función del arreglo en las 3 primeras | Archivo en las 3 primeras | Issues con ejemplo ejecutable |
|---|---|---|---|
| Banco, 40 al azar | 28 / 40 | 34 / 40 | 7 / 40 |
| Tareas oficiales de desarrollo | 38 / 72 | 41 / 72 | **0 / 72** |

Los enunciados oficiales son descripciones de *pull request*, no issues: mediana de 78 palabras frente a 112 del banco, y 23 de 72 con menos de 30 (2 de 40 en el banco). Ninguno trae un ejemplo que nuestro extractor pueda ejecutar, así que la validación por ejecución de la sección 3 nunca se activa en el examen. Es una diferencia de distribución que un banco de issues no mide.

## 6. Un banco de pruebas fuera de Kaggle

Con 30 h de GPU a la semana (que se nos agotaron el 11 de noviembre) y un envío al día no se puede iterar. Construimos cuatro piezas que usan el **harness oficial sin modificar**:

1. **Un banco de 104 tareas** de 35 repositorios distintos de los de desarrollo, a partir de un conjunto público (CC BY 4.0, [dmitriigluzdov]); conservamos las que el oráculo oficial resuelve en Kaggle (65 también en local).
2. **Un puente de inferencia** (`shim_vllm.py`) que se presenta ante el harness como vLLM y reenvía a cualquier API compatible con OpenAI, con tope de gasto. Un lote de 40 tareas cuesta unos 0,7 dólares.
3. **Una réplica Docker del sandbox** (sin red, 2 CPU, 4 GB) reconstruida desde el código del harness.
4. **Un servidor con el modelo del examen** en Modal: los pesos `qat-w4a16-ct` oficiales, vLLM 0.19.1 y los parsers de Gemma 4, con las versiones del wheelhouse de la competición. Se apaga solo tras 5 minutos sin uso; las sondas de la sección 8 costaron céntimos.

**Ruido.** Con 58 tareas públicas, una vale 0,017 puntos; el agente público más enviado varía ±1,5 tareas entre envíos idénticos [Afshar]. Y la ejecución no es reproducible: en Kaggle, con temperatura 0 y semilla fija, **0 de 8 trayectorias** salieron idénticas; con la misma entrada, el modelo diverge en la llamada 3-5. vLLM no es invariante al lote y el zip no lo puede controlar. Hay que medir con muestras, nunca con una ejecución.

## 7. Resultados

**Cruce 2×2 en 40 tareas al azar** (semilla fija sobre las 65 medibles en local; harness oficial; E4B sin cuantizar por API; una ejecución por celda):

| E4B | Sin razonamiento | Razonamiento 4096 |
|---|---|---|
| Agente público (`edit_file`) | 14 / 40, 67 s | **20 / 40**, 162 s |
| `fixer` (un campo + scripts) | **16 / 40**, 63 s | 10 / 40, 150 s |

Intervalos de Wilson al 95 %: de 14-40 % (10/40) a 35-65 % (20/40). Tres lecturas:

- **La interfaz no resuelve más que el agente público.** Emparejados contra el mejor público: 5 tareas solo para él y 1 solo para `fixer` (McNemar exacto, p = 0,22). Sí es 2,5 veces más rápida.
- **El razonamiento interactúa con la estructura.** Suma 6 tareas al agente público y resta 6 al nuestro; en el contraste por tarea, 11 a favor de la interacción y 1 en contra (test de signo, p = 0,006). Con los pasos ya fijados por los scripts, pensar añade vueltas (cinco tareas agotan los 80 turnos), no criterio.
- **El 31B con la vía corta resuelve 14**, todas dentro de las 16 de E4B. En las tareas con las que la afinamos resolvía 7 de 8: el ajuste engaña.

Cambiar el prompt del agente público no lo mejoró: cuatro variantes en las 14 tareas que discriminan sacaron 7, 8, 8 y 11, frente a 12 y 11 del original en dos repeticiones.

**Kaggle y examen**, con el modelo cuantizado:

| Dónde | Modelo | Agente | Resultado |
|---|---|---|---|
| Kaggle, banco (4 tareas medias) | E4B | `fixer` | 3 / 4 |
| Kaggle, 8 tareas oficiales | E4B | público (3 ejecuciones) | 1, 2 y 1 de 8 |
| Kaggle, 8 tareas oficiales | 31B | dossier, temperatura 0 | **4 / 8** |
| Examen, leaderboard público (58) | E4B | público | 0,03 (2 tareas) |
| Examen, leaderboard público | E4B | `fixer` | 0,01 (1 tarea) |
| Examen, leaderboard público | 31B | agente anterior, sin scripts | 0,18 (11 tareas) |

El 4/8 es una sola ejecución: sus fallos fueron dos cortes por tiempo, uno por turnos y un arreglo equivocado. La variante dossier del 31B con temperatura 0,2 dio 1 de 4 y 3 de 3 en dos ejecuciones sobre casi las mismas tareas del banco, con horas de diferencia.

**La brecha banco-examen.** E4B resuelve el 40-50 % del banco local y el 2-3 % del examen. Descartamos el entorno (Docker, formato, versión de Python). Quedan tres causas, las tres medidas: los enunciados oficiales son más pobres (sección 5), el E4B cuantizado abandona pronto y escribe peor (sección 8), y el banco usa un modelo sin cuantizar. Un banco local sirve para comparar versiones entre sí, no para predecir la nota.

**Lo que no funcionó**, además del razonamiento en `fixer`: un paso final de revisión que señalaba lo que faltaba (el modelo lo leyó y envió sin cambios, 0 de 4); exigir que los casos fallen antes del cambio (mismos aciertos, 3-4 veces más tiempo); y, en Kaggle, el dossier con E4B: localiza la función correcta más a menudo, pero el cambio que escribe sigue siendo incorrecto.

## 8. Lo que el modelo cuantizado no hereda

Para separar al modelo del agente, hicimos llamadas sueltas a E4B: nosotros damos el contexto, el modelo responde una vez y el código puntúa con los tests ocultos. Las mismas preguntas, con los pesos sin cuantizar (API) y con los oficiales cuantizados (nuestro servidor):

| Llamada suelta, E4B | Sin cuantizar | Cuantizado |
|---|---|---|
| Arreglo sin razonar (22 intentos, 11 tareas difíciles) | 5 | 5 |
| Arreglo razonando | **9** | **5** |
| Arreglo con los tests existentes como contexto, sin razonar | 5 | 6 |
| Intentos perdidos porque el SEARCH no coincide con el código | 12 de 88 | **24 de 88** |
| Localización del símbolo, 40 tareas: lista de archivos / mapa | 28 / 31 | 24 / 29 |

En Kaggle, el mismo agente público con E4B cuantizado usa una mediana de **6,5-8,5 llamadas por tarea, frente a 26** sin cuantizar. En *traitlets-773* edita a ciegas en la llamada 7, ve pasar los tests existentes y envía; sin cuantizar, la misma tarea sale 2 de 2 con 27 llamadas.

Cuatro conclusiones. Primera, **razonar ya no ayuda a arreglar** con el modelo cuantizado, y subir el presupuesto a 12.288 tokens en Kaggle no cambió nada (genera unos 200 por llamada). Segunda, el cuantizado **copia mal el texto a sustituir** el doble de veces, pero eso no es lo que le cuesta tareas: si reescribe la función entera y el código la sustituye por su nombre, los fallos de copia desaparecen y resuelve lo mismo (6 frente a 5 de 18 intentos). Lo que falla es el contenido del cambio. Tercera, **el mapa sigue ayudando** (+5 símbolos) y localizar no es el cuello de botella: con el archivo correcto, 55 de 64 intentos fallan igual. Cuarta, los tests existentes no aportan. Todo lo que medimos con el modelo sin cuantizar sobre razonamiento debe leerse con esta tabla al lado.

## 9. Trabajo relacionado

**SWE-bench** [Jimenez et al.] fijó el formato de esta evaluación: un issue real, un parche, tests ocultos. **SWE-agent** [Yang et al.] mostró que la interfaz entre el agente y el ordenador pesa tanto como el modelo. SWE-agent diseña la interfaz para que el modelo trabaje cómodo; nosotros, para que un modelo pequeño y cuantizado no pueda escribirla mal, y medimos el efecto en un harness ajeno y con los pesos cuantizados.

### Referencias

- [Jimenez et al.] C. E. Jimenez et al. *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024.
- [Yang et al.] J. Yang et al. *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering.* NeurIPS 2024.
- [usp787] [Gemma4_paper_track](https://github.com/usp787/Gemma4_paper_track), repositorio de un participante: razonamiento y llamadas mal formadas.
- [Afshar] D. Afshar, [Gemma 4: most-run public config averages 10/58](https://www.kaggle.com/code/dariushafshar/gemma-4-most-run-public-config-averages-10-58), notebook de Kaggle.
- [dmitriigluzdov] [gemma-4-task-soundness-and-local-results](https://www.kaggle.com/datasets/dmitriigluzdov/gemma-4-task-soundness-and-local-results), dataset de Kaggle, CC BY 4.0.

## 10. Conclusión

Con un modelo pequeño y cuantizado, la interfaz decide si el agente funciona; no decide cuánto resuelve. Cuatro reglas valen fuera de esta competición:

1. **Cada llamada, un solo campo; los textos largos, por archivo.** Del 88 % de llamadas rechazadas a ninguna.
2. **Lo que se pueda ejecutar, que lo ejecute el código**, y lo que se pueda buscar, que lo busque: el dossier pone la función correcta entre las tres primeras en la mitad de las tareas oficiales sin gastar una llamada.
3. **No tomar el razonamiento como una mejora fija.** Interactúa con la estructura del agente y desaparece al cuantizar.
4. **Medir con muestras al azar, emparejadas y con los pesos del examen.** Nuestras tareas de ajuste decían 7 de 8; el azar, 14 de 40; el modelo cuantizado, otra cosa.

Es el patrón que ya vimos en Nervo-Core con un modelo de 0,5B: la estructura y la validación hacen fiable lo que el modelo ya sabe hacer, y no le dan lo que le falta.

## Reproducir

Todo está en el [repositorio](https://github.com/RobertoVetere/nervo-gemma-paper) (etiqueta `paper-v1`): agentes en `variantes/`, resultados por tarea en `resultados/`, cada ejecución de Kaggle en `docs/HISTORIAL_EJECUCIONES.md` y las llamadas sueltas en `lab/oneshot/`. El cruce 2×2 se regenera sin coste desde los resultados guardados con `python3 local/tabla_lote.py resultados/local_deepinfra/l40`; `docs/REPRODUCIR.md` detalla el montaje y cada cifra.
