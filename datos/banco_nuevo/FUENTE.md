# Banco de repos nuevos

`validation_tasks.jsonl`: 165 tareas verificadas (fallan sin el arreglo, pasan con él, repetido en sandbox limpio) de 35 repos que no son los 4 públicos de la competición.

- Fuente: dataset de Kaggle `dmitriigluzdov/gemma-4-task-soundness-and-local-results` (Dmitrii Gluzdov), versión del 7-nov-2026.
- Licencia: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Copia sin cambios.
- Los parches de referencia (`patch`) y de tests (`test_patch`) son solo para puntuar: nunca se le enseñan al agente.

El workflow `Banco nuevo` construye los snapshots (`git archive` del commit base, sin historial) y los sube a Kaggle como dataset privado para usarlos con `NERVO_DATA`.
