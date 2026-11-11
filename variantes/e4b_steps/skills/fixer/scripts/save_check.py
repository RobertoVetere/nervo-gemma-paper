"""SAVE_CHECK: save the cases script as /tmp/check.py (verify.py runs it).

args: {"code": "<the full Python script>"}
"""
import argparse
import os
import py_compile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', required=True)
    a = ap.parse_args()
    folder = os.environ.get('TMPDIR') or '/tmp'
    path = os.path.join(folder, 'check.py')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(a.code)
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as e:
        print(f'ERROR: the script does not compile; fix it and save it again:\n{str(e)[-600:]}')
        return
    print(f'OK: saved {path} ({len(a.code.splitlines())} lines). scripts/verify.py will run it after your fix.')


if __name__ == '__main__':
    main()
