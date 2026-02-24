"""
أداة تحسين قاعدة البيانات المتقدمة
Advanced Database Optimization Tool
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from django.db import connection, models
from django.apps import apps
from django.core.management import call_command
from django.db.models import Count, F, Q
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """
    أداة شاملة لتحسين قاعدة البيانات
    """
    
    def __init__(self):
        self.issues = []
        self.optimizations = []
        self.stats = {}
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """تحليل شامل لقاعدة البيانات"""
        print("=" * 60)
        print("🔍 تحليل قاعدة البيانات الشامل")
        print("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'tables': self.analyze_tables(),
            'indexes': self.analyze_indexes(),
            'queries': self.analyze_slow_queries(),
            'optimizations': self.get_optimization_suggestions(),
            'size': self.get_database_size(),
        }
        
        return results
    
    def analyze_tables(self) -> List[Dict[str, Any]]:
        """تحليل الجداول"""
        print("\n📊 تحليل الجداول...")
        tables = []
        
        for model in apps.get_models():
            try:
                count = model.objects.count()
                table_name = model._meta.db_table
                
                tables.append({
                    'name': table_name,
                    'model': f"{model._meta.app_label}.{model.__name__}",
                    'rows': count,
                    'fields': len(model._meta.fields),
                    'has_index': self.check_model_indexes(model),
                })
                
                if count > 10000:
                    self.issues.append({
                        'type': 'large_table',
                        'table': table_name,
                        'rows': count,
                        'suggestion': 'فكر في إضافة فهارس أو تقسيم البيانات'
                    })
            except Exception as e:
                logger.warning(f"تعذر تحليل {model.__name__}: {e}")
        
        # ترتيب حسب الحجم
        tables.sort(key=lambda x: x['rows'], reverse=True)
        return tables
    
    def check_model_indexes(self, model) -> Dict[str, Any]:
        """فحص الفهارس لنموذج معين"""
        indexes = {
            'primary': True,  # دائماً موجود
            'foreign_keys': [],
            'custom': [],
        }
        
        for field in model._meta.fields:
            if field.db_index or field.unique:
                indexes['custom'].append(field.name)
            if field.is_relation:
                indexes['foreign_keys'].append(field.name)
        
        # فحص Meta indexes
        if hasattr(model._meta, 'indexes'):
            for idx in model._meta.indexes:
                indexes['custom'].append(str(idx))
        
        return indexes
    
    def analyze_indexes(self) -> List[Dict[str, Any]]:
        """تحليل الفهارس"""
        print("\n🔑 تحليل الفهارس...")
        index_suggestions = []
        
        for model in apps.get_models():
            # فحص الحقول التي تُستخدم في التصفية كثيراً
            common_filter_fields = ['created_at', 'updated_at', 'date', 'status', 'is_active', 'type']
            
            for field in model._meta.fields:
                if field.name in common_filter_fields:
                    if not field.db_index:
                        index_suggestions.append({
                            'model': f"{model._meta.app_label}.{model.__name__}",
                            'field': field.name,
                            'reason': 'حقل يُستخدم كثيراً في التصفية',
                            'priority': 'high',
                        })
        
        return index_suggestions
    
    def analyze_slow_queries(self) -> List[Dict[str, Any]]:
        """تحليل الاستعلامات البطيئة"""
        print("\n⏱️ تحليل الاستعلامات...")
        
        # في SQLite لا يوجد slow query log
        # لكن يمكننا تقديم نصائح عامة
        suggestions = [
            {
                'type': 'use_select_related',
                'description': 'استخدم select_related() للعلاقات ForeignKey',
                'example': 'Model.objects.select_related("foreign_field")',
            },
            {
                'type': 'use_prefetch_related',
                'description': 'استخدم prefetch_related() للعلاقات Many-to-Many',
                'example': 'Model.objects.prefetch_related("many_field")',
            },
            {
                'type': 'use_only',
                'description': 'استخدم only() لجلب الحقول المطلوبة فقط',
                'example': 'Model.objects.only("field1", "field2")',
            },
            {
                'type': 'use_defer',
                'description': 'استخدم defer() لتأجيل تحميل الحقول الكبيرة',
                'example': 'Model.objects.defer("large_text_field")',
            },
            {
                'type': 'avoid_count_in_loop',
                'description': 'تجنب استخدام count() داخل الحلقات',
                'example': 'احسب العدد مرة واحدة قبل الحلقة',
            },
        ]
        
        return suggestions
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """الحصول على اقتراحات التحسين"""
        print("\n💡 اقتراحات التحسين...")
        
        suggestions = []
        
        # فحص الجداول الكبيرة بدون فهارس
        for issue in self.issues:
            if issue['type'] == 'large_table':
                suggestions.append({
                    'priority': 'high',
                    'table': issue['table'],
                    'suggestion': f"أضف فهارس للجدول {issue['table']} ({issue['rows']} صف)",
                    'sql': f"CREATE INDEX idx_{issue['table']}_date ON {issue['table']}(created_at);"
                })
        
        # اقتراحات عامة
        suggestions.extend([
            {
                'priority': 'medium',
                'suggestion': 'فعّل connection pooling في الإنتاج',
                'details': 'استخدم django-db-connection-pool أو pgbouncer',
            },
            {
                'priority': 'medium',
                'suggestion': 'استخدم Redis للكاش بدلاً من الذاكرة',
                'details': 'أضف CACHES في settings.py',
            },
            {
                'priority': 'low',
                'suggestion': 'أضف VACUUM للصيانة الدورية (SQLite)',
                'details': 'شغّل VACUUM ANALYZE دورياً',
            },
        ])
        
        return suggestions
    
    def get_database_size(self) -> Dict[str, Any]:
        """حساب حجم قاعدة البيانات"""
        print("\n📦 حساب حجم قاعدة البيانات...")
        
        from django.conf import settings
        db_settings = settings.DATABASES['default']
        
        size_info = {
            'engine': db_settings.get('ENGINE', 'unknown').split('.')[-1],
        }
        
        if 'sqlite' in db_settings.get('ENGINE', '').lower():
            db_path = db_settings.get('NAME', '')
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                size_info['size_mb'] = round(size_bytes / (1024 * 1024), 2)
        
        return size_info
    
    def vacuum_database(self):
        """تنظيف قاعدة البيانات"""
        print("\n🧹 تنظيف قاعدة البيانات...")
        
        with connection.cursor() as cursor:
            cursor.execute("VACUUM;")
            print("✅ تم تنظيف قاعدة البيانات")
    
    def analyze_unused_data(self) -> Dict[str, Any]:
        """تحليل البيانات غير المستخدمة"""
        print("\n🗑️ تحليل البيانات غير المستخدمة...")
        
        cleanup_suggestions = []
        
        # فحص سجلات التدقيق القديمة
        try:
            from core.models import AuditLog
            old_logs = AuditLog.objects.filter(
                created_at__lt=datetime.now() - timedelta(days=90)
            ).count()
            if old_logs > 1000:
                cleanup_suggestions.append({
                    'model': 'AuditLog',
                    'count': old_logs,
                    'suggestion': 'أرشفة أو حذف سجلات التدقيق الأقدم من 90 يوم',
                })
        except Exception:
            pass
        
        # فحص الجلسات المنتهية
        try:
            from django.contrib.sessions.models import Session
            expired = Session.objects.filter(expire_date__lt=datetime.now()).count()
            if expired > 0:
                cleanup_suggestions.append({
                    'model': 'Session',
                    'count': expired,
                    'suggestion': 'حذف الجلسات المنتهية',
                    'command': 'python manage.py clearsessions',
                })
        except Exception:
            pass
        
        return {'suggestions': cleanup_suggestions}
    
    def generate_report(self) -> str:
        """توليد تقرير كامل"""
        analysis = self.run_full_analysis()
        unused = self.analyze_unused_data()
        
        report = []
        report.append("=" * 60)
        report.append("📋 تقرير تحسين قاعدة البيانات")
        report.append("=" * 60)
        report.append(f"\n📅 التاريخ: {analysis['timestamp']}")
        report.append(f"💾 نوع قاعدة البيانات: {analysis['size'].get('engine', 'unknown')}")
        if 'size_mb' in analysis['size']:
            report.append(f"📦 الحجم: {analysis['size']['size_mb']} MB")
        
        report.append("\n\n📊 أكبر 10 جداول:")
        report.append("-" * 40)
        for table in analysis['tables'][:10]:
            report.append(f"  • {table['name']}: {table['rows']:,} صف")
        
        if analysis['indexes']:
            report.append("\n\n🔑 فهارس مقترحة:")
            report.append("-" * 40)
            for idx in analysis['indexes'][:5]:
                report.append(f"  • {idx['model']}.{idx['field']}")
        
        report.append("\n\n💡 اقتراحات التحسين:")
        report.append("-" * 40)
        for opt in analysis['optimizations']:
            priority = opt.get('priority', 'medium')
            icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
            report.append(f"  {icon} {opt['suggestion']}")
        
        if unused.get('suggestions'):
            report.append("\n\n🗑️ بيانات قابلة للتنظيف:")
            report.append("-" * 40)
            for item in unused['suggestions']:
                report.append(f"  • {item['model']}: {item['count']:,} سجل")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


def run_optimization():
    """تشغيل التحسين"""
    optimizer = DatabaseOptimizer()
    report = optimizer.generate_report()
    print(report)
    
    # حفظ التقرير
    report_path = os.path.join(os.path.dirname(__file__), 'db_optimization_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📄 تم حفظ التقرير في: {report_path}")


if __name__ == '__main__':
    run_optimization()
