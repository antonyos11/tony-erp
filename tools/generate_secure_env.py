#!/usr/bin/env python3
"""
مولّد ملف .env آمن للإنتاج
Secure .env Generator for Production
الاستخدام:
  python tools/generate_secure_env.py            ← توليد ملف جديد
  python tools/generate_secure_env.py audit .env ← فحص ملف موجود
"""
import secrets
import string
import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

WEAK_PASSWORDS = {
    'admin123', 'password', '123456', 'admin', 'root', 'changeme',
    'strong_password', 'CHANGE_ME', 'secret', 'postgres', 'django',
    'tony_erp', 'test123', 'qwerty', '12345678', 'password123',
    'admin1234', 'letmein', '', 'test',
}


def generate_password(length=32):
    alpha = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        p = ''.join(secrets.choice(alpha) for _ in range(length))
        if (any(c.islower() for c in p) and any(c.isupper() for c in p)
                and any(c.isdigit() for c in p)
                and any(c in "!@#$%^&*()-_=+" for c in p)):
            return p


def generate_secret_key(length=50):
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_production_env(output_path=None):
    if output_path is None:
        output_path = BASE_DIR / '.env.production.secure'

    sk   = generate_secret_key(50)
    pgpw = generate_password(32)
    rdpw = generate_password(24)
    adpw = generate_password(20)
    bkpw = generate_password(32)

    content = f"""# ╔══════════════════════════════════════════════════════════════╗
# ║  Tony ERP - Production Environment (auto-generated)         ║
# ║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                          ║
# ║  ⚠️  لا تشارك هذا الملف ولا ترفعه على Git                  ║
# ╚══════════════════════════════════════════════════════════════╝

DJANGO_ENV=production
DEBUG=False
SECRET_KEY={sk}

# ⚠️ غيّر لنطاقك الحقيقي
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

DB_ENGINE=postgresql
POSTGRES_DB=tony_erp_production
POSTGRES_USER=tony_erp_user
POSTGRES_PASSWORD={pgpw}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DB_CONN_MAX_AGE=600

REDIS_URL=redis://:{rdpw}@localhost:6379/0
REDIS_PASSWORD={rdpw}
CELERY_BROKER_URL=redis://:{rdpw}@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:{rdpw}@localhost:6379/2

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
DJANGO_SUPERUSER_PASSWORD={adpw}

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=REPLACE_WITH_REAL_EMAIL_PASSWORD
DEFAULT_FROM_EMAIL=Tony ERP <noreply@yourdomain.com>

SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_AGE=3600
SESSION_EXPIRE_AT_BROWSER_CLOSE=True

LOG_LEVEL=WARNING
LOG_FILE=/var/log/tony_erp/app.log

BACKUP_DIR=/var/backups/tony_erp
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY={bkpw}
"""
    with open(output_path, 'w') as f:
        f.write(content)
    try:
        os.chmod(output_path, 0o600)
    except Exception:
        pass

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ✅ تم توليد ملف البيئة الآمن                               ║
║  📄 {str(output_path):<55}║
║                                                              ║
║  كلمات المرور المولّدة (الأولى 8 أحرف فقط):                  ║
║  PostgreSQL : {pgpw[:8]}...                                  ║
║  Redis      : {rdpw[:8]}...                                  ║
║  SuperAdmin : {adpw[:8]}...                                  ║
║                                                              ║
║  الخطوات التالية:                                            ║
║  1. غيّر ALLOWED_HOSTS لنطاقك                               ║
║  2. غيّر EMAIL_HOST_PASSWORD                                 ║
║  3. cp .env.production.secure .env                           ║
╚══════════════════════════════════════════════════════════════╝
""")
    return output_path


def audit_env(env_path=None):
    if env_path is None:
        env_path = BASE_DIR / '.env'

    if not Path(env_path).exists():
        print(f"❌ الملف غير موجود: {env_path}")
        return False

    issues, warns = [], []

    with open(env_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, val = line.partition('=')
            key, val = key.strip(), val.strip().strip('"\'')

            if key == 'DEBUG' and val.lower() in ('true', '1', 'yes'):
                issues.append(f"L{lineno}: DEBUG=True في الإنتاج!")
            if key == 'ALLOWED_HOSTS' and '*' in val:
                issues.append(f"L{lineno}: ALLOWED_HOSTS=* خطير!")
            if key == 'DB_ENGINE' and val == 'sqlite':
                issues.append(f"L{lineno}: DB_ENGINE=sqlite في الإنتاج!")
            if key in ('POSTGRES_PASSWORD', 'SECRET_KEY', 'REDIS_PASSWORD',
                       'DJANGO_SUPERUSER_PASSWORD'):
                if val.lower() in WEAK_PASSWORDS:
                    issues.append(f"L{lineno}: {key} ← ضعيفة أو فارغة!")
                elif len(val) < 12:
                    warns.append(f"L{lineno}: {key} قصيرة ({len(val)} حرف)")

    print("\n" + "=" * 55)
    print(f"  🔍 فحص أمني: {env_path}")
    print("=" * 55)
    if issues:
        print(f"\n  🔴 مشاكل حرجة ({len(issues)}):")
        for i in issues:
            print(f"     ❌ {i}")
    if warns:
        print(f"\n  🟡 تحذيرات ({len(warns)}):")
        for w in warns:
            print(f"     ⚠️  {w}")
    if not issues and not warns:
        print("\n  ✅ لا مشاكل أمنية!")
    print("=" * 55 + "\n")
    return len(issues) == 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'audit':
        audit_env(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        generate_production_env()
