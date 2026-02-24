#!/usr/bin/env python3
"""
نظام النسخ الاحتياطي والاستعادة - Tony ERP
Backup & Restore System
الاستخدام:
  python tools/backup_and_restore.py backup    ← إنشاء نسخة
  python tools/backup_and_restore.py verify <path> ← تحقق
  python tools/backup_and_restore.py restore <path> --confirm ← استعادة
  python tools/backup_and_restore.py cleanup   ← حذف القديمة
  python tools/backup_and_restore.py test      ← اختبار ذاتي
  python tools/backup_and_restore.py list      ← عرض النسخ
"""
import os
import sys
import json
import gzip
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    dotenv = BASE_DIR / '.env'
    if dotenv.exists():
        for line in dotenv.read_text(errors='ignore').splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip().strip('"\'')
    return env


class BackupManager:
    def __init__(self):
        self.env = load_env()
        self.backup_dir = Path(self.env.get('BACKUP_DIR', str(BASE_DIR / 'backups')))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention = int(self.env.get('BACKUP_RETENTION_DAYS', '30'))
        self.db_engine = self.env.get('DB_ENGINE', 'sqlite')

    # ─── إنشاء نسخة ─────────────────────────────────────────────

    def create(self, label='full'):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = f"backup_{label}_{ts}"
        path = self.backup_dir / name
        path.mkdir(parents=True)

        files, errors = [], []
        print(f"\n{'='*55}")
        print(f"  🔄 إنشاء نسخة: {name}")
        print(f"{'='*55}")

        # 1. قاعدة البيانات
        try:
            f = self._backup_db(path, ts)
            if f:
                files.append(f)
                print(f"  ✅ قاعدة البيانات: {f}")
        except Exception as e:
            errors.append(f"DB: {e}")
            print(f"  ❌ قاعدة البيانات: {e}")

        # 2. ملفات الميديا
        media_dir = BASE_DIR / 'media'
        if media_dir.exists():
            try:
                arc = shutil.make_archive(
                    str(path / f'media_{ts}'), 'gztar',
                    root_dir=str(media_dir.parent), base_dir='media'
                )
                files.append(Path(arc).name)
                print(f"  ✅ ميديا: {Path(arc).name}")
            except Exception as e:
                errors.append(f"Media: {e}")

        # 3. ملفات إعدادات
        cfg_dir = path / 'config'
        cfg_dir.mkdir()
        copied = 0
        for fname in ('.env', 'requirements.txt', 'nginx.conf', 'docker-compose.yml'):
            src = BASE_DIR / fname
            if src.exists():
                shutil.copy2(src, cfg_dir / fname)
                copied += 1
        if copied:
            files.append('config/')
            print(f"  ✅ إعدادات: {copied} ملف")

        # 4. metadata + checksums
        checksums = {}
        for fname in files:
            fp = path / fname
            if fp.is_file():
                checksums[fname] = self._checksum(fp)

        meta = {
            'name': name, 'ts': ts, 'label': label,
            'db_engine': self.db_engine,
            'files': files, 'errors': errors,
            'checksums': checksums,
            'created_at': datetime.now().isoformat(),
        }
        (path / 'backup_metadata.json').write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)
        )

        ok = len(errors) == 0
        status = "✅ اكتملت" if ok else "⚠️  اكتملت جزئياً"
        print(f"\n  {status} | الملفات: {len(files)} | الأخطاء: {len(errors)}")
        print(f"  📂 {path}")
        print(f"{'='*55}\n")
        return {'path': str(path), 'success': ok, 'files': files, 'errors': errors}

    def _backup_db(self, path, ts):
        if 'postgresql' in self.db_engine:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.env.get('POSTGRES_PASSWORD', '')
            out = path / f'db_{ts}.dump'
            subprocess.run([
                'pg_dump',
                '-h', self.env.get('POSTGRES_HOST', 'localhost'),
                '-p', self.env.get('POSTGRES_PORT', '5432'),
                '-U', self.env.get('POSTGRES_USER', self.env.get('POSTGRES_USER', 'tony_user')),
                '-d', self.env.get('POSTGRES_DB', 'tony_erp'),
                '-F', 'c', '-f', str(out),
                '--no-owner', '--no-acl',
            ], env=env, check=True, capture_output=True)
            # ضغط
            gz = out.with_suffix('.dump.gz')
            with open(out, 'rb') as fi, gzip.open(gz, 'wb') as fo:
                shutil.copyfileobj(fi, fo)
            out.unlink()
            return gz.name
        else:
            db = BASE_DIR / 'db.sqlite3'
            if db.exists():
                dst = path / f'db_{ts}.sqlite3.gz'
                with open(db, 'rb') as fi, gzip.open(dst, 'wb') as fo:
                    shutil.copyfileobj(fi, fo)
                return dst.name
        return None

    # ─── التحقق ──────────────────────────────────────────────────

    def verify(self, backup_path):
        backup_path = Path(backup_path)
        print(f"\n  🔍 التحقق: {backup_path.name}")

        meta_file = backup_path / 'backup_metadata.json'
        if not meta_file.exists():
            print("  ❌ metadata.json غير موجود")
            return False

        meta = json.loads(meta_file.read_text())
        all_ok = True

        for fname, expected in meta.get('checksums', {}).items():
            fp = backup_path / fname
            if fp.is_file():
                actual = self._checksum(fp)
                ok = actual == expected
                print(f"  {'✅' if ok else '❌'} {fname}")
                if not ok:
                    all_ok = False
            else:
                print(f"  ❌ {fname} غير موجود")
                all_ok = False

        print(f"  {'✅ سليمة' if all_ok else '❌ تالفة'}\n")
        return all_ok

    # ─── استعادة ─────────────────────────────────────────────────

    def restore(self, backup_path, confirm=False):
        if not confirm:
            print("  ⚠️  استخدم --confirm للتأكيد (سيُحل محل البيانات الحالية!)")
            return False
        backup_path = Path(backup_path)
        if not self.verify(backup_path):
            print("  ❌ التحقق فشل — إلغاء الاستعادة")
            return False

        meta = json.loads((backup_path / 'backup_metadata.json').read_text())
        for fname in meta.get('files', []):
            if 'db_' in fname:
                self._restore_db(backup_path / fname, meta)
                print("  ✅ قاعدة البيانات مُستعادة")
        return True

    def _restore_db(self, dump_path, meta):
        dump_path = Path(dump_path)
        # فك الضغط
        if str(dump_path).endswith('.gz'):
            unzipped = dump_path.with_suffix('')
            with gzip.open(dump_path, 'rb') as fi, open(unzipped, 'wb') as fo:
                shutil.copyfileobj(fi, fo)
            dump_path = unzipped

        if 'postgresql' in meta.get('db_engine', ''):
            env = os.environ.copy()
            env['PGPASSWORD'] = self.env.get('POSTGRES_PASSWORD', '')
            subprocess.run([
                'pg_restore',
                '-h', self.env.get('POSTGRES_HOST', 'localhost'),
                '-p', self.env.get('POSTGRES_PORT', '5432'),
                '-U', self.env.get('POSTGRES_USER', 'tony_user'),
                '-d', self.env.get('POSTGRES_DB', 'tony_erp'),
                '--clean', '--if-exists', '--no-owner', str(dump_path),
            ], env=env, check=True, capture_output=True)
        else:
            db = BASE_DIR / 'db.sqlite3'
            if db.exists():
                shutil.copy2(db, db.with_suffix('.bak'))
            shutil.copy2(dump_path, db)

    # ─── تنظيف ───────────────────────────────────────────────────

    def cleanup(self):
        cutoff = datetime.now().timestamp() - self.retention * 86400
        removed = 0
        for d in self.backup_dir.iterdir():
            if d.is_dir() and d.name.startswith('backup_'):
                if d.stat().st_mtime < cutoff:
                    shutil.rmtree(d)
                    print(f"  🗑️  حذف: {d.name}")
                    removed += 1
        print(f"  ✅ حذف {removed} نسخة قديمة (retention={self.retention}d)\n")
        return removed

    # ─── قائمة النسخ ─────────────────────────────────────────────

    def list_backups(self):
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith('backup_')],
            key=lambda x: x.stat().st_mtime, reverse=True
        )
        if not backups:
            print("  لا توجد نسخ احتياطية بعد.\n")
            return
        print(f"\n  📦 النسخ الاحتياطية ({len(backups)}):")
        for b in backups[:10]:
            size = sum(f.stat().st_size for f in b.rglob('*') if f.is_file())
            age = (datetime.now().timestamp() - b.stat().st_mtime) / 3600
            print(f"  • {b.name}  ({size/1024/1024:.1f}MB, قبل {age:.0f}h)")
        print()

    # ─── اختبار ذاتي ─────────────────────────────────────────────

    def self_test(self):
        print(f"\n{'='*55}")
        print("  🧪 اختبار ذاتي لنظام النسخ الاحتياطي")
        print(f"{'='*55}\n")

        p, f = 0, 0

        # اختبار 1: إنشاء
        r = self.create('selftest')
        if r['files']:
            print("  ✅ الإنشاء نجح")
            p += 1
        else:
            print("  ❌ الإنشاء فشل")
            f += 1

        # اختبار 2: التحقق
        if r.get('path'):
            if self.verify(r['path']):
                print("  ✅ التحقق نجح")
                p += 1
            else:
                print("  ❌ التحقق فشل")
                f += 1
            shutil.rmtree(r['path'], ignore_errors=True)

        # اختبار 3: مجلد النسخ
        if self.backup_dir.is_dir():
            print("  ✅ مجلد النسخ صحيح")
            p += 1
        else:
            print("  ❌ مجلد النسخ مفقود")
            f += 1

        print(f"\n  النتيجة: {p}/{p+f} ✅")
        print(f"{'='*55}\n")
        return f == 0

    # ─── مساعدات ─────────────────────────────────────────────────

    @staticmethod
    def _checksum(path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()


# ─── نقطة الدخول ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    mgr = BackupManager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'

    if cmd == 'backup':
        label = sys.argv[2] if len(sys.argv) > 2 else 'full'
        mgr.create(label)
    elif cmd == 'verify' and len(sys.argv) > 2:
        mgr.verify(sys.argv[2])
    elif cmd == 'restore' and len(sys.argv) > 2:
        mgr.restore(sys.argv[2], confirm='--confirm' in sys.argv)
    elif cmd == 'cleanup':
        mgr.cleanup()
    elif cmd == 'list':
        mgr.list_backups()
    elif cmd == 'test':
        mgr.self_test()
    else:
        print("""
  الاستخدام:
    python tools/backup_and_restore.py backup         ← نسخة احتياطية كاملة
    python tools/backup_and_restore.py list           ← عرض النسخ
    python tools/backup_and_restore.py verify <path>  ← تحقق من نسخة
    python tools/backup_and_restore.py restore <path> --confirm ← استعادة
    python tools/backup_and_restore.py cleanup        ← حذف القديمة
    python tools/backup_and_restore.py test           ← اختبار ذاتي
""")
