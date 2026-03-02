# RITA ERP — دليل مدير النظام
## ADMIN_GUIDE.md — النسخة v2.0

---

## 1. التثبيت والتشغيل

### متطلبات السيرفر
- Ubuntu 20.04+ / Debian 11+
- Python 3.12+
- PostgreSQL 14+
- Nginx
- 4GB RAM، 2 vCPU كحد أدنى

### التثبيت من Scratch

```bash
# 1. Clone المشروع
git clone <repo_url> /var/www/rita-erp
cd /var/www/rita-erp

# 2. بيئة افتراضية
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. متغيرات البيئة
cp .env.example .env
nano .env  # عدّل: SECRET_KEY, DB_*, ALLOWED_HOSTS

# 4. قاعدة البيانات
createdb rita_erp_db
python manage.py migrate --settings=config.settings.production

# 5. المستخدم الأول
python manage.py createsuperuser --settings=config.settings.production

# 6. الملفات الثابتة
python manage.py collectstatic --settings=config.settings.production

# 7. تشغيل الخدمة
cp rita-erp.service /etc/systemd/system/
systemctl enable rita-erp
systemctl start rita-erp
```

### ملف .env

```ini
SECRET_KEY=your-very-long-secret-key-here
DJANGO_ENV=production
DB_NAME=rita_erp_db
DB_USER=rita_erp_user
DB_PASSWORD=strong-password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=erp.yourcompany.com,www.erp.yourcompany.com
DEFAULT_FROM_EMAIL=noreply@yourcompany.com
EMAIL_HOST=smtp.yourcompany.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourcompany.com
EMAIL_HOST_PASSWORD=email-password
```

---

## 2. إدارة المستخدمين

### إضافة مستخدم جديد
1. الإعدادات ← المستخدمون ← "مستخدم جديد"
2. أدخل: الاسم، اسم المستخدم، البريد، كلمة المرور
3. حدد الفرع الافتراضي
4. عيّن الأدوار الوظيفية

### إعادة ضبط كلمة مرور
```bash
python manage.py changepassword <username> --settings=config.settings.production
```
أو من واجهة المدير:
المستخدمون ← اختر المستخدم ← "تغيير كلمة المرور"

### فتح حساب مقفل (Brute Force)
```python
# من Python shell
from apps.authorization.security import reset_brute_force
reset_brute_force('username', 'ip_address')
```
أو: اضغط "فتح الحساب" من صفحة تفاصيل المستخدم.

---

## 3. إدارة الأدوار والصلاحيات

### إنشاء دور جديد
1. الصلاحيات ← الأدوار ← "دور جديد"
2. حدد اسم الدور ومستواه
3. حدد الصلاحيات التفصيلية لكل قسم

### نقل صلاحية مؤقت (تفويض)
1. الصلاحيات ← التفويضات ← "تفويض جديد"
2. حدد المفوِّض، المفوَّض إليه، الدور، المدة

### مستويات الأمان
| الإعداد | القيمة |
|---------|--------|
| محاولات قبل القفل | 5 |
| مدة القفل | 30 دقيقة |
| مدة الجلسة | 8 ساعات |
| 2FA | اختياري لكل مستخدم |

---

## 4. سجل التدقيق (Audit Log)

### عرض السجل
الصلاحيات ← سجل التدقيق

### فلترة السجل
- **بالمستخدم:** عرض كل تصرفات مستخدم معين
- **بالتاريخ:** نشاط فترة زمنية
- **بالقسم:** كل نشاط قسم معين
- **بالـ IP:** نشاط من عنوان IP محدد
- **بالإجراء:** login / logout / create / delete...

### تقرير النشاط
التقارير ← نشاط المستخدمين (مرتب بالوقت)

### تصدير Audit Log
في صفحة سجل التدقيق:
- زر Excel لتصدير السجل الكامل
- قابل للفلترة قبل التصدير

---

## 5. النسخ الاحتياطي

### قاعدة البيانات (PostgreSQL)
```bash
# نسخة احتياطية يدوية
pg_dump rita_erp_db > backup_$(date +%Y%m%d_%H%M).sql

# استعادة
psql rita_erp_db < backup_20260101_0800.sql
```

### Script النسخ الاحتياطي التلقائي
```bash
# /etc/cron.daily/rita-backup
#!/bin/bash
BACKUP_DIR="/backups/rita-erp"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

# قاعدة البيانات
pg_dump rita_erp_db | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# ملفات الوسائط
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" /var/www/rita-erp/media/

# حذف النسخ القديمة (أكثر من 30 يوم)
find "$BACKUP_DIR" -mtime +30 -delete
```

---

## 6. الأداء والمراقبة

### Cache Warmup
```bash
python manage.py shell --settings=config.settings.production
>>> from apps.core.performance import *
>>> # Cache يُملأ تلقائيًا عند أول طلب
```

### مراقبة الـ Logs
```bash
# Logs التطبيق
tail -f /var/www/rita-erp/logs/app.log

# Logs الأمان (Login/Brute Force)
tail -f /var/www/rita-erp/logs/security.log

# Gunicorn
journalctl -u rita-erp -f

# Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Database Indexes
الـ Indexes الجاهزة (Sprint 25):
- `AuditLog.timestamp`, `AuditLog.action`, `AuditLog.module`
- `AuditLog.ip_address`, `AuditLog.object_id`

لإضافة index يدوي:
```sql
CREATE INDEX CONCURRENTLY idx_sales_date ON sales_salesinvoice(invoice_date);
```

---

## 7. التحديثات والـ Migrations

### تحديث النظام
```bash
cd /var/www/rita-erp
git pull origin main

source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production

systemctl restart rita-erp
```

### Migrations آمنة (لا downtime)
```bash
# تشغيل migrations بدون إيقاف الخدمة
python manage.py migrate --settings=config.settings.production --run-syncdb
```

---

## 8. إعداد الشركة

### البيانات الأساسية
الإعدادات ← بيانات الشركة:
- الاسم والاسم القانوني
- الرقم الضريبي والسجل التجاري
- الشعار والختم

### السنة المالية
المحاسبة ← الفترات المحاسبية ← "فترة جديدة"
- تاريخ البداية والنهاية
- تفعيل الفترة

### الفروع والمخازن
الإعدادات ← الفروع ← "فرع جديد"
الإعدادات ← المخازن ← "مخزن جديد"

---

## 9. الأمان والصيانة

### SSL/HTTPS
```bash
# تجديد شهادة SSL (Let's Encrypt)
certbot renew --nginx
systemctl reload nginx
```

### CSP Headers
مُعرّفة في `apps/authorization/middleware.py`.
لتعديل السياسة عدّل `CSP_POLICY` في `ContentSecurityPolicyMiddleware`.

### فحص صحة النظام
```bash
python manage.py check --deploy --settings=config.settings.production
```

### تنظيف الـ Sessions القديمة
```bash
python manage.py clearsessions --settings=config.settings.production
# أو أضفها في cron (أسبوعيًا)
```

---

## 10. استكشاف الأخطاء

### النظام لا يستجيب
```bash
systemctl status rita-erp
journalctl -u rita-erp -n 50
```

### خطأ 500
```bash
# تحقق من السجلات
cat /var/www/rita-erp/logs/app.log | tail -100
```

### قاعدة البيانات بطيئة
```sql
-- الاستعلامات الأبطأ
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### مشكلة في الـ Migrations
```bash
python manage.py showmigrations --settings=config.settings.production
python manage.py migrate --fake <app> <migration_name>
```

---

## 11. Helpdesk

| الحالة | الإجراء |
|--------|---------|
| مستخدم مقفل | admin reset_brute_force |
| نسيان كلمة مرور | changepassword أو من الواجهة |
| بطء في التقارير | تحقق من Indexes وCache |
| خطأ في التصدير | تحقق من openpyxl وxhtml2pdf |
| CSP يمنع محتوى | عدّل CSP_POLICY |

---

*RITA ERP v2.0 — دليل مدير النظام — Sprint 25*
