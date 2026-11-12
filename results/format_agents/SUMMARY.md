# Tool calls rejected for format, per agent version (Kaggle traces, quantized w4a16 model)

Computed with `count_format.py` over the `salida-kaggle` artifacts of each run (10 November).

| Version | Run | Model | Tasks | Solved | Calls | Rejected for format | Edits not applied |
|---|---|---|---|---|---|---|---|
| Agents without a skill (nervo_repro, community_base), `edit_file` | 42370774010 | E4B | 28 | 6 | 423 | 4 (1 %) | 32 |
| Agents without a skill | 42370845784 | 31B | 16 | 11 | 459 | 3 (1 %) | 2 |
| community_base / e4b_t0 | 42496460738 | E4B | 28 | 6 | 387 | 8 (2 %) | 25 |
| v4: skill through `run_skill_script` (3 fields) | 42528427422 | 31B | 18 | 0 | 770 | 689 (89 %) | 0 |
| v8 | 42667645366 | 31B | 1 | 0 | 80 | 65 (81 %) | 0 |
| v9 (call described as a list of fields) | 42670592555 | E4B | 1 | 0 | 11 | 2 (18 %) | 0 |
| v10 (+ mandatory retry) | 42673741260 | E4B | 1 | 1 | 12 | 4 (33 %) | 1 |
| v10 | 42676719254 | 31B | 1 | 0 | 80 | 65 (81 %) | 0 |
| v11 | 42677347101 | E4B | 1 | 0 | 20 | 6 (30 %) | 0 |
| **v12: one install call + one-field `run_command` + long texts through files** | 42687234244 | E4B | 1 | 0 | 15 | **0** | 0 |
| **v12** | 42708128706 | E4B | 4 | 3 | 66 | **0** | 3 |
| **v12 short path + example** | 42722453454 | 31B | 3 | 1 | 24 | **0** | 1 |

Reading: agents with only flat tools (`edit_file`) almost never break the format (1-2 %), but E4B loses many edits
(`old_string` not found). Adding our own code through skills with the three-field call collapses the format (81-89 %
rejected with the 31B). The one-field interface of v12 keeps the scripts and brings format rejections to **0 of 105**
calls.
