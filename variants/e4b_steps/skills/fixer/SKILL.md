---
name: fixer
description: Scripts that do the hard work for a bug fix - find the code the issue talks about, show functions, apply edits safely and verify the patch.
---
Run each script with the tool run_skill_script, using three separate fields, in this order: skill_name: fixer, then file_path: scripts/<script>.py, then args: an object with the script arguments (always last).
Scripts:
- scripts/evidence.py  args {"issue": "<full issue text>"}: traceback functions, issue strings found in the source, candidate functions with their code.
- scripts/show_function.py  args {"file": "pkg/mod.py", "name": "Class.method"}: code of one function or class with line numbers.
- scripts/callers.py  args {"names": "func_a,func_b"}: every call site of those functions in the source, and copies with the same name.
- scripts/save_check.py  args {"code": "<python script>"}: saves the cases script as /tmp/check.py.
- scripts/apply_edit.py  args {"file": "pkg/mod.py", "blocks": "<SEARCH/REPLACE blocks>"}: applies the edit, tolerant to whitespace; shows the diff.
- scripts/verify.py  (no args): checks the patch, runs /tmp/check.py and shows its WRONG cases; prints VERDICT SUBMIT, FIX or NO_EDIT.
