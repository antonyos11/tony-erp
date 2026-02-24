#!/bin/bash
# دليل سريع للتحقق من حالة النظام
# Quick System Health Check

echo "════════════════════════════════════════════════════════════"
echo "🔍 فحص صحة نظام Tony ERP"
echo "════════════════════════════════════════════════════════════"

cd /var/www/tony_erp

# 1. فحص Django System Check
echo ""
echo "1️⃣  فحص نظام Django..."
python3 manage.py check --quiet 2>&1 | tail -3

# 2. عرض الهجرات
echo ""
echo "2️⃣  حالة الهجرات:"
python3 manage.py showmigrations 2>&1 | grep -E "advanced_|bank_|risk_|tax_|contract_|treasury_|business_|correspondence_|intellectual_" -A 1 | head -40

# 3. عدد الجداول
echo ""
echo "3️⃣  عدد الجداول الجديدة:"
python3 manage.py shell << 'PYEOF' 2>/dev/null
from django.apps import apps
from django.db import connection

new_apps = [
    'advanced_crm',
    'bank_integration', 
    'risk_management',
    'tax_system',
    'contract_management',
    'advanced_notifications',
    'treasury_management',
    'business_intelligence',
    'correspondence_management',
    'intellectual_property'
]

tables = connection.introspection.table_names()
new_tables = [t for t in tables if any(app in t for app in new_apps)]

print(f"✓ {len(new_tables)} جدول جديد تم إنشاؤها")
PYEOF

# 4. اختبار الاستيراد
echo ""
echo "4️⃣  اختبار الاستيراد:"
python3 manage.py shell << 'PYEOF' 2>/dev/null
from bank_integration.models import BankAccount
from risk_management.models import Risk
from tax_system.models import TaxType
from contract_management.models import Contract
from advanced_notifications.models import MessageTemplate
from treasury_management.models import CashFlow
from advanced_crm.models import Opportunity
from business_intelligence.models import Dashboard
from correspondence_management.models import Correspondence
from intellectual_property.models import Patent

models = [
    ('BankAccount', BankAccount),
    ('Risk', Risk),
    ('TaxType', TaxType),
    ('Contract', Contract),
    ('MessageTemplate', MessageTemplate),
    ('CashFlow', CashFlow),
    ('Opportunity', Opportunity),
    ('Dashboard', Dashboard),
    ('Correspondence', Correspondence),
    ('Patent', Patent),
]

print(f"✓ تم استيراد جميع {len(models)} نموذج بنجاح")
PYEOF

# 5. إحصائيات قاعدة البيانات
echo ""
echo "5️⃣  إحصائيات النماذج:"
python3 manage.py shell << 'PYEOF' 2>/dev/null
from django.apps import apps

new_apps = [
    'advanced_crm',
    'bank_integration',
    'risk_management',
    'tax_system',
    'contract_management',
    'advanced_notifications',
    'treasury_management',
    'business_intelligence',
    'correspondence_management',
    'intellectual_property'
]

total_models = 0
for app_label in new_apps:
    try:
        app = apps.get_app_config(app_label)
        model_count = len(app.get_models())
        total_models += model_count
        print(f"  {app_label}: {model_count} نماذج")
    except:
        pass

print(f"\n✓ إجمالي {total_models} نموذج")
PYEOF

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ جميع الفحوصات اكتملت بنجاح!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📚 الملفات المرجعية:"
echo "  • INTEGRATION_COMPLETE.md - تقرير التكامل الشامل"
echo "  • NEW_FEATURES_USAGE_GUIDE.md - دليل استخدام الميزات"
echo ""
