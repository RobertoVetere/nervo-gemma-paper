"""INSTALL: copy the repomap script into <repo>/.fixer/ (ignored by git, never in the patch).

After this, every script runs with the tool run_command, for example:
  python3 .fixer/map.py "words from the issue"
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import go_to_repo  # noqa: E402

# ADK runs this file as a relative path ('scripts/install.py') from a temp folder: resolve it BEFORE
# go_to_repo() changes the working directory.
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    repo = go_to_repo()
    if not repo:
        print('ERROR: repository not found')
        return
    dest = os.path.join(repo, '.fixer')
    os.makedirs(dest, exist_ok=True)
    copied = []
    for f in os.listdir(HERE):
        if f.endswith('.py') and f != 'install.py':
            shutil.copy(os.path.join(HERE, f), os.path.join(dest, f))
            copied.append(f)
    if 'map.py' not in copied:
        print(f'ERROR: scripts not found next to install.py ({HERE}); copied: {copied}')
        return
    info = os.path.join(repo, '.git', 'info')
    os.makedirs(info, exist_ok=True)
    exclude = os.path.join(info, 'exclude')
    old = open(exclude).read() if os.path.exists(exclude) else ''
    if '.fixer/' not in old.split():
        with open(exclude, 'a') as fh:
            fh.write(('' if old.endswith('\n') or not old else '\n') + '.fixer/\n')
    print(f'OK: {len(copied)} scripts installed in .fixer/ (git ignores this folder).')
    print('NEXT: run_command python3 .fixer/map.py "<exact names and key words from the issue>"')


if __name__ == '__main__':
    main()
