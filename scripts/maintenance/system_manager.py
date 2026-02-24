#!/usr/bin/env python
"""
مدير النظام المتقدم - نظام الشامل
يتضمن مراقبة الأداء، النسخ الاحتياطي التلقائي، وإدارة المستخدمين
"""
import os
import sys
import time
import subprocess
import threading
import socket
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

try:  # Prefer shared implementation
    from core.utils.console import safe_print  # type: ignore
except Exception:  # Fallback local (should rarely execute)
    def safe_print(*args, **kwargs):  # pragma: no cover
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            cleaned = []
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
            print(*cleaned, **kwargs)
        except Exception:
            pass


class SystemManager:
    def __init__(self):
        self.project_path = Path(__file__).resolve().parent.parent.parent
        self.db_path = self.project_path / "db.sqlite3"
        self.backup_path = self.project_path / "backups"
        self.logs_path = self.project_path / "logs"
        self.server_process = None
        self.monitoring_thread = None
        self.is_running = False
        
        # إنشاء المجلدات اللازمة
        self.backup_path.mkdir(exist_ok=True)
        self.logs_path.mkdir(exist_ok=True)
        
    def get_local_ip(self):
        """الحصول على عنوان IP المحلي"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def check_system_health(self):
        """فحص صحة النظام"""
        safe_print("فحص صحة النظام ...")

        issues = []

        # فحص مساحة القرص
        if hasattr(shutil, 'disk_usage'):
            total, used, free = shutil.disk_usage(self.project_path)
            free_gb = free // (1024**3)
            if free_gb < 1:
                issues.append("تحذير: مساحة القرص المتبقية أقل من 1GB")

        # فحص قاعدة البيانات
        if not self.db_path.exists():
            issues.append("خطأ: ملف قاعدة البيانات غير موجود")
        else:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.execute("SELECT 1")
                conn.close()
                safe_print("قاعدة البيانات سليمة")
            except Exception as e:
                issues.append(f"خطأ في قاعدة البيانات: {e}")

        # فحص المنافذ
        port = 8000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            issues.append(f"تحذير: المنفذ {port} مستخدم بالفعل")

        if issues:
            safe_print("تحذير: تم العثور على مشاكل:")
            for issue in issues:
                safe_print(f"   {issue}")
            return False
        else:
            safe_print("النظام جاهز للعمل")
            return True
    
    def create_backup(self):
        """إنشاء نسخة احتياطية"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_path / f"backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_file)
            safe_print(f"تم إنشاء نسخة احتياطية: {backup_file.name}")
            
            # الاحتفاظ بآخر 7 نسخ فقط
            backups = sorted(self.backup_path.glob("backup_*.db"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    safe_print(f"حذف نسخة قديمة: {old_backup.name}")
                    
            return True
        except Exception as e:
            safe_print(f"فشل إنشاء النسخة الاحتياطية: {e}")
            return False
    
    def get_system_stats(self):
        """الحصول على إحصائيات النظام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # عدد المستخدمين
            cursor.execute("SELECT COUNT(*) FROM auth_user")
            users_count = cursor.fetchone()[0]
            
            # عدد الجلسات النشطة
            cursor.execute("SELECT COUNT(*) FROM users_usersession WHERE is_active = 1")
            active_sessions = cursor.fetchone()[0]
            
            # عدد الأنشطة اليوم
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(f"SELECT COUNT(*) FROM users_useractivity WHERE date(timestamp) = ?", (today,))
            today_activities = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'users_count': users_count,
                'active_sessions': active_sessions,
                'today_activities': today_activities,
                'db_size': self.db_path.stat().st_size / (1024*1024)  # MB
            }
        except Exception as e:
            return {'error': str(e)}
    
    def monitor_system(self):
        """مراقبة النظام في خيط منفصل"""
        backup_interval = 24 * 60 * 60  # 24 ساعة
        last_backup = time.time()
        
        while self.is_running:
            try:
                # إنشاء نسخة احتياطية كل 24 ساعة
                if time.time() - last_backup > backup_interval:
                    self.create_backup()
                    last_backup = time.time()
                
                # عرض الإحصائيات كل 5 دقائق
                stats = self.get_system_stats()
                if 'error' not in stats:
                    current_time = datetime.now().strftime("%H:%M")
                    safe_print(f"\nإحصائيات النظام [{current_time}]:")
                    safe_print(f"   المستخدمون: {stats['users_count']}")
                    safe_print(f"   الجلسات النشطة: {stats['active_sessions']}")
                    safe_print(f"   أنشطة اليوم: {stats['today_activities']}")
                    safe_print(f"   حجم قاعدة البيانات: {stats['db_size']:.1f} MB")
                
                time.sleep(300)  # انتظار 5 دقائق
                
            except Exception as e:
                safe_print(f"خطأ في المراقبة: {e}")
                time.sleep(60)  # انتظار دقيقة عند حدوث خطأ
    
    def start_server(self, port=8000):
        """تشغيل الخادم"""
        local_ip = self.get_local_ip()
        
        safe_print(f"بدء تشغيل النظام ...")
        safe_print(f"عنوان الشبكة: {local_ip}:{port}")
        
        # بدء مراقبة النظام
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self.monitor_system, daemon=True)
        self.monitoring_thread.start()
        
        try:
            # تشغيل خادم Django
            cmd = [sys.executable, "manage.py", "runserver", f"{local_ip}:{port}"]
            self.server_process = subprocess.Popen(
                cmd, 
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            safe_print(f"\n{'='*60}")
            safe_print("النظام يعمل الآن")
            safe_print(f"{'='*60}")
            safe_print(f"الرابط المحلي: http://localhost:{port}")
            safe_print(f"رابط الشبكة: http://{local_ip}:{port}")
            safe_print("المدير: superadmin / admin123")
            safe_print(f"{'='*60}")
            safe_print("لإيقاف النظام: Ctrl+C")
            safe_print(f"{'='*60}\n")
            
            # قراءة output من Django
            if self.server_process and self.server_process.stdout:
                for line in iter(self.server_process.stdout.readline, ''):
                    if line:
                        safe_print(f"[Server] {line.rstrip()}")
            else:
                safe_print("تحذير: لا يمكن قراءة output من الخادم")
                    
        except Exception as e:
            safe_print(f"خطأ في تشغيل الخادم: {e}")
    
    def stop_server(self):
        """إيقاف الخادم"""
        self.is_running = False
        
        if self.server_process:
            safe_print("\nإيقاف الخادم ...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            safe_print("تم إيقاف الخادم")
    
    def run_command(self, command):
        """تشغيل أوامر Django management"""
        try:
            result = subprocess.run([
                sys.executable, "manage.py"
            ] + command, 
            cwd=self.project_path,
            capture_output=True,
            text=True
            )
            
            if result.returncode == 0:
                safe_print("أُنجز الأمر بنجاح")
                if result.stdout:
                    safe_print(result.stdout)
                return True
            else:
                safe_print("فشل تنفيذ الأمر")
                if result.stderr:
                    safe_print(result.stderr)
                return False
                
        except Exception as e:
            safe_print(f"خطأ: {e}")
            return False
    
    def show_menu(self):
        """عرض القائمة التفاعلية"""
        while True:
            safe_print(f"\n{'='*50}")
            safe_print("مدير النظام")
            safe_print(f"{'='*50}")
            safe_print("1. تشغيل النظام على الشبكة")
            safe_print("2. فحص صحة النظام") 
            safe_print("3. إنشاء نسخة احتياطية")
            safe_print("4. عرض الإحصائيات")
            safe_print("5. إعداد الأدوار والصلاحيات")
            safe_print("6. إنشاء مدير عام جديد")
            safe_print("7. تحديث قاعدة البيانات")
            safe_print("8. خروج")
            safe_print(f"{'='*50}")
            
            choice = input("اختر رقماً (1-8): ").strip()
            
            if choice == '1':
                if not self.check_system_health():
                    safe_print("تحذير: يرجى حل المشاكل أولاً")
                    continue
                self.start_server()
                break
                
            elif choice == '2':
                self.check_system_health()
                
            elif choice == '3':
                self.create_backup()
                
            elif choice == '4':
                stats = self.get_system_stats()
                if 'error' not in stats:
                    safe_print(f"\nإحصائيات النظام:")
                    safe_print(f"   إجمالي المستخدمين: {stats['users_count']}")
                    safe_print(f"   الجلسات النشطة: {stats['active_sessions']}")
                    safe_print(f"   أنشطة اليوم: {stats['today_activities']}")
                    safe_print(f"   حجم قاعدة البيانات: {stats['db_size']:.1f} MB")
                else:
                    safe_print(f"خطأ في جلب الإحصائيات: {stats['error']}")
                    
            elif choice == '5':
                safe_print("إعداد الأدوار والصلاحيات...")
                self.run_command(['setup_roles_permissions'])
                
            elif choice == '6':
                username = input("اسم المستخدم: ")
                email = input("البريد الإلكتروني: ")
                arabic_name = input("الاسم بالعربية: ")
                employee_id = input("رقم الموظف: ")
                
                self.run_command([
                    'create_superadmin',
                    f'--username={username}',
                    f'--email={email}',
                    f'--arabic-name={arabic_name}',
                    f'--employee-id={employee_id}'
                ])
                
            elif choice == '7':
                safe_print("تحديث قاعدة البيانات ...")
                self.run_command(['migrate'])
                
            elif choice == '8':
                safe_print("شكراً لاستخدام نظام الشامل")
                break
                
            else:
                safe_print("اختيار غير صحيح")
            
            input("\nاضغط Enter للمتابعة...")


def main():
    manager = SystemManager()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--auto':
            # تشغيل تلقائي
            if manager.check_system_health():
                manager.start_server()
        else:
            # تشغيل تفاعلي
            manager.show_menu()
            
    except KeyboardInterrupt:
        safe_print("\n\nتم إيقاف النظام")
        manager.stop_server()
    except Exception as e:
        safe_print(f"\nخطأ غير متوقع: {e}")
    finally:
        safe_print("\nتم إغلاق مدير النظام")


if __name__ == "__main__":
    main()