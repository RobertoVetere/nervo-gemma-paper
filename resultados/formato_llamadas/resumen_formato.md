| Backend | Model | Interface | Calls | Not called | Fields lost / unparsable | Text not exact | Exact |
|---|---|---|---|---|---|---|---|
| deepinfra | e4b | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | e4b | one_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | e4b | three_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | e4b+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | e4b+ctx36k | one_field | 160 | 0 | 0 | 0 | 160 (100%) |
| deepinfra | e4b+ctx36k | three_field | 160 | 0 | 6 | 0 | 154 (96%) |
| modal | e4b | edit_file | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b | three_field | 160 | 0 | 4 | 4 | 152 (95%) |
| modal | e4b+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b+ctx36k | one_field | 160 | 0 | 1 | 2 | 157 (98%) |
| modal | e4b+ctx36k | three_field | 160 | 0 | 21 | 0 | 139 (87%) |
| modal | e4b-bf16 | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b-bf16 | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b-bf16 | three_field | 160 | 0 | 7 | 2 | 151 (94%) |
| modal | e4b-bf16+ctx36k | edit_file | 160 | 0 | 0 | 0 | 160 (100%) |
| modal | e4b-bf16+ctx36k | one_field | 160 | 0 | 0 | 2 | 158 (99%) |
| modal | e4b-bf16+ctx36k | three_field | 160 | 0 | 6 | 0 | 154 (96%) |

('deepinfra', 'e4b', 'edit_file'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('deepinfra', 'e4b', 'one_field'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('deepinfra', 'e4b', 'three_field'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('deepinfra', 'e4b+ctx36k', 'edit_file'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('deepinfra', 'e4b+ctx36k', 'one_field'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('deepinfra', 'e4b+ctx36k', 'three_field'): failures ending in quote 1/50, other 5/110, Fisher p = 0.666
('modal', 'e4b', 'edit_file'): failures ending in quote 0/50, other 2/110, Fisher p = 1.000
('modal', 'e4b', 'one_field'): failures ending in quote 0/50, other 2/110, Fisher p = 1.000
('modal', 'e4b', 'three_field'): failures ending in quote 0/50, other 8/110, Fisher p = 0.058
('modal', 'e4b+ctx36k', 'edit_file'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('modal', 'e4b+ctx36k', 'one_field'): failures ending in quote 0/50, other 3/110, Fisher p = 0.553
('modal', 'e4b+ctx36k', 'three_field'): failures ending in quote 2/50, other 19/110, Fisher p = 0.023
('modal', 'e4b-bf16', 'edit_file'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('modal', 'e4b-bf16', 'one_field'): failures ending in quote 0/50, other 2/110, Fisher p = 1.000
('modal', 'e4b-bf16', 'three_field'): failures ending in quote 0/50, other 9/110, Fisher p = 0.058
('modal', 'e4b-bf16+ctx36k', 'edit_file'): failures ending in quote 0/50, other 0/110, Fisher p = 1.000
('modal', 'e4b-bf16+ctx36k', 'one_field'): failures ending in quote 0/50, other 2/110, Fisher p = 1.000
('modal', 'e4b-bf16+ctx36k', 'three_field'): failures ending in quote 0/50, other 6/110, Fisher p = 0.178

edit_file: modal/e4b-bf16 0/160 vs modal/e4b 2/160 failures, Fisher p = 0.498
edit_file: deepinfra/e4b 0/160 vs modal/e4b 2/160 failures, Fisher p = 0.498
edit_file+ctx36k: modal/e4b-bf16+ctx36k 0/160 vs modal/e4b+ctx36k 0/160 failures, Fisher p = 1.000
edit_file+ctx36k: deepinfra/e4b+ctx36k 0/160 vs modal/e4b+ctx36k 0/160 failures, Fisher p = 1.000
edit_file: context effect modal/e4b: 2/160 -> 0/160, Fisher p = 0.498
edit_file: context effect modal/e4b-bf16: 0/160 -> 0/160, Fisher p = 1.000
one_field: modal/e4b-bf16 2/160 vs modal/e4b 2/160 failures, Fisher p = 1.000
one_field: deepinfra/e4b 0/160 vs modal/e4b 2/160 failures, Fisher p = 0.498
one_field+ctx36k: modal/e4b-bf16+ctx36k 2/160 vs modal/e4b+ctx36k 3/160 failures, Fisher p = 1.000
one_field+ctx36k: deepinfra/e4b+ctx36k 0/160 vs modal/e4b+ctx36k 3/160 failures, Fisher p = 0.248
one_field: context effect modal/e4b: 2/160 -> 3/160, Fisher p = 1.000
one_field: context effect modal/e4b-bf16: 2/160 -> 2/160, Fisher p = 1.000
three_field: modal/e4b-bf16 9/160 vs modal/e4b 8/160 failures, Fisher p = 1.000
three_field: deepinfra/e4b 0/160 vs modal/e4b 8/160 failures, Fisher p = 0.007
three_field+ctx36k: modal/e4b-bf16+ctx36k 6/160 vs modal/e4b+ctx36k 21/160 failures, Fisher p = 0.004
three_field+ctx36k: deepinfra/e4b+ctx36k 6/160 vs modal/e4b+ctx36k 21/160 failures, Fisher p = 0.004
three_field: context effect modal/e4b: 8/160 -> 21/160, Fisher p = 0.018
three_field: context effect modal/e4b-bf16: 9/160 -> 6/160, Fisher p = 0.598
