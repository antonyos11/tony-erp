import os, sys
from pathlib import Path

try:
    from mypy import api as mypy_api
except Exception as e:  # pragma: no cover
    print(f"Could not import mypy API: {e}")
    sys.exit(1)

BASE = Path(__file__).parent
os.chdir(BASE)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
config_path = BASE / 'mypy.ini'
if not config_path.exists():
    print('mypy.ini not found next to run_mypy_utf8.py')
    sys.exit(2)

args = ['--config-file', str(config_path), '.']
stdout, stderr, exit_status = mypy_api.run(args)
report_path = BASE / 'mypy_report.txt'
error_lines = []
for line in stdout.splitlines():
    if ': error:' in line:
        error_lines.append(line)

with report_path.open('w', encoding='utf-8') as f:
    f.write(stdout)
    if stderr:
        f.write('\n[STDERR]\n')
        f.write(stderr)
    f.write(f"\nExit status: {exit_status}\n")
    f.write(f"Total errors: {len(error_lines)}\n")

print(f"Wrote mypy_report.txt with {len(error_lines)} errors (exit {exit_status})")
