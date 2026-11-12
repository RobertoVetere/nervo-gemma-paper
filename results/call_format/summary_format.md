Model labels: e4b, e2b = official 4-bit (QAT w4a16) weights on our vLLM server; -bf16 = original weights; "31B (API; asked for e4b)" = DeepInfra, which served a 31B for E4B requests.

| Backend | Model | Interface | Calls | Not called | Fields lost / unparsable | Text not exact | Exact |
|---|---|---|---|---|---|---|---|
| deepinfra | 31B (API; asked for e4b) | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | 31B (API; asked for e4b) | one_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | 31B (API; asked for e4b) | three_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | 31B (API; asked for e4b)+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | 31B (API; asked for e4b)+ctx36k | one_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | 31B (API; asked for e4b)+ctx36k | three_field | 160 | 0 | 6 | 0 | 154 (96%) |
| modal | e2b 4-bit | edit_file | 160 | 0 | 35 | 3 | 122 (76%) |
| modal | e2b 4-bit | one_field | 160 | 0 | 149 | 0 | 11 (7%) |
| modal | e2b 4-bit | three_field | 160 | 0 | 87 | 2 | 71 (44%) |
| modal | e2b 4-bit+ctx36k | edit_file | 160 | 0 | 27 | 9 | 124 (78%) |
| modal | e2b 4-bit+ctx36k | one_field | 160 | 0 | 146 | 0 | 14 (9%) |
| modal | e2b 4-bit+ctx36k | three_field | 160 | 1 | 104 | 3 | 52 (32%) |
| modal | e2b-bf16 | edit_file | 160 | 0 | 10 | 2 | 148 (92%) |
| modal | e2b-bf16 | one_field | 160 | 0 | 142 | 2 | 16 (10%) |
| modal | e2b-bf16 | three_field | 160 | 0 | 41 | 9 | 110 (69%) |
| modal | e2b-bf16+ctx36k | edit_file | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e2b-bf16+ctx36k | one_field | 160 | 0 | 127 | 2 | 31 (19%) |
| modal | e2b-bf16+ctx36k | three_field | 160 | 0 | 68 | 9 | 83 (52%) |
| modal | e4b 4-bit | edit_file | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b 4-bit | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b 4-bit | three_field | 160 | 0 | 4 | 4 | 152 (95%) |
| modal | e4b 4-bit+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b 4-bit+ctx36k | one_field | 160 | 0 | 1 | 2 | 157 (98%) |
| modal | e4b 4-bit+ctx36k | three_field | 160 | 0 | 21 | 0 | 139 (87%) |
| modal | e4b-bf16 | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b-bf16 | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b-bf16 | three_field | 160 | 0 | 7 | 2 | 151 (94%) |
| modal | e4b-bf16+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b-bf16+ctx36k | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b-bf16+ctx36k | three_field | 160 | 0 | 6 | 0 | 154 (96%) |
| modal | qwen3-1.7b-bf16 | edit_file | 160 | 27 | 3 | 130 | 0 (0%) |
| modal | qwen3-1.7b-bf16 | one_field | 160 | 1 | 0 | 159 | 0 (0%) |
| modal | qwen3-1.7b-bf16 | three_field | 160 | 7 | 2 | 151 | 0 (0%) |
| modal | qwen3-1.7b-bf16+ctx36k | edit_file | 160 | 53 | 21 | 80 | 6 (4%) |
| modal | qwen3-1.7b-bf16+ctx36k | one_field | 160 | 15 | 13 | 132 | 0 (0%) |
| modal | qwen3-1.7b-bf16+ctx36k | three_field | 160 | 103 | 10 | 47 | 0 (0%) |
| modal | qwen3-4b AWQ 4-bit | edit_file | 160 | 71 | 21 | 14 | 54 (34%) |
| modal | qwen3-4b AWQ 4-bit | one_field | 160 | 2 | 4 | 154 | 0 (0%) |
| modal | qwen3-4b AWQ 4-bit | three_field | 160 | 114 | 2 | 6 | 38 (24%) |
| modal | qwen3-4b AWQ 4-bit+ctx36k | edit_file | 160 | 75 | 4 | 24 | 57 (36%) |
| modal | qwen3-4b AWQ 4-bit+ctx36k | one_field | 160 | 8 | 15 | 137 | 0 (0%) |
| modal | qwen3-4b AWQ 4-bit+ctx36k | three_field | 160 | 100 | 0 | 18 | 42 (26%) |
| modal | qwen3-4b-bf16 | edit_file | 160 | 71 | 28 | 16 | 45 (28%) |
| modal | qwen3-4b-bf16 | one_field | 160 | 0 | 0 | 160 | 0 (0%) |
| modal | qwen3-4b-bf16 | three_field | 160 | 103 | 0 | 7 | 50 (31%) |
| modal | qwen3-4b-bf16+ctx36k | edit_file | 160 | 73 | 11 | 15 | 61 (38%) |
| modal | qwen3-4b-bf16+ctx36k | one_field | 160 | 0 | 1 | 159 | 0 (0%) |
| modal | qwen3-4b-bf16+ctx36k | three_field | 160 | 101 | 0 | 9 | 50 (31%) |

31B (API; asked for e4b) edit_file: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
31B (API; asked for e4b) one_field: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
31B (API; asked for e4b) three_field: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
31B (API; asked for e4b)+ctx36k edit_file: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
31B (API; asked for e4b)+ctx36k one_field: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
31B (API; asked for e4b)+ctx36k three_field: failures ending in quote 1/50, other 5/110, Fisher p = 0.666
e2b 4-bit edit_file: failures ending in quote 2/50, other 36/110, Fisher p = 0.000
e2b 4-bit one_field: failures ending in quote 50/50, other 99/110, Fisher p = 0.018
e2b 4-bit three_field: failures ending in quote 12/50, other 77/110, Fisher p = 0.000
e2b 4-bit+ctx36k edit_file: failures ending in quote 4/50, other 32/110, Fisher p = 0.004
e2b 4-bit+ctx36k one_field: failures ending in quote 50/50, other 96/110, Fisher p = 0.005
e2b 4-bit+ctx36k three_field: failures ending in quote 21/50, other 87/110, Fisher p = 0.000
e2b-bf16 edit_file: failures ending in quote 0/50, other 12/110, Fisher p = 0.019
e2b-bf16 one_field: failures ending in quote 50/50, other 94/110, Fisher p = 0.003
e2b-bf16 three_field: failures ending in quote 8/50, other 42/110, Fisher p = 0.006
e2b-bf16+ctx36k edit_file: failures ending in quote 0/50, other 2/110, Fisher p = 1.000
e2b-bf16+ctx36k one_field: failures ending in quote 50/50, other 79/110, Fisher p = 0.000
e2b-bf16+ctx36k three_field: failures ending in quote 6/50, other 71/110, Fisher p = 0.000
e4b 4-bit edit_file: failures ending in quote 0/50, other 2/110, Fisher p = 1.000
e4b 4-bit one_field: failures ending in quote 0/50, other 2/110, Fisher p = 1.000
e4b 4-bit three_field: failures ending in quote 0/50, other 8/110, Fisher p = 0.058
e4b 4-bit+ctx36k edit_file: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
e4b 4-bit+ctx36k one_field: failures ending in quote 0/50, other 3/110, Fisher p = 0.553
e4b 4-bit+ctx36k three_field: failures ending in quote 2/50, other 19/110, Fisher p = 0.023
e4b-bf16 edit_file: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
e4b-bf16 one_field: failures ending in quote 0/50, other 2/110, Fisher p = 1.000
e4b-bf16 three_field: failures ending in quote 0/50, other 9/110, Fisher p = 0.058
e4b-bf16+ctx36k edit_file: failures ending in quote 0/50, other 0/110, Fisher p = 1.000
e4b-bf16+ctx36k one_field: failures ending in quote 0/50, other 2/110, Fisher p = 1.000
e4b-bf16+ctx36k three_field: failures ending in quote 0/50, other 6/110, Fisher p = 0.178
qwen3-1.7b-bf16 edit_file: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-1.7b-bf16 one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-1.7b-bf16 three_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-1.7b-bf16+ctx36k edit_file: failures ending in quote 49/50, other 105/110, Fisher p = 0.666
qwen3-1.7b-bf16+ctx36k one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-1.7b-bf16+ctx36k three_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-4b AWQ 4-bit edit_file: failures ending in quote 37/50, other 69/110, Fisher p = 0.207
qwen3-4b AWQ 4-bit one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-4b AWQ 4-bit three_field: failures ending in quote 37/50, other 85/110, Fisher p = 0.691
qwen3-4b AWQ 4-bit+ctx36k edit_file: failures ending in quote 33/50, other 70/110, Fisher p = 0.859
qwen3-4b AWQ 4-bit+ctx36k one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-4b AWQ 4-bit+ctx36k three_field: failures ending in quote 36/50, other 82/110, Fisher p = 0.846
qwen3-4b-bf16 edit_file: failures ending in quote 40/50, other 75/110, Fisher p = 0.134
qwen3-4b-bf16 one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-4b-bf16 three_field: failures ending in quote 36/50, other 74/110, Fisher p = 0.586
qwen3-4b-bf16+ctx36k edit_file: failures ending in quote 34/50, other 65/110, Fisher p = 0.298
qwen3-4b-bf16+ctx36k one_field: failures ending in quote 50/50, other 110/110, Fisher p = 1.000
qwen3-4b-bf16+ctx36k three_field: failures ending in quote 37/50, other 73/110, Fisher p = 0.363

edit_file: e4b-bf16 0/160 vs e4b 4-bit 2/160 failures, Fisher p = 0.498
edit_file: e2b-bf16 12/160 vs e2b 4-bit 38/160 failures, Fisher p = 0.000
edit_file: qwen3-4b-bf16 115/160 vs qwen3-4b AWQ 4-bit 106/160 failures, Fisher p = 0.333
edit_file: 31B (API; asked for e4b) 0/160 vs e4b 4-bit 2/160 failures, Fisher p = 0.498
edit_file+ctx36k: e4b-bf16+ctx36k 0/160 vs e4b 4-bit+ctx36k 0/160 failures, Fisher p = 1.000
edit_file+ctx36k: e2b-bf16+ctx36k 2/160 vs e2b 4-bit+ctx36k 36/160 failures, Fisher p = 0.000
edit_file+ctx36k: qwen3-4b-bf16+ctx36k 99/160 vs qwen3-4b AWQ 4-bit+ctx36k 103/160 failures, Fisher p = 0.728
edit_file+ctx36k: 31B (API; asked for e4b)+ctx36k 0/160 vs e4b 4-bit+ctx36k 0/160 failures, Fisher p = 1.000
edit_file: context effect modal/e2b: 38/160 -> 36/160, Fisher p = 0.895
edit_file: context effect modal/e2b-bf16: 12/160 -> 2/160, Fisher p = 0.011
edit_file: context effect modal/e4b: 2/160 -> 0/160, Fisher p = 0.498
edit_file: context effect modal/e4b-bf16: 0/160 -> 0/160, Fisher p = 1.000
edit_file: context effect modal/qwen3-1.7b-bf16: 160/160 -> 154/160, Fisher p = 0.030
edit_file: context effect modal/qwen3-4b-awq: 106/160 -> 103/160, Fisher p = 0.814
edit_file: context effect modal/qwen3-4b-bf16: 115/160 -> 99/160, Fisher p = 0.075
one_field: e4b-bf16 2/160 vs e4b 4-bit 2/160 failures, Fisher p = 1.000
one_field: e2b-bf16 144/160 vs e2b 4-bit 149/160 failures, Fisher p = 0.422
one_field: qwen3-4b-bf16 160/160 vs qwen3-4b AWQ 4-bit 160/160 failures, Fisher p = 1.000
one_field: 31B (API; asked for e4b) 0/160 vs e4b 4-bit 2/160 failures, Fisher p = 0.498
one_field+ctx36k: e4b-bf16+ctx36k 2/160 vs e4b 4-bit+ctx36k 3/160 failures, Fisher p = 1.000
one_field+ctx36k: e2b-bf16+ctx36k 129/160 vs e2b 4-bit+ctx36k 146/160 failures, Fisher p = 0.009
one_field+ctx36k: qwen3-4b-bf16+ctx36k 160/160 vs qwen3-4b AWQ 4-bit+ctx36k 160/160 failures, Fisher p = 1.000
one_field+ctx36k: 31B (API; asked for e4b)+ctx36k 0/160 vs e4b 4-bit+ctx36k 3/160 failures, Fisher p = 0.248
one_field: context effect modal/e2b: 149/160 -> 146/160, Fisher p = 0.678
one_field: context effect modal/e2b-bf16: 144/160 -> 129/160, Fisher p = 0.026
one_field: context effect modal/e4b: 2/160 -> 3/160, Fisher p = 1.000
one_field: context effect modal/e4b-bf16: 2/160 -> 2/160, Fisher p = 1.000
one_field: context effect modal/qwen3-1.7b-bf16: 160/160 -> 160/160, Fisher p = 1.000
one_field: context effect modal/qwen3-4b-awq: 160/160 -> 160/160, Fisher p = 1.000
one_field: context effect modal/qwen3-4b-bf16: 160/160 -> 160/160, Fisher p = 1.000
three_field: e4b-bf16 9/160 vs e4b 4-bit 8/160 failures, Fisher p = 1.000
three_field: e2b-bf16 50/160 vs e2b 4-bit 89/160 failures, Fisher p = 0.000
three_field: qwen3-4b-bf16 110/160 vs qwen3-4b AWQ 4-bit 122/160 failures, Fisher p = 0.168
three_field: 31B (API; asked for e4b) 0/160 vs e4b 4-bit 8/160 failures, Fisher p = 0.007
three_field+ctx36k: e4b-bf16+ctx36k 6/160 vs e4b 4-bit+ctx36k 21/160 failures, Fisher p = 0.004
three_field+ctx36k: e2b-bf16+ctx36k 77/160 vs e2b 4-bit+ctx36k 108/160 failures, Fisher p = 0.001
three_field+ctx36k: qwen3-4b-bf16+ctx36k 110/160 vs qwen3-4b AWQ 4-bit+ctx36k 118/160 failures, Fisher p = 0.387
three_field+ctx36k: 31B (API; asked for e4b)+ctx36k 6/160 vs e4b 4-bit+ctx36k 21/160 failures, Fisher p = 0.004
three_field: context effect modal/e2b: 89/160 -> 108/160, Fisher p = 0.038
three_field: context effect modal/e2b-bf16: 50/160 -> 77/160, Fisher p = 0.003
three_field: context effect modal/e4b: 8/160 -> 21/160, Fisher p = 0.018
three_field: context effect modal/e4b-bf16: 9/160 -> 6/160, Fisher p = 0.598
three_field: context effect modal/qwen3-1.7b-bf16: 160/160 -> 160/160, Fisher p = 1.000
three_field: context effect modal/qwen3-4b-awq: 122/160 -> 118/160, Fisher p = 0.699
three_field: context effect modal/qwen3-4b-bf16: 110/160 -> 110/160, Fisher p = 1.000
e4b vs e4b-bf16, blocks (short): 4-bit 3/80 vs bf16 4/80 blocks with lost fields; discordant 2 vs 3, McNemar p = 1.000
e4b vs e4b-bf16, blocks+ctx36k: 4-bit 12/80 vs bf16 4/80 blocks with lost fields; discordant 10 vs 2, McNemar p = 0.039
e2b vs e2b-bf16, blocks (short): 4-bit 45/80 vs bf16 21/80 blocks with lost fields; discordant 25 vs 1, McNemar p = 0.000
e2b vs e2b-bf16, blocks+ctx36k: 4-bit 55/80 vs bf16 36/80 blocks with lost fields; discordant 22 vs 3, McNemar p = 0.000
qwen3-4b-awq vs qwen3-4b-bf16, blocks (short): 4-bit 1/80 vs bf16 0/80 blocks with lost fields; discordant 1 vs 0, McNemar p = 1.000
qwen3-4b-awq vs qwen3-4b-bf16, blocks+ctx36k: 4-bit 0/80 vs bf16 0/80 blocks with lost fields; discordant 0 vs 0, McNemar p = 1.000

Lost fields (called but required fields missing), nested / flat / one field, per model and context:
  e2b 4-bit                          87/160  35/160  149/160
  e2b 4-bit+ctx36k                   104/160  27/160  146/160
  e2b-bf16                           41/160  10/160  142/160
  e2b-bf16+ctx36k                    68/160  0/160  127/160
  31B (API; asked for e4b)           0/160  0/160  0/160
  e4b 4-bit                          4/160  0/160  0/160
  31B (API; asked for e4b)+ctx36k    6/160  0/160  0/160
  e4b 4-bit+ctx36k                   21/160  0/160  1/160
  e4b-bf16                           7/160  0/160  0/160
  e4b-bf16+ctx36k                    6/160  0/160  0/160
  qwen3-1.7b-bf16                    2/160  3/160  0/160
  qwen3-1.7b-bf16+ctx36k             10/160  21/160  13/160
  qwen3-4b AWQ 4-bit                 2/160  21/160  4/160
  qwen3-4b AWQ 4-bit+ctx36k          0/160  4/160  15/160
  qwen3-4b-bf16                      0/160  28/160  0/160
  qwen3-4b-bf16+ctx36k               0/160  11/160  1/160

Re-scored: calls with a LOST field (layout errors in brackets), nested / flat / one field:
  e2b 4-bit                          87/160 (0)  35/160 (0)  0/160 (149)
  e2b 4-bit+ctx36k                   104/160 (0)  27/160 (0)  2/160 (144)
  e2b-bf16                           41/160 (0)  10/160 (0)  0/160 (142)
  e2b-bf16+ctx36k                    68/160 (0)  0/160 (0)  0/160 (127)
  31B (API; asked for e4b)           0/160 (0)  0/160 (0)  0/160 (0)
  e4b 4-bit                          4/160 (0)  0/160 (0)  0/160 (0)
  31B (API; asked for e4b)+ctx36k    6/160 (0)  0/160 (0)  0/160 (0)
  e4b 4-bit+ctx36k                   21/160 (0)  0/160 (0)  0/160 (1)
  e4b-bf16                           7/160 (0)  0/160 (0)  0/160 (0)
  e4b-bf16+ctx36k                    6/160 (0)  0/160 (0)  0/160 (0)
  qwen3-1.7b-bf16                    2/160 (0)  3/160 (0)  0/160 (0)
  qwen3-1.7b-bf16+ctx36k             10/160 (0)  21/160 (0)  0/160 (13)
  qwen3-4b AWQ 4-bit                 2/160 (0)  21/160 (0)  0/160 (4)
  qwen3-4b AWQ 4-bit+ctx36k          0/160 (0)  4/160 (0)  0/160 (15)
  qwen3-4b-bf16                      0/160 (0)  28/160 (0)  0/160 (0)
  qwen3-4b-bf16+ctx36k               0/160 (0)  11/160 (0)  0/160 (1)

Structural failures (not executed + lost field), nested / flat / one field, per model and context:
  e2b 4-bit                          87/160 (0 not run)  35/160 (0 not run)  0/160 (0 not run)
  e2b 4-bit+ctx36k                   105/160 (1 not run)  27/160 (0 not run)  2/160 (0 not run)
  e2b-bf16                           41/160 (0 not run)  10/160 (0 not run)  0/160 (0 not run)
  e2b-bf16+ctx36k                    68/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  31B (API; asked for e4b)           0/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  e4b 4-bit                          4/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  31B (API; asked for e4b)+ctx36k    6/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  e4b 4-bit+ctx36k                   21/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  e4b-bf16                           7/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  e4b-bf16+ctx36k                    6/160 (0 not run)  0/160 (0 not run)  0/160 (0 not run)
  qwen3-1.7b-bf16                    9/160 (7 not run)  30/160 (27 not run)  1/160 (1 not run)
  qwen3-1.7b-bf16+ctx36k             113/160 (103 not run)  74/160 (53 not run)  15/160 (15 not run)
  qwen3-4b AWQ 4-bit                 116/160 (114 not run)  92/160 (71 not run)  2/160 (2 not run)
  qwen3-4b AWQ 4-bit+ctx36k          100/160 (100 not run)  79/160 (75 not run)  8/160 (8 not run)
  qwen3-4b-bf16                      103/160 (103 not run)  99/160 (71 not run)  0/160 (0 not run)
  qwen3-4b-bf16+ctx36k               101/160 (101 not run)  84/160 (73 not run)  0/160 (0 not run)

One field vs multi-field, block-level McNemar per model (short and long context pooled; e4b, e2b = 4-bit; Modal only):
  e2b              vs three_field: one field worse in 0, better in 99 blocks (p = 3.2e-30); vs edit_file: one field worse in 0, better in 33 blocks (p = 2.3e-10)
  e2b-bf16         vs three_field: one field worse in 0, better in 57 blocks (p = 1.4e-17); vs edit_file: one field worse in 0, better in 5 blocks (p = 0.062)
  e4b              vs three_field: one field worse in 0, better in 15 blocks (p = 6.1e-05); vs edit_file: one field worse in 0, better in 0 blocks (p = 1)
  e4b-bf16         vs three_field: one field worse in 0, better in 8 blocks (p = 0.0078); vs edit_file: one field worse in 0, better in 0 blocks (p = 1)
  qwen3-1.7b-bf16  vs three_field: one field worse in 3, better in 56 blocks (p = 1.2e-13); vs edit_file: one field worse in 5, better in 51 blocks (p = 1.2e-10)
  qwen3-4b-awq     vs three_field: one field worse in 1, better in 107 blocks (p = 6.7e-31); vs edit_file: one field worse in 1, better in 84 blocks (p = 4.4e-24)
  qwen3-4b-bf16    vs three_field: one field worse in 0, better in 107 blocks (p = 1.2e-32); vs edit_file: one field worse in 0, better in 96 blocks (p = 2.5e-29)

4-bit vs original weights, structural failures of the nested call, block-level McNemar:
  e4b vs e4b-bf16 (short): blocks failing 3 vs 4 of 80; discordant 2 vs 3, p = 1
  e4b vs e4b-bf16+ctx36k: blocks failing 12 vs 4 of 80; discordant 10 vs 2, p = 0.0386
  e2b vs e2b-bf16 (short): blocks failing 45 vs 21 of 80; discordant 25 vs 1, p = 8.05e-07
  e2b vs e2b-bf16+ctx36k: blocks failing 55 vs 36 of 80; discordant 22 vs 3, p = 0.000157
  qwen3-4b-awq vs qwen3-4b-bf16 (short): blocks failing 59 vs 54 of 80; discordant 11 vs 6, p = 0.332
  qwen3-4b-awq vs qwen3-4b-bf16+ctx36k: blocks failing 52 vs 53 of 80; discordant 7 vs 8, p = 1
