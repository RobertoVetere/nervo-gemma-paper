---
name: repomap
description: Map of the repository - the classes (with method signatures) and functions of the files most related to the issue, so you read the right code first.
---
Run scripts/install.py once with the tool run_skill_script (skill_name: repomap, file_path: scripts/install.py, args: {}).
It copies map.py into .fixer/ in the repository (ignored by git, never in the patch). Then use run_command:
- python3 .fixer/map.py "words and exact names from the issue": classes, method signatures and functions of the most related files.
- python3 .fixer/map.py --exists Class.method: checks that a symbol exists and shows the closest real names if it does not.
