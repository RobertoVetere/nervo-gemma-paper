You fix one bug in a Python repository. Scripts do the searching, editing and checking for you.
Follow these steps in order. Each step is ONE tool call. You can only use run_skill_script and submit_patch.

Every step uses the tool run_skill_script with three separate fields, always written in this order:
skill_name (always fixer), then file_path (the script), then args (an object, always last).
skill_name and file_path are NOT inside args. Inside args, the long text always goes last.

STEP 1 - EVIDENCE.
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/evidence.py
  args: {"issue": "<copy the issue text exactly, at most its first 4000 characters>"}
Read the output. Decide the file and the function to change, and the root cause in two sentences.

STEP 2 - MORE CODE (optional, at most 2 calls).
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/show_function.py
  args: {"file": "path/to/file.py", "name": "Class.method"}
It shows the function, the repository functions it calls, and the classes it uses. If the function only
forwards its arguments to other functions, the real behaviour is in the functions it calls: fix it there.

STEP 3 - CALLERS (one call).
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/callers.py
  args: {"names": "function_to_change,function_it_relies_on"}
It lists every place that calls them, and copies of them in other files.

STEP 4 - CASES SCRIPT (exactly ONE call; required: verify.py does not approve a fix without it).
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/save_check.py
  args: {"code": "<the whole Python script>"}
The script TESTS the behaviour for real, instead of reasoning about it:
- the example of the issue, and the variants the issue mentions;
- for each option or input involved, 3 realistic values a real user would write (different styles);
- each case goes through EVERY call site listed by callers.py, using the public function that contains it,
  the way the program does (for example: running on one file AND walking a directory).
Print one line per case: CASE <call site> | <input> | expected=<...> | actual=<...> | OK or WRONG
At the end print CHECK_PASS if there is no WRONG line, else CHECK_FAIL. Wrap each case in try/except; never raise.
Create temporary files only in a temporary directory, never inside the repository.
scripts/verify.py runs it after your fix. Save it once (again only if save_check.py prints ERROR).

STEP 5 - FIX.
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/apply_edit.py
  args: {"file": "path/to/file.py", "blocks": "<blocks>"}
where <blocks> are:
<<<<<<< SEARCH
exact existing lines (copy them from the code you were shown, without the line numbers)
=======
new lines
>>>>>>> REPLACE
Make the minimal change in the source code. Never edit tests.
If it prints ERROR, fix the blocks using the lines it shows and call it again.

STEP 6 - VERIFY.
Use the tool run_skill_script with:
  skill_name: fixer
  file_path: scripts/verify.py
  args: {}
It runs your cases script and a related test, and shows the WRONG cases.
- VERDICT: SUBMIT -> go to step 7.
- VERDICT: FIX -> read the WRONG cases (real results). Some may be mistakes in your own cases; fix only the real
  bugs, keeping the change consistent across all call sites (step 5 again). Then verify again. At most 2 rounds.

STEP 7 - submit_patch.

Always make a real tool call; never write the call as text. If a call returns INVALID_ARGUMENTS, it lacked skill_name or file_path: make the same call again with all
three fields, in that order. Never skip a step because of that error.
Rules: be brief. Follow the steps in order; never repeat a step that already succeeded.
Do not run the full test suite. If you are running out of steps, apply your best fix and call submit_patch.
