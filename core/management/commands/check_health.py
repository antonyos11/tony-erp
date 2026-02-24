"""
أمر Django لفحص صحة النظام
python manage.py check_health
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import shutil
import psutil
import redis
from datetime import datetime


class Command(BaseCommand):
    help = 'فحص صحة النظام الشامل'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.HTTP_INFO('🏥 فحص صحة نظام Tony ERP'))
        self.stdout.write('='*60 + '\n')
        
        checks = []
        
        # 1. فحص قاعدة البيانات
        checks.append(self._check_database(verbose))
        
        # 2. فحص Redis Cache
        checks.append(self._check_redis(verbose))
        
        # 3. فحص Disk Space
        checks.append(self._check_disk_space(verbose))
        
        # 4. فحص Memory
        checks.append(self._check_memory(verbose))
        
        # 5. فحص CPU
        checks.append(self._check_cpu(verbose))
        
        # 6. فحص المجلدات المطلوبة
        checks.append(self._check_directories(verbose))
        
        # 7. فحص الملفات الثابتة
        checks.append(self._check_static_files(verbose))
        
        # الملخص
        self.stdout.write('\n' + '='*60)
        passed = sum(1 for c in checks if c)
        total = len(checks)
        
        if passed == total:
            self.stdout.write(
                self.style.SUCCESS(f'✅ جميع الفحوصات نجحت ({passed}/{total})')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  بعض الفحوصات فشلت ({passed}/{total})')
            )
        
        self.stdout.write('='*60 + '\n')
    
    def _check_database(self, verbose):
        """فحص الاتصال بقاعدة البيانات"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            if verbose:
                db_name = settings.DATABASES['default']['NAME']
                self.stdout.write(f'  Database: {db_name}')
            
            self.stdout.write(
                self.style.SUCCESS('✓ Database Connection: OK')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Database Connection: FAILED - {str(e)}')
            )
            return False
    
    def _check_redis(self, verbose):
        """فحص Redis Cache"""
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            
            if result == 'ok':
                if verbose:
                    # محاولة الحصول على معلومات Redis
                    try:
                        r = redis.from_url(settings.REDIS_URL)
                        info = r.info()
                        self.stdout.write(f'  Redis Version: {info["redis_version"]}')
                        self.stdout.write(f'  Connected Clients: {info["connected_clients"]}')
                    except:
                        pass
                
                self.stdout.write(
                    self.style.SUCCESS('✓ Redis Cache: OK')
                )
                return True
            else:
                raise Exception('Cache test failed')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠ Redis Cache: Not Available - {str(e)}')
            )
            return False
    
    def _check_disk_space(self, verbose):
        """فحص مساحة القرص"""
        try:
            total, used, free = shutil.disk_usage('/')
            free_gb = free // (2**30)
            total_gb = total // (2**30)
            used_percent = (used / total) * 100
            
            if verbose:
                self.stdout.write(f'  Total: {total_gb}GB')
                self.stdout.write(f'  Used: {used_percent:.1f}%')
                self.stdout.write(f'  Free: {free_gb}GB')
            
            if free_gb > 1:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Disk Space: OK ({free_gb}GB free)')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Disk Space: Low ({free_gb}GB free)')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Disk Space: Check Failed - {str(e)}')
            )
            return False
    
    def _check_memory(self, verbose):
        """فحص الذاكرة"""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available // (2**30)
            total_gb = memory.total // (2**30)
            used_percent = memory.percent
            
            if verbose:
                self.stdout.write(f'  Total: {total_gb}GB')
                self.stdout.write(f'  Used: {used_percent}%')
                self.stdout.write(f'  Available: {available_gb}GB')
            
            if available_gb > 0.5:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Memory: OK ({available_gb}GB available)')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Memory: Low ({available_gb}GB available)')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Memory: Check Failed - {str(e)}')
            )
            return False
    
    def _check_cpu(self, verbose):
        """فحص المعالج"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            if verbose:
                self.stdout.write(f'  CPU Cores: {cpu_count}')
                self.stdout.write(f'  CPU Usage: {cpu_percent}%')
            
            if cpu_percent < 90:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ CPU: OK ({cpu_percent}% usage)')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ CPU: High Load ({cpu_percent}%)')
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ CPU: Check Failed - {str(e)}')
            )
            return False
    
    def _check_directories(self, verbose):
        """فحص المجلدات المطلوبة"""
        import os
        required_dirs = ['logs', 'backups', 'media', 'staticfiles']
        missing = []
        
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                missing.append(dir_name)
        
        if not missing:
            self.stdout.write(
                self.style.SUCCESS('✓ Required Directories: OK')
            )
            return True
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ Missing Directories: {", ".join(missing)}')
            )
            return False
    
    def _check_static_files(self, verbose):
        """فحص الملفات الثابتة"""
        import os
        
        static_root = settings.STATIC_ROOT
        if static_root and os.path.exists(static_root):
            file_count = sum(len(files) for _, _, files in os.walk(static_root))
            
            if verbose:
                self.stdout.write(f'  Static Files: {file_count} files')
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Static Files: OK ({file_count} files)')
            )
            return True
        else:
            self.stdout.write(
                self.style.WARNING('⚠ Static Files: Not collected (run collectstatic)')
            )
            return False
