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

edit_file: deepinfra 0/160 vs modal 2/160 failures, Fisher p = 0.498
one_field: deepinfra 0/160 vs modal 2/160 failures, Fisher p = 0.498
three_field: deepinfra 0/160 vs modal 8/160 failures, Fisher p = 0.007
edit_file: deepinfra 0/160 vs modal 0/160 failures, Fisher p = 1.000
one_field: deepinfra 0/160 vs modal 3/160 failures, Fisher p = 0.248
three_field: deepinfra 6/160 vs modal 21/160 failures, Fisher p = 0.004
