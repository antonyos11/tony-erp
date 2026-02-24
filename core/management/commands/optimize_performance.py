"""
أمر إدارة لتحسين أداء النظام
System Performance Optimization Management Command
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.conf import settings
import time
import sys


class Command(BaseCommand):
    help = 'تحسين وفحص أداء النظام الشامل'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='تحليل الأداء الحالي',
        )
        parser.add_argument(
            '--optimize-db',
            action='store_true',
            help='تحسين قاعدة البيانات',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='مسح جميع الكاش',
        )
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='تسخين الكاش للاستعلامات الشائعة',
        )
        parser.add_argument(
            '--check-templates',
            action='store_true',
            help='فحص القوالب بحثاً عن أخطاء',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='تشغيل جميع التحسينات',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 نظام تحسين الأداء الشامل'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        start_time = time.time()
        
        if options['full']:
            options['analyze'] = True
            options['optimize_db'] = True
            options['clear_cache'] = True
            options['warm_cache'] = True
            options['check_templates'] = True
        
        if options['analyze']:
            self.analyze_performance()
        
        if options['optimize_db']:
            self.optimize_database()
        
        if options['clear_cache']:
            self.clear_cache()
        
        if options['warm_cache']:
            self.warm_cache()
        
        if options['check_templates']:
            self.check_templates()
        
        elapsed = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ تم الانتهاء في {elapsed:.2f} ثانية'))

    def analyze_performance(self):
        """تحليل الأداء الحالي"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('📊 تحليل الأداء...'))
        
        from django.db import connection
        
        # فحص إعدادات الكاش
        cache_backend = settings.CACHES.get('default', {}).get('BACKEND', 'unknown')
        self.stdout.write(f'   • نوع الكاش: {cache_backend.split(".")[-1]}')
        
        # فحص قاعدة البيانات
        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', 'unknown')
        self.stdout.write(f'   • قاعدة البيانات: {db_engine.split(".")[-1]}')
        
        # فحص Redis
        redis_available = getattr(settings, 'REDIS_AVAILABLE', False)
        self.stdout.write(f'   • Redis متوفر: {"نعم ✓" if redis_available else "لا ✗"}')
        
        # فحص الملفات الثابتة
        static_storage = getattr(settings, 'STATICFILES_STORAGE', 'unknown')
        self.stdout.write(f'   • تخزين الملفات الثابتة: {static_storage.split(".")[-1]}')
        
        # إحصائيات النماذج
        from django.apps import apps
        total_models = len(apps.get_models())
        self.stdout.write(f'   • عدد النماذج: {total_models}')
        
        # اقتراحات التحسين
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('💡 اقتراحات:'))
        
        if not redis_available:
            self.stdout.write('   🔴 قم بتثبيت Redis لتحسين الكاش والجلسات')
        
        if 'sqlite' in db_engine.lower():
            self.stdout.write('   🟡 استخدم PostgreSQL للإنتاج')
        
        if settings.DEBUG:
            self.stdout.write('   🔴 وضع DEBUG مفعل - أوقفه في الإنتاج')

    def optimize_database(self):
        """تحسين قاعدة البيانات"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('🔧 تحسين قاعدة البيانات...'))
        
        from django.db import connection
        
        db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        
        if 'sqlite' in db_engine.lower():
            with connection.cursor() as cursor:
                # VACUUM لتنظيف SQLite
                self.stdout.write('   • تنظيف قاعدة البيانات (VACUUM)...')
                cursor.execute('VACUUM;')
                
                # ANALYZE لتحديث الإحصائيات
                self.stdout.write('   • تحديث الإحصائيات (ANALYZE)...')
                cursor.execute('ANALYZE;')
                
                # تحسين الفهارس
                cursor.execute('PRAGMA optimize;')
                
            self.stdout.write(self.style.SUCCESS('   ✓ تم تحسين SQLite'))
        else:
            self.stdout.write('   ℹ️ قاعدة البيانات لا تحتاج تحسين يدوي')
        
        # تنظيف الجلسات المنتهية
        try:
            from django.contrib.sessions.models import Session
            from datetime import datetime
            expired = Session.objects.filter(expire_date__lt=datetime.now()).delete()
            self.stdout.write(f'   • تم حذف {expired[0]} جلسة منتهية')
        except Exception as e:
            self.stdout.write(f'   ⚠️ تعذر تنظيف الجلسات: {e}')

    def clear_cache(self):
        """مسح الكاش"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('🗑️ مسح الكاش...'))
        
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS('   ✓ تم مسح جميع الكاش'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ فشل مسح الكاش: {e}'))

    def warm_cache(self):
        """تسخين الكاش"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('🔥 تسخين الكاش...'))
        
        try:
            from core.cache_system import CacheWarmer
            
            CacheWarmer.warm_common_queries()
            self.stdout.write(self.style.SUCCESS('   ✓ تم تسخين الاستعلامات الشائعة'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️ فشل تسخين الكاش: {e}'))

    def check_templates(self):
        """فحص القوالب"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('📝 فحص القوالب...'))
        
        from django.template.loader import get_template
        from pathlib import Path
        
        templates_dir = Path(settings.BASE_DIR) / 'templates'
        errors = []
        checked = 0
        
        for template_file in templates_dir.rglob('*.html'):
            relative_path = template_file.relative_to(templates_dir)
            try:
                get_template(str(relative_path))
                checked += 1
            except Exception as e:
                errors.append({
                    'template': str(relative_path),
                    'error': str(e)[:100]
                })
        
        self.stdout.write(f'   • تم فحص {checked} قالب')
        
        if errors:
            self.stdout.write(self.style.WARNING(f'   • وُجد {len(errors)} أخطاء:'))
            for err in errors[:5]:  # أول 5 أخطاء فقط
                self.stdout.write(f'     - {err["template"]}')
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ جميع القوالب سليمة'))
