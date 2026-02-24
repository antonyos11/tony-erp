#!/usr/bin/env python
"""تشغيل النظام (محسن) مع إخراج متوافق Windows"""
import os
import sys
import subprocess
import socket
import time
import webbrowser
from pathlib import Path
from typing import Optional

try:
    from core.utils.console import safe_print  # noqa: F401
except Exception:  # pragma: no cover
    def safe_print(*args, **kwargs) -> None:  # fallback with cleansing
        try:
            print(*args, **kwargs)
            return
        except UnicodeEncodeError:
            cleaned: list[str] = []
            for a in args:
                try:
                    s = str(a)
                except Exception:
                    s = repr(a)
                s2 = ''.join(ch for ch in s if (ord(ch) < 128) or ch.isalnum() or ch.isspace() or '\u0600' <= ch <= '\u06FF')
                cleaned.append(s2)
            try:
                print(*cleaned, **kwargs)
            except Exception:
                pass
        except Exception:
            pass


class SystemManager:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.venv_path = self.base_dir / ".venv"
        self.python_exe = self.venv_path / "Scripts" / "python.exe"
        self.manage_py = self.base_dir / "manage.py"

    # ---------------------------- واجهة مستخدم ----------------------------
    def print_banner(self):
        safe_print("\n" + "=" * 60)
        safe_print("نظام الشامل للمحاسبة والإدارة المتكامل")
        safe_print("الإصدار: 2025 - الشبكة المحلية")
        safe_print("=" * 60)

    # --------------------------- فحص البيئة -------------------------------
    def check_virtual_environment(self) -> bool:
        safe_print("فحص البيئة الافتراضية ...")
        if not self.venv_path.exists():
            safe_print("خطأ: البيئة الافتراضية غير موجودة")
            return False
        if not self.python_exe.exists():
            safe_print("خطأ: مفسر Python غير موجود داخل البيئة")
            return False
        safe_print("البيئة الافتراضية جاهزة")
        return True

    # --------------------------- أدوات مساعدة ----------------------------
    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def run_command(self, command, show_output=True):
        full = [str(self.python_exe), str(self.manage_py)] + command
        try:
            result = subprocess.run(
                full,
                cwd=self.base_dir,
                capture_output=not show_output,
                text=True,
                check=True,
            )
            if not show_output and result.stdout:
                safe_print(result.stdout)
            return True, getattr(result, 'stdout', '')
        except subprocess.CalledProcessError as e:
            safe_print(f"خطأ في الأمر: {' '.join(command)}")
            if getattr(e, 'stderr', ''):
                safe_print(f"تفاصيل: {e.stderr}")
            return False, ''

    # --------------------------- قاعدة البيانات ---------------------------
    def setup_database(self) -> bool:
        safe_print("\nإعداد قاعدة البيانات ...")
        ok, _ = self.run_command(["showmigrations"], show_output=False)
        if not ok:
            safe_print("تحذير: تعذر عرض migrations")
        safe_print("تطبيق migrations ...")
        ok, _ = self.run_command(["migrate"], show_output=False)
        if ok:
            safe_print("تم تحديث قاعدة البيانات بنجاح")
            return True
        safe_print("فشل تحديث قاعدة البيانات")
        return False

    # -------------------------- ملفات ثابتة -------------------------------
    def collect_static_files(self) -> bool:
        safe_print("\nجمع الملفات الثابتة ...")
        ok, _ = self.run_command(["collectstatic", "--noinput"], show_output=False)
        if ok:
            safe_print("تم جمع الملفات الثابتة")
        return ok

    # -------------------------- فحص النظام --------------------------------
    def run_system_check(self) -> bool:
        safe_print("\nفحص النظام ...")
        _, output = self.run_command(["check"], show_output=False)
        if "no issues" in output:
            safe_print("النظام جاهز")
        else:
            safe_print("تحذير: ملاحظات غير حرجة (مسموح محلياً)")
        return True

    # ---------------------- المستخدم الإداري ------------------------------
    def create_superuser_if_needed(self) -> bool:
        safe_print("\nفحص المستخدم الإداري ...")
        cmd = [
            "shell",
            "-c",
            "from django.contrib.auth.models import User; print('EXISTS' if User.objects.filter(is_superuser=True).exists() else 'NONE')",
        ]
        ok, output = self.run_command(cmd, show_output=False)
        if ok and "EXISTS" in output:
            safe_print("المستخدم الإداري موجود: superadmin")
        else:
            safe_print("تحذير: لا يوجد مستخدم إداري (يمكن إنشاؤه لاحقاً)")
        return True

    # --------------------------- تشغيل الخادم -----------------------------
    def start_server(self, ip="127.0.0.1", port=8000):
        safe_print(f"\nتشغيل الخادم على {ip}:{port}")
        safe_print("\n" + "=" * 60)
        safe_print("روابط الوصول:")
        safe_print(f"  - المحلي: http://127.0.0.1:{port}")
        if ip != "127.0.0.1":
            safe_print(f"  - الشبكة: http://{ip}:{port}")
        safe_print("\nبيانات الدخول:")
        safe_print("  - المستخدم: superadmin")
        safe_print("  - كلمة المرور: admin123")
        safe_print("\nملاحظات:")
        safe_print("  - Ctrl+C للإيقاف")
        safe_print("  - تأكد أن كل الأجهزة على نفس الشبكة")
        safe_print("=" * 60)
        safe_print("\nبدء الخادم ...")
        try:
            time.sleep(2)
            webbrowser.open(f"http://127.0.0.1:{port}")
            subprocess.run(
                [str(self.python_exe), str(self.manage_py), "runserver", f"{ip}:{port}"],
                cwd=self.base_dir,
            )
        except KeyboardInterrupt:
            safe_print("\nتم إيقاف الخادم")
        except Exception as e:
            safe_print(f"\nخطأ في تشغيل الخادم: {e}")

    # ----------------------------- المسار الرئيسي -------------------------
    def main(self):
        self.print_banner()
        if not self.check_virtual_environment():
            safe_print("\nتعذر العثور على البيئة الافتراضية")
            input("اضغط Enter للخروج...")
            return False
        if not self.setup_database():
            safe_print("\nفشل في إعداد قاعدة البيانات")
            input("اضغط Enter للخروج...")
            return False
        self.collect_static_files()
        self.run_system_check()
        self.create_superuser_if_needed()
        ip = self.get_local_ip()
        safe_print(f"\nعنوان IP المحلي: {ip}")
        safe_print("\nاختر طريقة التشغيل:")
        safe_print("1. تشغيل محلي (localhost فقط)")
        safe_print("2. تشغيل على الشبكة المحلية (جميع الأجهزة)")
        try:
            choice = input("\nاختر (1 أو 2) [افتراضي: 2]: ").strip()
            if choice == "1":
                self.start_server("127.0.0.1", 8000)
            else:
                self.start_server("0.0.0.0", 8000)
        except KeyboardInterrupt:
            safe_print("\nتم إلغاء التشغيل")
        return True


if __name__ == "__main__":
    mgr = SystemManager()
    try:
        mgr.main()
    except Exception as exc:  # pragma: no cover
        safe_print(f"\nخطأ غير متوقع: {exc}")
        input("اضغط Enter للخروج...")