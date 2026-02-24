#!/usr/bin/env python
"""
سكريبت تجهيز النظام للإنتاج - Tony ERP
Production Preparation Script

يفحص ويصلح المشاكل الشائعة قبل النشر.

الاستخدام:
    python tools/prepare_production.py --check     # فحص فقط
    python tools/prepare_production.py --fix       # فحص وإصلاح
"""
import os
import sys
import argparse
import secrets
import string

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProductionPreparer:
    """تجهيز النظام للإنتاج"""

    def __init__(self, fix=False):
        self.fix = fix
        self.issues = []
        self.fixed = []
        self.warnings = []

    def run(self):
        """تشغيل جميع الفحوصات"""
        print("\n" + "=" * 60)
        print("  Tony ERP - تجهيز الإنتاج")
        print("  Production Preparation")
        print("=" * 60 + "\n")

        checks = [
            ('ملف البيئة .env', self.check_env_file),
            ('SECRET_KEY', self.check_secret_key),
            ('وضع التصحيح DEBUG', self.check_debug_mode),
            ('قاعدة البيانات', self.check_database_config),
            ('ALLOWED_HOSTS', self.check_allowed_hosts),
            ('ملفات النسخ الاحتياطية', self.check_backup_files_in_repo),
            ('ملفات SQLite', self.check_sqlite_files),
            ('كلمات المرور الافتراضية', self.check_default_passwords_in_scripts),
            ('المجلدات المطلوبة', self.check_required_directories),
            ('.gitignore', self.check_gitignore),
        ]

        for name, check in checks:
            try:
                print(f"  فحص: {name}...")
                check()
            except Exception as e:
                self.issues.append(f"خطأ في فحص {name}: {e}")

        self._print_report()

    def check_env_file(self):
        """فحص وجود ملف .env"""
        env_path = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_path):
            self.issues.append('.env غير موجود')
            if self.fix:
                example = os.path.join(BASE_DIR, '.env.example')
                if os.path.exists(example):
                    import shutil
                    shutil.copy2(example, env_path)
                    self.fixed.append('تم نسخ .env.example إلى .env - تأكد من تعديل القيم!')
                else:
                    self.issues.append('.env.example غير موجود أيضاً')
        else:
            print("    ✅ ملف .env موجود")

    def check_secret_key(self):
        """فحص SECRET_KEY"""
        env_path = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_path):
            return

        with open(env_path, 'r') as f:
            content = f.read()

        insecure_patterns = [
            'change-me', 'your-secret', 'django-insecure',
            'changeme', 'secret-key-here', 'change_me',
        ]

        for pattern in insecure_patterns:
            if pattern in content.lower():
                self.issues.append(f'SECRET_KEY غير آمن (يحتوي على: {pattern})')
                if self.fix:
                    new_key = self._generate_secret_key()
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('DJANGO_SECRET_KEY=') or line.strip().startswith('SECRET_KEY='):
                            key_name = line.split('=')[0]
                            lines[i] = f'{key_name}={new_key}'
                            break
                    with open(env_path, 'w') as f:
                        f.write('\n'.join(lines))
                    self.fixed.append('تم توليد SECRET_KEY جديد')
                return

        print("    ✅ SECRET_KEY آمن")

    def check_debug_mode(self):
        """فحص وضع DEBUG"""
        env_path = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_path):
            return

        with open(env_path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith('DEBUG=') and not stripped.startswith('#'):
                    value = stripped.split('=', 1)[1].strip().lower()
                    if value in ('1', 'true', 'yes'):
                        self.warnings.append(
                            'DEBUG=True. تأكد من تعطيله في الإنتاج (DEBUG=0)'
                        )
                        return

        print("    ✅ DEBUG غير مفعل أو غير محدد")

    def check_database_config(self):
        """فحص إعدادات قاعدة البيانات"""
        env_path = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_path):
            return

        with open(env_path, 'r') as f:
            content = f.read()

        # فحص المحرك
        if 'DB_ENGINE=sqlite' in content.lower() or ('DB_ENGINE' not in content and 'DATABASE_URL' not in content):
            self.warnings.append(
                'قاعدة البيانات SQLite. استخدم PostgreSQL في الإنتاج (DB_ENGINE=postgresql)'
            )
        else:
            print("    ✅ قاعدة البيانات مضبوطة")

        # فحص كلمة مرور قاعدة البيانات
        default_passwords = [
            'POSTGRES_PASSWORD=CHANGE_ME',
            'POSTGRES_PASSWORD=strong_password',
            'POSTGRES_PASSWORD=changeme',
            'POSTGRES_PASSWORD=password',
        ]
        for dp in default_passwords:
            if dp in content:
                self.issues.append(f'كلمة مرور PostgreSQL افتراضية! غيّرها فوراً')
                if self.fix:
                    new_pw = self._generate_password(24)
                    content = content.replace(dp, f'POSTGRES_PASSWORD={new_pw}')
                    with open(env_path, 'w') as f:
                        f.write(content)
                    self.fixed.append('تم توليد كلمة مرور PostgreSQL جديدة')
                break

    def check_allowed_hosts(self):
        """فحص ALLOWED_HOSTS"""
        env_path = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_path):
            return

        with open(env_path, 'r') as f:
            content = f.read()

        if 'ALLOWED_HOSTS=*' in content:
            self.issues.append(
                'ALLOWED_HOSTS=* غير آمن! حدد النطاقات المسموحة.'
            )
        else:
            print("    ✅ ALLOWED_HOSTS مضبوط")

    def check_backup_files_in_repo(self):
        """فحص وجود ملفات النسخ الاحتياطية في المشروع"""
        backup_patterns = ['.backup_', '.sql.gz', '.dump']
        found = []
        for f in os.listdir(BASE_DIR):
            for pattern in backup_patterns:
                if pattern in f and not f.endswith('.example'):
                    found.append(f)

        if found:
            self.warnings.append(
                f'ملفات نسخ احتياطية في المشروع: {", ".join(found[:5])}'
            )
        else:
            print("    ✅ لا توجد ملفات نسخ احتياطية مكشوفة")

    def check_sqlite_files(self):
        """فحص وجود ملفات SQLite"""
        sqlite_files = [
            f for f in os.listdir(BASE_DIR)
            if '.sqlite3' in f and f != 'db.sqlite3'
        ]
        if sqlite_files:
            self.warnings.append(
                f'ملفات SQLite إضافية: {", ".join(sqlite_files[:5])}'
            )
            if self.fix:
                # لا نحذف، فقط ننبه
                self.warnings.append('يُنصح بحذف النسخ القديمة يدوياً بعد التأكد من وجود نسخة احتياطية')
        else:
            print("    ✅ لا توجد ملفات SQLite إضافية")

    def check_default_passwords_in_scripts(self):
        """فحص كلمات المرور الافتراضية في السكريبتات"""
        scripts_dir = os.path.join(BASE_DIR, 'scripts')
        if not os.path.exists(scripts_dir):
            return

        default_passwords = ['admin123', 'password123', '123456']
        found_any = False

        for root, dirs, files in os.walk(scripts_dir):
            for fname in files:
                if fname.endswith(('.sh', '.bat', '.ps1', '.py')):
                    filepath = os.path.join(root, fname)
                    try:
                        with open(filepath, 'r', errors='ignore') as f:
                            content = f.read()
                        for pw in default_passwords:
                            if pw in content:
                                self.warnings.append(
                                    f'كلمة مرور افتراضية "{pw}" في {fname}'
                                )
                                found_any = True
                    except Exception:
                        pass

        if not found_any:
            print("    ✅ لا توجد كلمات مرور افتراضية مكشوفة في السكريبتات")

    def check_required_directories(self):
        """فحص المجلدات المطلوبة"""
        required = ['logs', 'media', 'backups', 'staticfiles']
        missing = []

        for d in required:
            path = os.path.join(BASE_DIR, d)
            if not os.path.exists(path):
                missing.append(d)
                if self.fix:
                    os.makedirs(path, exist_ok=True)
                    self.fixed.append(f'تم إنشاء مجلد {d}/')

        if missing and not self.fix:
            self.issues.append(f'مجلدات مفقودة: {", ".join(missing)}')
        elif not missing:
            print("    ✅ جميع المجلدات المطلوبة موجودة")

    def check_gitignore(self):
        """فحص .gitignore"""
        gitignore_path = os.path.join(BASE_DIR, '.gitignore')
        if not os.path.exists(gitignore_path):
            self.issues.append('.gitignore غير موجود!')
            return

        with open(gitignore_path, 'r') as f:
            content = f.read()

        must_ignore = ['.env', 'db.sqlite3.backup_*']
        missing = [p for p in must_ignore if p not in content]

        if missing:
            self.warnings.append(
                f'أنماط مفقودة من .gitignore: {", ".join(missing)}'
            )
            if self.fix:
                with open(gitignore_path, 'a') as f:
                    f.write('\n\n# Auto-added by prepare_production\n')
                    for pattern in missing:
                        f.write(f'{pattern}\n')
                self.fixed.append('تم تحديث .gitignore')
        else:
            print("    ✅ .gitignore مكتمل")

    def _generate_secret_key(self):
        """توليد مفتاح سري آمن"""
        chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
        return ''.join(secrets.choice(chars) for _ in range(64))

    def _generate_password(self, length=24):
        """توليد كلمة مرور آمنة"""
        chars = string.ascii_letters + string.digits + '!@#$%^&*()'
        return ''.join(secrets.choice(chars) for _ in range(length))

    def _print_report(self):
        """طباعة التقرير النهائي"""
        print("\n" + "-" * 60)

        if self.fixed:
            print("\n  🔧 تم الإصلاح:")
            for item in self.fixed:
                print(f"     ✅ {item}")

        if self.issues:
            print("\n  ❌ مشاكل حرجة:")
            for item in self.issues:
                print(f"     ❌ {item}")

        if self.warnings:
            print("\n  ⚠️  تحذيرات:")
            for item in self.warnings:
                print(f"     ⚠️  {item}")

        if not self.issues and not self.warnings:
            print("\n  ✅ النظام جاهز للإنتاج!")

        print(f"\n  📊 المجموع: {len(self.issues)} مشكلة، {len(self.warnings)} تحذير، {len(self.fixed)} إصلاح")
        print("=" * 60)

        if self.issues and not self.fix:
            print("\n  💡 شغّل مع --fix لمحاولة الإصلاح التلقائي:")
            print("     python tools/prepare_production.py --fix\n")


def main():
    parser = argparse.ArgumentParser(
        description='Tony ERP - تجهيز النظام للإنتاج'
    )
    parser.add_argument(
        '--check', action='store_true', default=True,
        help='فحص فقط (افتراضي)'
    )
    parser.add_argument(
        '--fix', action='store_true',
        help='فحص وإصلاح تلقائي'
    )
    args = parser.parse_args()

    preparer = ProductionPreparer(fix=args.fix)
    preparer.run()


if __name__ == '__main__':
    main()
