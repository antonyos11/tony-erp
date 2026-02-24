#!/usr/bin/env python3
"""
فاحص جاهزية الإنتاج الشامل - Tony ERP
Production Readiness Checker
الاستخدام: python tools/production_readiness_checklist.py
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV = BASE_DIR / '.env'


def load_env():
    """تحميل أزواج key=value من ملف .env"""
    env = {}
    if DOTENV.exists():
        for line in DOTENV.read_text(errors='ignore').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip().strip('"\'')
    return env


def run():
    env = load_env()
    results = {}

    checks = [
        ("قاعدة البيانات PostgreSQL",   _chk_db),
        ("كلمات المرور الآمنة",          _chk_passwords),
        ("DEBUG=False",                  _chk_debug),
        ("ALLOWED_HOSTS آمن",             _chk_hosts),
        ("SSL / HTTPS",                  _chk_ssl),
        ("Django system check",          _chk_django),
        ("الهجرات مطبّقة",              _chk_migrations),
        ("الملفات الثابتة مجمّعة",       _chk_static),
        ("ملف .gitignore",               _chk_gitignore),
        ("الاختبارات (≥80 نجاح)",        _chk_tests),
        ("النسخ الاحتياطي",              _chk_backup),
        ("السجلات (Logging)",            _chk_logging),
    ]

    print("\n" + "═" * 65)
    print("  🏭 فحص جاهزية الإنتاج - Tony ERP")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 65)

    passed = failed = warned = 0

    for name, fn in checks:
        try:
            status, msg = fn(env)
        except Exception as e:
            status, msg = 'fail', str(e)

        results[name] = {'status': status, 'msg': msg}
        icon = {'pass': '✅', 'warn': '⚠️ ', 'fail': '❌'}[status]
        print(f"\n  {icon} {name}")
        if msg:
            print(f"      {msg}")
        if status == 'pass':
            passed += 1
        elif status == 'warn':
            warned += 1
        else:
            failed += 1

    total = passed + failed + warned
    score = round(passed / total * 100) if total else 0

    print(f"\n{'═'*65}")
    print(f"  📊 النتيجة: {passed}/{total} ✅  |  {warned} ⚠️  |  {failed} ❌")
    print(f"  📈 النسبة: {score}%")

    if score >= 90:
        verdict = "🎉 جاهز للإنتاج!"
    elif score >= 70:
        verdict = "⚠️  قريب — أصلح المشاكل المتبقية"
    else:
        verdict = "❌ غير جاهز — يحتاج عمل إضافي"

    print(f"\n  {verdict}")
    print(f"{'═'*65}\n")

    report = BASE_DIR / 'production_readiness_report.json'
    with open(report, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': datetime.now().isoformat(),
                   'score': score, 'verdict': verdict,
                   'passed': passed, 'failed': failed, 'warned': warned,
                   'details': results}, f, ensure_ascii=False, indent=2)
    print(f"  📄 التقرير: {report}\n")
    return score >= 90


# ─── فحوصات فردية ───────────────────────────────────────────

def _chk_db(env):
    engine = env.get('DB_ENGINE', 'sqlite')
    if 'postgresql' in engine or 'postgres' in engine:
        host = env.get('POSTGRES_HOST', 'localhost')
        db   = env.get('POSTGRES_DB', '?')
        return 'pass', f"PostgreSQL @ {host}/{db}"
    return 'fail', 'DB_ENGINE=sqlite — غيّره إلى postgresql'


def _chk_passwords(env):
    weak = {'admin123', 'password', 'changeme', 'strong_password',
            'secret', '123456', '', 'postgres', 'django', 'test'}
    issues = []
    # يدعم كلا الاسمين
    secret_key = env.get('SECRET_KEY') or env.get('DJANGO_SECRET_KEY', '')
    if not secret_key:
        issues.append('SECRET_KEY / DJANGO_SECRET_KEY غير موجودة')
    elif secret_key.lower() in weak:
        issues.append('SECRET_KEY ضعيفة')
    elif len(secret_key) < 20:
        issues.append(f'SECRET_KEY قصيرة ({len(secret_key)})')
    pg_pass = env.get('POSTGRES_PASSWORD', '')
    if pg_pass.lower() in weak:
        issues.append('POSTGRES_PASSWORD ضعيفة')
    elif pg_pass and len(pg_pass) < 8:
        issues.append(f'POSTGRES_PASSWORD قصيرة ({len(pg_pass)})')
    if issues:
        return 'fail', ' | '.join(issues)
    return 'pass', 'كلمات المرور قوية ✓'


def _chk_debug(env):
    debug = env.get('DEBUG', 'True').lower()
    if debug in ('false', '0', 'no'):
        return 'pass', 'DEBUG=False ✓'
    django_env = env.get('DJANGO_ENV', env.get('ENVIRONMENT', 'development'))
    if django_env == 'production':
        return 'fail', 'DEBUG=True في بيئة production!'
    return 'warn', f'DEBUG=True (البيئة: {django_env})'


def _chk_hosts(env):
    hosts = env.get('ALLOWED_HOSTS', '')
    if '*' in hosts:
        return 'fail', 'ALLOWED_HOSTS=* خطير!'
    if not hosts:
        return 'warn', 'ALLOWED_HOSTS فارغ'
    return 'pass', f'{hosts[:50]}'


def _chk_ssl(env):
    ssl = env.get('SECURE_SSL_REDIRECT', env.get('SECURE_SSL_REDIRECT', ''))
    hsts = env.get('SECURE_HSTS_SECONDS', '0')
    if ssl in ('True', '1', 'true'):
        return 'pass', f'SSL ✓  |  HSTS={hsts}s'
    django_env = env.get('DJANGO_ENV', env.get('ENVIRONMENT', ''))
    if django_env == 'production':
        return 'warn', 'SECURE_SSL_REDIRECT غير مفعّل'
    return 'warn', 'SSL غير مفعّل (مقبول للتطوير)'


def _chk_django(env):
    try:
        result = subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy'],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        # عدّ الأخطاء الحرجة فقط (ليس تحذيرات drf_spectacular)
        errors = [l for l in output.splitlines()
                  if 'ERROR' in l and 'drf_spectacular' not in l]
        issues_count = output.count('issues') and int(
            next((w for w in output.split() if w.isdigit()), '0'))
        warns_only = all('drf_spectacular' in l or 'W00' in l
                         for l in output.splitlines()
                         if l.startswith('?:'))
        if errors:
            return 'fail', f'{len(errors)} أخطاء حرجة'
        if warns_only:
            return 'pass', f'تحذيرات API توثيق فقط (لا أخطاء حرجة) ✓'
        if 'issues' in output:
            return 'warn', f'تحذيرات مختلطة ({issues_count} مسألة)'
        return 'pass', 'لا أخطاء ✓'
    except Exception as e:
        return 'warn', str(e)


def _chk_migrations(env):
    try:
        result = subprocess.run(
            [sys.executable, 'manage.py', 'showmigrations', '--plan'],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=30
        )
        unapplied = [l for l in result.stdout.splitlines() if '[ ]' in l]
        if unapplied:
            return 'fail', f'{len(unapplied)} هجرة غير مطبّقة!'
        return 'pass', 'جميع الهجرات مطبّقة ✓'
    except Exception as e:
        return 'warn', str(e)


def _chk_static(env):
    static_dir = BASE_DIR / 'staticfiles'
    if static_dir.exists():
        count = sum(1 for _ in static_dir.rglob('*') if _.is_file())
        if count > 100:
            return 'pass', f'{count:,} ملف ثابت ✓'
        return 'warn', f'{count} ملف فقط — شغّل collectstatic'
    return 'warn', 'لا يوجد staticfiles/ — شغّل: python manage.py collectstatic'


def _chk_gitignore(env):
    gi = BASE_DIR / '.gitignore'
    if not gi.exists():
        return 'fail', '.gitignore غير موجود!'
    content = gi.read_text(errors='ignore')
    missing = [p for p in ('.env', 'db.sqlite3', '__pycache__') if p not in content]
    if missing:
        return 'warn', f'غير مستبعد: {", ".join(missing)}'
    return 'pass', 'يستبعد الملفات الحساسة ✓'


def _chk_tests(env):
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest',
             'tests/test_core_health.py',
             'tests/test_security.py',
             'tests/test_system_ready.py',
             '--override-ini=addopts=-q --tb=no -p no:warnings',
             '--maxfail=50'],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=180
        )
        output = result.stdout + result.stderr
        # استخراج أرقام النجاح والفشل
        import re
        m = re.search(r'(\d+) passed', output)
        f = re.search(r'(\d+) failed', output)
        passed = int(m.group(1)) if m else 0
        failed = int(f.group(1)) if f else 0
        total = passed + failed
        rate = round(passed / total * 100) if total else 0
        msg = f"{passed}/{total} نجح ({rate}%)"
        if rate >= 80:
            return 'pass', msg
        if rate >= 60:
            return 'warn', msg
        return 'fail', msg
    except Exception as e:
        return 'warn', str(e)


def _chk_backup(env):
    backup_dir = Path(env.get('BACKUP_DIR', str(BASE_DIR / 'backups')))
    tool = BASE_DIR / 'tools' / 'backup_and_restore.py'
    if not tool.exists():
        return 'warn', 'أداة النسخ غير موجودة'
    if backup_dir.exists():
        backups = sorted(backup_dir.glob('backup_*'), key=lambda x: x.stat().st_mtime)
        if backups:
            last = backups[-1]
            age_h = (datetime.now().timestamp() - last.stat().st_mtime) / 3600
            return 'pass', f'آخر نسخة: {last.name} (قبل {age_h:.0f} ساعة)'
        return 'warn', 'أداة موجودة لكن لا توجد نسخ بعد'
    return 'warn', 'مجلد النسخ غير موجود بعد'


def _chk_logging(env):
    log_file = env.get('LOG_FILE', '')
    log_level = env.get('LOG_LEVEL', '')
    if log_file and log_level:
        return 'pass', f'Level={log_level} | File={log_file}'
    if log_level:
        return 'warn', 'LOG_FILE غير محدد'
    return 'warn', 'اضف LOG_LEVEL وLOG_FILE في .env'


if __name__ == '__main__':
    success = run()
    sys.exit(0 if success else 1)
