"""
سكريبت لإصلاح تعارضات CASCADE+NULL في جميع Models
يقوم بتحليل جميع ملفات models.py واكتشاف الحالات التي تستخدم on_delete=CASCADE مع null=True
"""

import os
import re
from pathlib import Path

# مسار المشروع
BASE_DIR = Path(__file__).resolve().parent

# التطبيقات المطلوب فحصها
APPS_TO_CHECK = [
    'users', 'accounts', 'core', 'inventory', 'sales', 'purchases',
    'accounting', 'partners', 'reports', 'api', 'hr', 'crm',
    'production', 'maintenance', 'payments', 'exports', 'fleet',
    'pos', 'showrooms', 'approvals', 'notifications',
    'woocommerce_integration', 'fixed_assets'
]

def find_cascade_null_conflicts():
    """البحث عن جميع حالات CASCADE+NULL"""
    conflicts = []
    
    for app_name in APPS_TO_CHECK:
        models_file = BASE_DIR / app_name / 'models.py'
        if not models_file.exists():
            continue
            
        content = models_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # البحث عن ForeignKey مع CASCADE و null=True
        for i, line in enumerate(lines, 1):
            if 'ForeignKey' in line or (i < len(lines) and 'on_delete' in lines[i]):
                # جمع السطور التالية للحصول على التعريف الكامل
                full_definition = line
                j = i
                while j < len(lines) and ')' not in full_definition:
                    j += 1
                    if j < len(lines):
                        full_definition += ' ' + lines[j].strip()
                
                # التحقق من وجود CASCADE و null=True معاً
                if 'on_delete=models.CASCADE' in full_definition and 'null=True' in full_definition:
                    conflicts.append({
                        'app': app_name,
                        'file': str(models_file),
                        'line': i,
                        'code': full_definition[:200]  # أول 200 حرف
                    })
    
    return conflicts


def generate_fix_report():
    """إنشاء تقرير شامل بالمشاكل المكتشفة"""
    conflicts = find_cascade_null_conflicts()
    
    report = []
    report.append("=" * 80)
    report.append("تقرير فحص تعارضات CASCADE+NULL في Models")
    report.append("=" * 80)
    report.append(f"\nعدد الحالات المكتشفة: {len(conflicts)}\n")
    
    if not conflicts:
        report.append("✅ لم يتم العثور على أي تعارضات!")
        return '\n'.join(report)
    
    # تجميع حسب التطبيق
    by_app = {}
    for conflict in conflicts:
        app = conflict['app']
        if app not in by_app:
            by_app[app] = []
        by_app[app].append(conflict)
    
    # طباعة النتائج
    for app_name, app_conflicts in sorted(by_app.items()):
        report.append(f"\n{'='*80}")
        report.append(f"التطبيق: {app_name}")
        report.append(f"عدد المشاكل: {len(app_conflicts)}")
        report.append('='*80)
        
        for idx, conflict in enumerate(app_conflicts, 1):
            report.append(f"\n  {idx}. السطر {conflict['line']}:")
            report.append(f"     {conflict['code']}")
    
    # التوصيات
    report.append(f"\n{'='*80}")
    report.append("التوصيات:")
    report.append('='*80)
    report.append("\n1. تغيير on_delete=models.CASCADE إلى on_delete=models.SET_NULL")
    report.append("   للحقول التي تسمح بـ null=True")
    report.append("\n2. أو إزالة null=True, blank=True إذا كان الحقل إلزامياً")
    report.append("\n3. استخدام CASCADE فقط مع الحقول الإلزامية (بدون null=True)")
    
    report.append(f"\n{'='*80}")
    report.append("أمثلة الإصلاح:")
    report.append('='*80)
    report.append("\n# قبل:")
    report.append("user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)")
    report.append("\n# بعد (الخيار 1 - إذا كان اختياري):")
    report.append("user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)")
    report.append("\n# بعد (الخيار 2 - إذا كان إلزامي):")
    report.append("user = models.ForeignKey(User, on_delete=models.CASCADE)")
    
    return '\n'.join(report)


if __name__ == '__main__':
    report = generate_fix_report()
    print(report)
    
    # حفظ التقرير في ملف
    report_file = BASE_DIR / 'CASCADE_NULL_CONFLICTS_REPORT.txt'
    report_file.write_text(report, encoding='utf-8')
    print(f"\n\n✅ تم حفظ التقرير في: {report_file}")
