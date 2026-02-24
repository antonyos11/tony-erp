#!/usr/bin/env python3
"""
المراجعة الأمنية الشاملة - Tony ERP
Comprehensive Security Audit Tool
الاستخدام: python tools/security_audit.py
"""
import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env',
                'migrations', '.pytest_cache', 'staticfiles', 'media', 'logs',
                'testsprite_tests', 'docs', 'backup'}

WEAK_PASSWORDS = {
    'admin123', 'password', 'changeme', 'secret', 'admin', '123456', 'test',
    'strong_password', 'CHANGE_ME', 'postgres', 'django', 'root', 'qwerty',
}


def get_files(ext):
    for f in BASE_DIR.rglob(f'*.{ext}'):
        if not any(ex in f.parts for ex in EXCLUDE_DIRS):
            yield f


def scan():
    findings = {'critical': [], 'high': [], 'medium': [], 'low': []}
    scanned = 0

    print("🔍 بدء المراجعة الأمنية...\n")

    # 1. فحص .env
    print("  [1/6] فحص ملف .env...")
    env_file = BASE_DIR / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                key, val = key.strip(), val.strip().strip('"\'')
                if key == 'DEBUG' and val.lower() in ('true', '1'):
                    findings['high'].append(('env', str(env_file.relative_to(BASE_DIR)), lineno, 'DEBUG=True'))
                if key == 'ALLOWED_HOSTS' and '*' in val:
                    findings['high'].append(('env', str(env_file.relative_to(BASE_DIR)), lineno, 'ALLOWED_HOSTS=* خطير!'))
                if key in ('POSTGRES_PASSWORD', 'SECRET_KEY') and val.lower() in WEAK_PASSWORDS:
                    findings['critical'].append(('weak_password', str(env_file.relative_to(BASE_DIR)), lineno, f'{key} ضعيفة!'))
    else:
        findings['critical'].append(('missing_env', '.env', 0, 'ملف .env غير موجود!'))

    # 2. فحص .gitignore
    print("  [2/6] فحص .gitignore...")
    gitignore = BASE_DIR / '.gitignore'
    if gitignore.exists():
        content = gitignore.read_text(errors='ignore')
        if '.env' not in content:
            findings['critical'].append(('.gitignore', '.gitignore', 0, '.env غير مستبعد من Git!'))
        if 'db.sqlite3' not in content:
            findings['medium'].append(('.gitignore', '.gitignore', 0, 'db.sqlite3 غير مستبعد من Git'))
    else:
        findings['high'].append(('missing_gitignore', '', 0, '.gitignore غير موجود!'))

    # 3. فحص إعدادات مكتوبة في الكود
    print("  [3/6] فحص أسرار مكتوبة في الكود...")
    secret_patterns = [
        (r'password\s*=\s*["\'][a-zA-Z0-9!@#$%]{6,}["\']', 'كلمة مرور في الكود'),
        (r'secret_key\s*=\s*["\'][^"\']{10,}["\']', 'مفتاح سري في الكود'),
        (r'api_key\s*=\s*["\'][^"\']{10,}["\']', 'مفتاح API في الكود'),
    ]
    for py_file in get_files('py'):
        scanned += 1
        try:
            text = py_file.read_text(encoding='utf-8', errors='ignore')
            for pat, desc in secret_patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    ln = text[:m.start()].count('\n') + 1
                    line = text.split('\n')[ln - 1].strip()
                    if line.startswith('#') or 'test' in py_file.name.lower():
                        continue
                    findings['high'].append(('hardcoded', str(py_file.relative_to(BASE_DIR)), ln, desc))
        except Exception:
            pass

    # 4. فحص SQL Injection
    print("  [4/6] فحص SQL Injection...")
    sql_patterns = [
        (r'\.raw\s*\([^)]*%[^)]*%', 'raw() مع format string'),
        (r'f["\'].*SELECT.*FROM.*\{', 'f-string في SQL'),
        (r'cursor\.execute\s*\(\s*["\'].*\+', 'تسلسل نصوص في execute()'),
    ]
    for py_file in get_files('py'):
        try:
            text = py_file.read_text(encoding='utf-8', errors='ignore')
            for pat, desc in sql_patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    ln = text[:m.start()].count('\n') + 1
                    line = text.split('\n')[ln - 1].strip()
                    if not line.startswith('#'):
                        findings['critical'].append(('sql_injection', str(py_file.relative_to(BASE_DIR)), ln, desc))
        except Exception:
            pass

    # 5. فحص CSRF في القوالب
    print("  [5/6] فحص CSRF في القوالب...")
    for html_file in get_files('html'):
        try:
            text = html_file.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'method=["\']post["\']', text, re.IGNORECASE):
                if 'csrf_token' not in text and 'csrfmiddlewaretoken' not in text:
                    findings['high'].append(('csrf', str(html_file.relative_to(BASE_DIR)), 0, 'نموذج POST بدون csrf_token'))
        except Exception:
            pass

    # 6. فحص دوال خطيرة
    print("  [6/6] فحص دوال خطيرة...")
    dangerous = [
        (r'\beval\s*\(', 'eval()'),
        (r'pickle\.loads?\s*\(', 'pickle.load() - يسمح بتنفيذ كود'),
        (r'subprocess\.[^(]*shell\s*=\s*True', 'subprocess shell=True'),
    ]
    for py_file in get_files('py'):
        try:
            text = py_file.read_text(encoding='utf-8', errors='ignore')
            for pat, desc in dangerous:
                for m in re.finditer(pat, text):
                    ln = text[:m.start()].count('\n') + 1
                    line = text.split('\n')[ln - 1].strip()
                    if not line.startswith('#'):
                        findings['medium'].append(('dangerous_func', str(py_file.relative_to(BASE_DIR)), ln, desc))
        except Exception:
            pass

    # === التقرير ===
    total = sum(len(v) for v in findings.values())
    icons = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}

    print(f"\n{'═'*60}")
    print(f"  📋 تقرير الأمان - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📂 ملفات مفحوصة: {scanned} | إجمالي النتائج: {total}")
    print(f"{'═'*60}")

    for sev, items in findings.items():
        if items:
            print(f"\n  {icons[sev]} {sev.upper()} ({len(items)})")
            for (_, fname, ln, desc) in items[:8]:
                loc = f":{ln}" if ln else ""
                print(f"     • {fname}{loc} → {desc}")
            if len(items) > 8:
                print(f"     ... و {len(items)-8} أخرى")

    print(f"\n{'═'*60}")
    if findings['critical']:
        print("  ❌ مشاكل حرجة يجب إصلاحها فوراً!")
        verdict = "غير آمن"
    elif findings['high']:
        print("  ⚠️  مشاكل مهمة يجب مراجعتها")
        verdict = "يحتاج مراجعة"
    else:
        print("  ✅ لا مشاكل حرجة أو عالية الخطورة!")
        verdict = "آمن"
    print(f"{'═'*60}\n")

    # حفظ التقرير
    report = BASE_DIR / 'security_audit_report.json'
    with open(report, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'verdict': verdict,
            'files_scanned': scanned,
            'summary': {k: len(v) for k, v in findings.items()},
            'findings': {k: [{'file': r[1], 'line': r[2], 'desc': r[3]} for r in v]
                         for k, v in findings.items() if v},
        }, f, ensure_ascii=False, indent=2)
    print(f"  📄 التقرير: {report}\n")
    return findings


if __name__ == '__main__':
    scan()
