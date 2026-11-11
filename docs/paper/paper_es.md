# El prompt propone, el código decide: diseño de interfaces para agentes de código pequeños y cuantizados

## Resumen

Los modelos de lenguaje pequeños servidos con pesos de 4 bits son atractivos para agentes de código locales, pero se sabe poco de cómo conectarlos a un agente. Estudiamos Gemma 4 E4B y 31B (w4a16) como agentes que reparan repositorios con límites estrictos de tiempo, llamadas a herramientas y turnos, puntuados con tests ocultos. Aportamos cuatro resultados, de solidez desigual. (1) Las llamadas a herramientas se rompen de cinco formas recurrentes; una interfaz en la que cada llamada tiene un solo campo y los textos largos viajan por archivos reduce las llamadas rechazadas del 88 % a 0 de 105. (2) El razonamiento no es una ganancia fija: en 40 tareas al azar suma seis tareas resueltas a un agente libre y resta seis a uno guiado por scripts (interacción, test de signo p = 0,006, una ejecución por celda). (3) La cuantización no es neutra: con entradas idénticas, el E4B cuantizado copia mal el código a sustituir el doble de veces (24 frente a 12 de 88 intentos, p = 0,04), y la ganancia del razonamiento que se ve en precisión completa en arreglos de una llamada (5 → 9 de 22) no aparece (5 → 5), una observación con muestra pequeña coherente con lo visto dentro del agente. (4) Las prácticas habituales de evaluación engañan: las tareas de ajuste inflan el acierto (7/8 frente a 14/40 al azar), las ejecuciones no se repiten ni con temperatura 0, y los bancos basados en issues difieren, de formas que anulan las comprobaciones por ejecución, de las descripciones escuetas de *pull requests*. Publicamos los agentes, un banco de 104 tareas validadas con oráculo, un puente que ejecuta el evaluador oficial contra cualquier API y un servidor con los pesos cuantizados exactos.

## 1. Introducción

Los agentes de código suelen construirse para modelos grandes detrás de APIs comerciales. Un modelo pequeño que corre en local, cuantizado para caber en hardware modesto, cambia el problema: escribe las llamadas a herramientas con menos fiabilidad, edita con menos precisión y su presupuesto de tiempo lo consumen los tokens que escribe. Qué decisiones de diseño se trasladan a este régimen está, en gran parte, sin probar.

Partimos de una postura de diseño que llamamos *el prompt propone, el código decide*. El modelo elige qué cambiar; scripts deterministas localizan el código, aplican los cambios y ejecutan comprobaciones, y sus veredictos, no la autoevaluación del modelo, deciden el paso siguiente. La postura viene de un orquestador anterior de cadenas de prompts en el que validar cada paso subió a un modelo de 0,5B del 25 % al 62,5 % en 16 problemas de aritmética, sin ayudar en los cinco más difíciles.

La evaluamos en reparación de repositorios: dado un issue y una copia del repositorio, producir un parche que pase tests ocultos. Nuestras contribuciones son medidas, no un puesto en una clasificación:

1. Una taxonomía de los fallos de llamadas de los modelos cuantizados y una regla de interfaz que los elimina (sección 4.1).
2. Evidencia de que el razonamiento interactúa con la estructura del agente (sección 4.2).
3. Una comparación entre pesos cuantizados y de precisión completa con entradas idénticas (sección 4.3), pequeña pero emparejada.
4. Un recuperador sin modelo y un análisis de dónde están los fallos que quedan (sección 4.4), y tres trampas de evaluación (sección 5).

## 2. Escenario

**Tarea.** Cada instancia es un repositorio real de Python en un commit fijo, el texto de un issue y tests ocultos (los que deben pasar a funcionar y los que deben seguir funcionando). Se resuelve si el parche del agente hace pasar todos. Los agentes corren en un sandbox sin red con límites de 8 minutos, 28 llamadas a herramientas y 80 turnos del modelo.

**Modelos y servicio.** Gemma 4 E4B y Gemma 4 31B, con pesos de 4 bits y activaciones de 16 (w4a16), servidos con vLLM 0.19.1 en cuatro GPU NVIDIA L4 con los parsers de llamadas y de razonamiento de Gemma 4 y 32k de contexto.

**Marco del agente.** Los agentes se declaran en YAML sobre el Agent Development Kit de Google y solo pueden usar un conjunto cerrado de nueve herramientas (comando de terminal, leer/escribir/editar archivos, enviar el parche y consultas al grafo de código). El único código propio permitido son los scripts de una *skill*, invocados con una llamada de tres campos. El marco resume la conversación cada 15 eventos. Es el entorno de la competición de Kaggle *Gemma 4 Developer Agent*, cuyo evaluador oficial usamos sin modificar.

**Datos.** *Banco*: 104 instancias de 24 repositorios, tomadas de una colección pública CC BY 4.0 [4] y conservadas solo si el oráculo oficial las resuelve con el parche de referencia; 65 se pueden resolver también en nuestro entorno local. *Oficiales*: 72 instancias de desarrollo medibles en local, de tres repositorios. Salvo que se diga otra cosa, todas las condiciones usan las mismas instancias y las comparaciones son emparejadas.

## 3. Diseño

El agente `fixer` tiene tres herramientas (`run_command`, `write_file`, `submit_patch`) y una skill. Su única llamada a la skill copia los scripts en una carpeta del repositorio que git ignora; desde ahí, cada paso es un comando de un solo campo:

- `evidence.py` lee el issue de un archivo y lista funciones candidatas (de las trazas de error, del punto de entrada de cualquier comando citado y de los textos del issue que aparecen en el código);
- `show_function.py` y `callers.py` enseñan una función, lo que llama y quién la llama;
- `apply_edit.py` aplica bloques de búsqueda y sustitución tolerantes a espacios y, si no encajan, enseña las líneas reales más cercanas;
- `verify.py` ejecuta el propio ejemplo del issue antes y después del cambio y devuelve `SUBMIT`, `FIX` o `NO_EDIT`.

Cada script termina con una línea `NEXT:` con la orden exacta siguiente, porque tras un resumen el modelo ya no ve sus instrucciones pero siempre ve la última salida de herramienta.

[FIGURA 1: flujo de fixer — instalar, issue a archivo, evidencia, cambio, verificación, decisión]

La ejecución sustituye al juicio donde se puede. En una instancia, el 31B protegió la primera línea que fallaba en el ejemplo del issue y se dejó la segunda; `verify.py` devolvió `original → TypeError`, `con tu arreglo → AttributeError`, `VERDICT: FIX`, y el modelo completó el arreglo.

## 4. Resultados

### 4.1 Las llamadas se rompen de formas predecibles

Observamos los cinco en ejecuciones con el modelo cuantizado. Los dos primeros vienen de convenciones del marco; los tres últimos, de cómo escribe el modelo las llamadas cuando vLLM las extrae de texto libre, y no aparecieron cuando los mismos agentes corrieron contra una API comercial que devuelve llamadas estructuradas.

| Fallo | Causa | Remedio |
|---|---|---|
| Llama a la skill con el nombre del agente (653 errores, 0 de 18 tareas) | El marco inyecta "tu nombre interno es X" en cada petición | Mismo nombre para agente y skill |
| La skill no carga | Solo admite nombres en *kebab-case* | Validar los nombres antes de ejecutar |
| Escribe la llamada como texto y nunca se ejecuta | Imitaba la notación de llamada tipo código del prompt | Describir las llamadas como listas de campos |
| Se pierden campos cuando un argumento es largo | El modelo no cierra la cadena y el parser mezcla campos | Textos largos por archivo |
| Repite 64 veces la misma llamada incompleta | El resumen borra el prompt | Órdenes de un campo y líneas `NEXT` |

| Interfaz | Modelo | Llamadas | Rechazadas por formato | Cambios no aplicados |
|---|---|---|---|---|
| Herramientas planas (`edit_file`) | E4B | 810 | 12 (1,5 %) | 57 |
| Herramientas planas | 31B | 459 | 3 (0,7 %) | 2 |
| Skill, llamada de tres campos | 31B | 930 | 819 (88 %) | 0 |
| Skill, llamada de tres campos (tres versiones del prompt) | E4B | 43 | 12 (28 %) | 1 |
| **Instalación única + órdenes de un campo** | E4B, 31B | 105 | **0** (cota superior al 95 %: 2,8 %) | 4 |

Las herramientas planas casi nunca fallan por formato, pero el modelo pequeño pierde cambios porque no reproduce el texto a sustituir. Los scripts arreglan los cambios, pero la llamada que los invoca se hunde. La interfaz de un campo conserva los scripts y elimina los fallos de formato, sin razonamiento.

### 4.2 El razonamiento interactúa con la estructura del agente

Cruzamos dos agentes con dos configuraciones de razonamiento en 40 instancias del banco elegidas con semilla fija, con el E4B de precisión completa por API y el evaluador oficial (una ejecución por celda).

| E4B, 40 tareas | Sin razonamiento | Razonamiento (4.096 tokens) |
|---|---|---|
| Agente libre (`edit_file`) | 14 (67 s) | **20** (162 s) |
| `fixer` (scripts, llamadas de un campo) | **16** (63 s) | 10 (150 s) |

*Tareas resueltas; mediana de segundos por tarea. Los intervalos de Wilson al 95 % van del 14-40 % (10/40) al 35-65 % (20/40).*

Las mejores celdas no difieren de forma significativa (5 tareas solo las resuelve el agente libre y 1 solo `fixer`; McNemar exacto, p = 0,22), pero `fixer` es 2,5 veces más rápido. El razonamiento mueve a los dos agentes en direcciones opuestas: en el contraste por tarea (ganancia del agente libre menos ganancia de `fixer`), 11 tareas apoyan la interacción y 1 va en contra (test de signo, p = 0,006). Con razonamiento, `fixer` agotó el límite de turnos en cinco tareas (ninguna sin él): cuando los pasos ya los fijan los scripts, pensar añade vueltas, no criterio.

![Figura 2: tareas resueltas de 40 por agente y razonamiento. Las líneas se cruzan: el razonamiento ayuda al agente libre y perjudica al guiado por scripts.](fig_interaction.png)

Una versión reducida de `fixer` con el 31B resuelve 14, todas dentro de las 16 del modelo pequeño: en estas instancias el tamaño del modelo no sustituyó a la interfaz.

Cambiar el prompt del agente libre no lo mejoró: cuatro variantes (leer funciones enteras, ejecutar el ejemplo del issue, "entender antes de editar", un mapa del repositorio) resolvieron 7, 8, 8 y 11 de 14 instancias discriminantes, frente a 12 y 11 del original en dos repeticiones (las instancias se eligieron con los resultados del original, lo que le favorece).

### 4.3 Qué cambia la cuantización

Para separar el modelo del agente, hicimos llamadas sueltas: nosotros damos el contexto, el modelo responde una vez y los tests ocultos puntúan la respuesta. Hicimos las mismas preguntas al E4B de precisión completa y a los pesos oficiales w4a16, servidos con la misma versión de vLLM.

| Llamada suelta, E4B | Precisión completa | w4a16 |
|---|---|---|
| Arreglo sin razonamiento (22 intentos, 11 instancias) | 5 | 5 |
| Arreglo con razonamiento | **9** | **5** |
| Arreglo con los tests existentes añadidos al contexto | 5 | 6 |
| Intentos perdidos porque el texto buscado no coincide con el código | 12 de 88 | **24 de 88** |
| Localización en 40 tareas, símbolo correcto: lista de archivos / mapa del repositorio | 28 / 31 | 24 / 29 |

Con 22 intentos por celda, la diferencia en la ganancia del razonamiento (+4 frente a 0) no es significativa por sí sola (9/22 frente a 5/22, Fisher p = 0,33); los fallos de copia sí lo son (24/88 frente a 12/88, p = 0,04), y las diferencias de localización no. Dos observaciones dentro del agente apuntan en la misma dirección que la del razonamiento. Subir el presupuesto de razonamiento a 12.288 tokens dentro del agente libre no cambió nada (1 de 6 tareas en ambos casos): el modelo cuantizado escribía unos 200 tokens por llamada y solo 2 de 76 llamadas pasaron de 4.096. Y el E4B cuantizado dentro del agente libre usó una mediana de 6,5 a 18 llamadas por tarea en cuatro ejecuciones, frente a 26 en precisión completa en la muestra de 40; los conjuntos de tareas difieren, pero en la única instancia presente en ambos, el modelo cuantizado editó a ciegas en la llamada 7, vio pasar los tests existentes y envió un parche equivocado, mientras que el de precisión completa la resolvió en sus dos ejecuciones con 27 llamadas.

Por tanto, las conclusiones sobre el razonamiento sacadas con pesos de precisión completa hay que volver a comprobarlas con los pesos desplegados antes de fiarse de ellas.

### 4.4 Dónde están los fallos que quedan

**Localizar no es el cuello de botella.** Un recuperador sin modelo (`dossier.py`) construye un informe por secciones a partir del issue: funciones de la traza de ejecución del ejemplo del issue, BM25 sobre cuerpos de función, coincidencias exactas de identificadores, el código de las candidatas, implementaciones hermanas en el mismo archivo y los tests existentes que las tocan, cada sección con una instrucción delante (para los tests: pasarlos no prueba el arreglo). Contra los parches de referencia, pone la función cambiada entre sus tres primeras en 28 de 40 instancias del banco y 38 de 72 oficiales, sin coste de modelo. Con el archivo correcto en la mano, 55 de 64 intentos de arreglo en una llamada del E4B cuantizado siguen fallando.

**Tampoco el formato del cambio.** Como el modelo cuantizado copia mal el texto buscado el doble de veces, le dejamos reescribir la función entera y la sustituimos por su nombre desde el código. Los fallos de copia desaparecieron, pero los intentos resueltos se quedaron igual (6 frente a 5 de los 18 intentos en los que el objetivo era una función). Lo que falla es el contenido del cambio.

**Ahí el tamaño del modelo sí ayuda.** Con el 31B, un agente construido sobre el recuperador resolvió 4 de 8 instancias oficiales en una sola ejecución, frente a 1-2 de 8 del modelo pequeño con el agente libre en tres ejecuciones. Son ejecuciones pequeñas y sueltas; lo damos como dirección, no como resultado.

## 5. Trampas de evaluación

**Las tareas de ajuste inflan.** El agente del 31B resolvía 7 de las 8 instancias con las que se diseñó y 14 de 40 al azar.

**Las ejecuciones no se repiten.** Con temperatura 0, `top_p` 1 y semilla fija, 0 de 8 trayectorias fueron idénticas entre dos ejecuciones sobre las mismas instancias; con entradas idénticas, divergían en la llamada 3-5. Los kernels por lotes de vLLM no son invariantes al lote y ningún ajuste del cliente lo controla. Cada ejecución hay que leerla como una muestra.

**Los bancos no se parecen al despliegue.** Las instancias oficiales son descripciones de *pull requests*, no issues: mediana de 78 palabras frente a 112 en el banco, 23 de 72 con menos de 30 palabras (2 de 40 en el banco), y ninguna con un ejemplo que nuestro extractor pueda ejecutar (7 de 40 en el banco). Las comprobaciones por ejecución como `verify.py` nunca se activan en ellas. Con pesos de precisión completa, el modelo pequeño resolvía el 40-50 % del banco; con los pesos desplegados, los mismos agentes sacaron 0,01 y 0,03 en un conjunto reservado de 58 instancias (en torno a 1-2 resueltas). El entorno no explicó la diferencia (una réplica Docker del sandbox reprodujo 4 de 5 resultados del banco), lo que deja los enunciados y los pesos. Un banco local ordena versiones; no predice el despliegue.

## 6. Trabajo relacionado

SWE-bench [1] definió la reparación de repositorios con tests ocultos; SWE-agent [2] mostró que la interfaz entre el agente y el ordenador importa tanto como el modelo. Compartimos esa tesis pero apuntamos al extremo opuesto: una interfaz diseñada para que un modelo pequeño y cuantizado no pueda escribirla mal, medida con los pesos desplegados. Nuestros resultados sobre el razonamiento se suman a la evidencia de que pensar en tiempo de inferencia ayuda al formato de las llamadas en modelos pequeños [3], y muestran que su valor depende de la estructura del agente y de la cuantización.

## 7. Limitaciones

La mayoría de las comparaciones usan una ejecución por condición en 40 instancias o menos, así que solo se detectan efectos grandes, y las ejecuciones no se repiten (sección 5). El cruce 2×2 usó pesos de precisión completa; la sección 4.3 sugiere que su efecto del razonamiento se reduciría con el modelo desplegado. Los dos agentes del cruce difieren en más que el razonamiento. Las llamadas sueltas cubren 11 instancias con dos muestras cada una, demasiado pocas para que la diferencia del razonamiento sea significativa. Todos los resultados son de una familia de modelos y un marco de agentes.

## 8. Conclusión

Con modelos pequeños y cuantizados, la interfaz decide si un agente funciona, no cuánto resuelve. Las llamadas de un campo con los textos en archivos hacen fiable el uso de herramientas; los scripts abaratan la localización y la verificación; ninguna de las dos cosas arregla el contenido del cambio, que es donde están los fallos que quedan. El razonamiento y la cuantización interactúan con estas decisiones, así que los diseños de agentes deben validarse con los pesos desplegados, con muestras al azar, comparaciones emparejadas y ejecuciones repetidas.

## Reproducibilidad

Código, agentes, datos y resultados por tarea: https://github.com/RobertoVetere/nervo-gemma-paper (etiqueta `paper-v1`). `docs/REPRODUCIR.md` asocia cada cifra a un archivo y una orden; la tabla 2×2 se regenera sin coste con `python3 local/tabla_lote.py resultados/local_deepinfra/l40`.

## Referencias

[1] C. E. Jimenez et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.
[2] J. Yang et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 2024.
[3] usp787. Gemma4_paper_track. https://github.com/usp787/Gemma4_paper_track
[4] D. Gluzdov. gemma-4-task-soundness-and-local-results (dataset, CC BY 4.0). Kaggle.
