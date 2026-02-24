import subprocess, sys, pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent


def test_system_self_check_runs():
    # Run quietly; expect non-zero exit code if issues found but should not raise Unicode errors
    proc = subprocess.run([sys.executable, 'manage.py', 'system_self_check', '--quiet'], cwd=BASE, capture_output=True, text=True, encoding='utf-8')
    assert 'UnicodeEncodeError' not in proc.stdout
    assert 'UnicodeEncodeError' not in proc.stderr
    # Accept either 0 or 1 exit codes (1 means issues but command executed correctly)
    assert proc.returncode in (0,1)
