# Tony ERP - الاختبارات والصحة

هذا الملف يوضح أوامر الاختبار، مراقبة الصحة، وضبط بيئة الإنتاج.

## 1. أوامر الاختبار السريعة

```cmd
python manage.py smoke_test         # فحص صفحات رئيسية وتسجيل الدخول سريعاً
python.manage.py health_check       # فحص JSON: قاعدة البيانات، المهاجرات، القرص
python manage.py run_p1_tests --json # سيناريوهات P1 الحرجة (تسجيل دخول + مخزون + قيد محاسبي + API)
```

أمثلة تشغيل تفصيلية:
```cmd
python manage.py run_p1_tests
python manage.py run_p1_tests --json > p1_report.json
```

## 2. توسيع التغطية (مقترح P2/P3)
- `run_p2_tests` (مستقبلي): تدفقات الموارد البشرية، CRM، المشتريات → المبيعات.
- `run_p3_tests` (مستقبلي): التقارير، الموافقات، الأسطول، التصدير.

## 3. مراقبة الصحة (Health / Smoke)
- `smoke_test`: يتأكد من قدرة النظام على إرجاع صفحات أساسية (home, login, dashboard).
- `health_check`: يُرجع JSON يمكن استهلاكه من مراقب خارجي (Nagios / Zabbix / Uptime Robot) يتضمن:
  - database: جاهزية الاتصال
  - migrations: أي مهاجرات متبقية
  - critical_apps: تحقق وجود التطبيقات الحرجة
  - disk: نسبة الاستخدام

تشغيل مع إخراج منسق:
```cmd
python manage.py health_check | python -m json.tool
```

## 4. تنبيهات المخزون منخفض (Low Stock)
- تمت إضافة نموذج `LowStockEvent` (واحد لكل منتج) لتخزين آخر إخطار.
- الإشارة في `inventory/signals.py` تستخدم:
  - Debounce زمني (ثوانٍ قابلة للتعديل عبر `_LOW_STOCK_DEBOUNCE_SECONDS`).
  - مقارنة before/after + delta في الرسالة.
- الحقول:
  - `last_quantity`
  - `threshold`
  - `notification_count`
  - `last_notified_at`

## 5. إعدادات الإنتاج
استخدم ملف: `accountant_pro/settings_prod.py`

تشغيل الخادم بالبيئة الإنتاجية:
```cmd
set DJANGO_SETTINGS_MODULE=accountant_pro.settings_prod
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

متغيرات مهمة:
- `PROD_ALLOWED_HOSTS=erp.example.com` (مطلوب، يمنع wildcard)
- `DATABASE_URL=postgres://...` أو إعدادات محلية PostgreSQL/MySQL
- رفض SQLite في الإنتاج إلا إذا `ALLOW_SQLITE_PROD=1`
- البريد: ضبط `EMAIL_BACKEND` الحقيقي أو السماح المؤقت `ALLOW_CONSOLE_EMAIL=1`

## 6. تسلسل الأرقام (Sequences)
- الملف `core/sequence_utils.py` يوفر نموذج `Sequence` مع دالة `next_sequence`.
- تم استبدال المنطق اليدوي في `create_sample_data.py` لاستخدام:
```python
from core.sequence_utils import next_sequence, format_code
seq = next_sequence('INVOICE')
number = format_code('INV', seq)
```
- فواتير الشراء التجريبية تستخدم مفتاح مستقل `PURCHASE_BILL_SAMPLE` حتى لا تتداخل مع الترقيم التشغيلي.

## 7. إضافة اختبارات جديدة (دليل مختصر)
إنشاء أمر إدارة جديد:
```python
# core/management/commands/run_p2_tests.py
from django.core.management.base import BaseCommand
from django.test import Client

class Command(BaseCommand):
    help = 'P2 test scenarios (HR, CRM, Purchases→Sales)' 
    def handle(self, *args, **options):
        c = Client()
        # 1) تسجيل الدخول
        # 2) إنشاء موظف / فرصة CRM
        # 3) ربط شراء بمبيعات
        self.stdout.write(self.style.SUCCESS('P2 tests placeholder OK'))
```
ثم:
```cmd
python manage.py run_p2_tests
```

## 8. مراقبة أداء مقترحة (مستقبلي)
- دمج عداد (middleware) لحساب عدد الاستعلامات في الطلبات الحرجة.
- خيار `--perf` مستقبلي في `health_check` لقياس زمن استعلام نموذجي.

## 9. استكشاف الأخطاء (Quick Tips)
| العرض | السبب المحتمل | الحل |
|-------|----------------|------|
| تكرار تنبيه مخزون | تعطل حفظ LowStockEvent | راجع السجل `app.log` وخطأ DB | 
| SQLite مرفوض | تشغيل settings_prod بدون DB حقيقية | ضبط `DATABASE_URL` أو `ALLOW_SQLITE_PROD=1` مؤقتاً |
| بريد console ممنوع | حماية إنتاج | ضبط مزود SMTP أو `ALLOW_CONSOLE_EMAIL=1` |

## 10. أوامر مفيدة إضافية
```cmd
python manage.py system_self_check --fix
python manage.py backup_now
python manage.py clear_pyc
python manage.py showmigrations
```

---
تم إعداد هذا الدليل لدعم الاستقرار والاختبار السريع قبل التوسع في التغطية.
