---
name: fixer
description: Scripts that do the hard work for a bug fix - find the code the issue talks about, show functions, apply edits safely and verify the patch.
---
Run scripts/install.py once with the tool run_skill_script (skill_name: fixer, file_path: scripts/install.py, args: {}).
It copies the scripts into .fixer/ in the repository (ignored by git). After that, run them with run_command:
- python3 .fixer/evidence.py  (reads .fixer/issue.txt): traceback functions, issue strings found in the source, candidate functions.
- python3 .fixer/show_function.py --file pkg/mod.py --name Class.method: code of one function with line numbers.
- python3 .fixer/apply_edit.py --file pkg/mod.py  (reads .fixer/edit.txt): applies SEARCH/REPLACE blocks, tolerant to whitespace, then verifies the patch and prints a VERDICT.
