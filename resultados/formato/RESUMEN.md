# Llamadas rechazadas por formato, por versión (trazas de Kaggle, modelo cuantizado w4a16)

Calculado con `contar_formato.py` sobre los artefactos `salida-kaggle` de cada run (10-nov).

| Versión | Run | Modelo | Tareas | Resueltas | Llamadas | Rechazadas por formato | Ediciones no aplicadas |
|---|---|---|---|---|---|---|---|
| Agentes sin skill (nervo_repro, base_comunidad), `edit_file` | 42370774010 | E4B | 28 | 6 | 423 | 4 (1 %) | 32 |
| Agentes sin skill | 42370845784 | 31B | 16 | 11 | 459 | 3 (1 %) | 2 |
| base_comunidad / e4b_t0 | 42496460738 | E4B | 28 | 6 | 387 | 8 (2 %) | 25 |
| v4: skill con `run_skill_script` (3 campos) | 42528427422 | 31B | 18 | 0 | 770 | 689 (89 %) | 0 |
| v8 | 42667645366 | 31B | 1 | 0 | 80 | 65 (81 %) | 0 |
| v9 (llamada descrita como lista de campos) | 42670592555 | E4B | 1 | 0 | 11 | 2 (18 %) | 0 |
| v10 (+ reintento obligatorio) | 42673741260 | E4B | 1 | 1 | 12 | 4 (33 %) | 1 |
| v10 | 42676719254 | 31B | 1 | 0 | 80 | 65 (81 %) | 0 |
| v11 | 42677347101 | E4B | 1 | 0 | 20 | 6 (30 %) | 0 |
| **v12: instalación única + `run_command` de un campo + textos por archivo** | 42687234244 | E4B | 1 | 0 | 15 | **0** | 0 |
| **v12** | 42708128706 | E4B | 4 | 3 | 66 | **0** | 3 |
| **v12 vía corta + ejemplo** | 42722453454 | 31B | 3 | 1 | 24 | **0** | 1 |

Lectura: los agentes con solo herramientas planas (`edit_file`) casi no rompen el formato (1-2 %), pero E4B pierde muchas ediciones (`old_string` no encontrado). Al añadir código propio vía skills con la llamada de 3 campos, el formato se hunde (81-89 % rechazadas con el 31B). La interfaz de un solo campo de la v12 conserva los scripts y deja el formato en **0 de 105** llamadas.
