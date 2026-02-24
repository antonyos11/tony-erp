# تشغيل النظام داخلياً على جهاز ويندوز كسيرفر (دليل شامل)

هذا الدليل يجهز الجهاز ليعمل كسيرفر داخلي، وباقي أجهزة الشبكة تدخل عبر المتصفح.

## المتطلبات الأساسية
1. Python 3.11 أو أحدث (مضاف إلى PATH)
2. (اختياري الآن / مستحسن لاحقاً) PostgreSQL 14+ بدل SQLite
3. PowerShell (مع صلاحية تنفيذ سكربتات ExecutionPolicy Bypass مؤقت)
4. اتصال إنترنت لتنزيل الحزم (أول مرة)
5. (اختياري) NSSM لخدمات ويندوز: ضع `nssm.exe` في `C:\nssm\`
6. (اختياري) openssl لاستخراج ملفات PEM للشهادة الذاتية

## (أ) أسرع تشغيل يدوي (خطوات أساسية)
```powershell
cd D:\الشامل
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress
```

## ملف البيئة `.env`
أنشئ ملف `D:\الشامل\.env` (عدّل القيم):
```
DJANGO_SETTINGS_MODULE=accountant_pro.settings
DEBUG=False
SECRET_KEY=غيّر_هذه_القيمة_وارفع_طولها_52_حرفاً
ALLOWED_HOSTS=127.0.0.1,0.0.0.0,localhost,192.168.1.50,erp.local
TIME_ZONE=Africa/Cairo
# لو استخدمت PostgreSQL ارفع السطر التالي
# DATABASE_URL=postgres://erp_user:StrongPass@127.0.0.1:5432/tonyerp
```

## جمع الملفات الثابتة وتشغيل التهيئة
```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # نفّذ مرة واحدة
```

## سكربت التشغيل `start_waitress.bat`
يوضع في `D:\الشامل\start_waitress.bat`:
```
@echo off
setlocal
cd /d D:\الشامل
call .venv\Scripts\activate.bat
REM يمكن تعديل المنفذ لاحقاً إلى 80 خلف عكس (Reverse Proxy)
waitress-serve --listen=0.0.0.0:8000 accountant_pro.wsgi:application
```

## فتح المنفذ في جدار الحماية
نفّذ مرة واحدة (PowerShell مسؤول):
```powershell
New-NetFirewallRule -DisplayName "TonyERP 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

## تثبيت الخدمة (NSSM)
1. حمّل nssm (انسخ nssm.exe إلى مسار ثابت مثال: `C:\nssm\nssm.exe`).
2. PowerShell (مسؤول):
```powershell
C:\nssm\nssm.exe install TonyERP "D:\الشامل\.venv\Scripts\python.exe" "D:\الشامل\manage.py" runserver 0.0.0.0:8000
```
(أبسط بديل: خدمة تستخدم `start_waitress.bat` بدل runserver)
```powershell
C:\nssm\nssm.exe install TonyERP "D:\الشامل\start_waitress.bat"
```
3. بعد التثبيت:
```powershell
C:\nssm\nssm.exe set TonyERP Start SERVICE_AUTO_START
net start TonyERP
```

## استعمال اسم بدلاً من IP
عدِّل ملف hosts على الأجهزة العميلة (كمستخدم مسؤول):
```
192.168.1.50   erp.local
```
ثم ادخل: `http://erp.local:8000/`

## اختبار من جهاز عميل
```powershell
ping 192.168.1.50
Test-NetConnection 192.168.1.50 -Port 8000
```

## السكربت الموحد ALL-IN-ONE (مستحسن للمبتدئين)
لتنفيذ كل شيء (تهيئة + اختيار PostgreSQL + شهادة HTTPS + خدمة + Celery + نسخ احتياطي):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./deploy_windows/all_in_one_setup.ps1 -ServerIP 192.168.1.50 -UsePostgres -PgPassword StrongPass123! -UseDaphne -CreateCert -CertDns erp.local -RegisterCelery -ScheduleBackup -FullZipBackup -MigrateIfPostgres -Force
```
يمكن إزالة المعاملات التي لا تريدها (مثلاً احذف -UsePostgres لو ستبقى على SQLite).

المعاملات المهمة:
- `-UseDaphne` لتشغيل ASGI (WebSockets) عبر daphne بدلاً من waitress.
- `-CreateCert` + `-CertDns erp.local` لإنشاء شهادة HTTPS داخلية.
- `-RegisterCelery` لإنشاء خدمات worker/beat/flower.
- `-ScheduleBackup` لإنشاء مهمة نسخ احتياطي يومي.
- `-FullZipBackup` لإنشاء نسخة ZIP فورية.
- `-MigrateIfPostgres` يرحّل بيانات SQLite إلى PostgreSQL بعد الإنشاء.

## تشغيل بـ Daphne يدوي (بدون السكربت الموحد)
```powershell
.\.venv\Scripts\Activate.ps1
daphne -b 0.0.0.0 -p 8000 accountant_pro.asgi:application
```
لخدمة NSSM بـ daphne مع شهادة (بعد إنشاء الشهادة):
```powershell
./deploy_windows/register_service_nssm.ps1 -ServiceName TonyERP -Mode daphne -Port 8000 -CertPath D:\الشامل\certs\erp.local.crt.pem -KeyPath D:\الشامل\certs\erp.local.key.pem
```

## إنشاء شهادة HTTPS ذاتية (داخلياً)
```powershell
./deploy_windows/make_self_signed_cert.ps1 -DnsName erp.local -OutDir D:\الشامل\certs
```
وزّع ملف CER واستورده في Trusted Root على الأجهزة العميلة لتجنب التحذيرات.

## تسجيل خدمات Celery + Flower (منفرداً)
```powershell
./deploy_windows/register_celery_services.ps1 -NssmPath C:\nssm\nssm.exe -ServicePrefix TonyERP
```
اللوحة: http://192.168.1.50:5555

## نسخ احتياطي بسيط
```powershell
./deploy_windows/backup_simple.ps1
```
## نسخ احتياطي مضغوط شامل (مع تدوير)
SQLite:
```powershell
./deploy_windows/backup_full_zip.ps1 -Keep 10
```
PostgreSQL:
```powershell
./deploy_windows/backup_full_zip.ps1 -PgDb tonyerp -PgUser erp_user -PgPassword StrongPass123! -Keep 14
```
## جدولة النسخ الاحتياطي اليومي (XML جاهز)
```powershell
schtasks /Create /TN "TonyERP_DailyBackup" /XML "D:\الشامل\deploy_windows\backup_daily_task.xml"
```

## ترحيل SQLite إلى PostgreSQL (يدوياً)
```powershell
./deploy_windows/migrate_sqlite_to_postgres.ps1 -DbName tonyerp -DbUser erp_user -DbPassword StrongPass123!
```

## نسخ احتياطية سريعة (لو بقيت على SQLite)
انسخ `db.sqlite3` و`media` أو استخدم السكربتات أعلاه.

## PostgreSQL (مستحسن للإنتاج)
1. تثبيت PostgreSQL ثم إعداد مستخدم وقاعدة (psql):
	```sql
	CREATE USER erp_user WITH PASSWORD 'StrongPass123!';
	CREATE DATABASE tonyerp OWNER erp_user;
	```
2. ضبط `DATABASE_URL` في `.env` أو تشغيل:
	```powershell
	./deploy_windows/setup_postgres.ps1 -DbName tonyerp -DbUser erp_user -DbPassword StrongPass123!
	```
3. (إن كنت تملك بيانات قديمة في SQLite) استخدم سكربت الترحيل.

## تحديث الحزم
```powershell
.\.venv\Scripts\Activate.ps1
pip list --outdated
pip install --upgrade <package>
```

## إيقاف وتشغيل الخدمة
```powershell
net stop TonyERP
net start TonyERP
```

## ملاحظات أمان مهمة
1. غيّر كلمة مرور superadmin مباشرة بعد أول دخول.
2. اجعل `DEBUG=False` دائماً في السيرفر.
3. خزّن ملف `.env` خارج النسخ العامة (لا ترفعه Git).
4. استخدم كلمات مرور قوية (قاعدة البيانات، Flower، الخ).
5. راقب أحجام اللوج وقم بأرشفتها دورياً.
6. لو فعّلت HTTPS ذاتي، وزّع الشهادة بأمان ولا تستخدمها خارج الشبكة.

## استكشاف أخطاء شائعة
| العرض | السبب المحتمل | الحل |
|-------|---------------|------|
| المتصفح لا يفتح IP | منفذ مغلق / IP خاطئ | تأكد من `Test-NetConnection <IP> -Port 8000` وفتح الجدار |
| خطأ SSL | شهادة غير مستوردة | استورد CER إلى Trusted Root |
| WebSockets لا تعمل | تشغيل waitress بدلاً من daphne | أعد تسجيل الخدمة بـ daphne |
| بطء أول زيارة | جمع static لم يتم | شغّل `python manage.py collectstatic` |
| أخطاء قاعدة بعد الترحيل | فشل loaddata | أعد الترحيل أو افحص السجلات |

انتهى — استخدم السكربت الموحد لتوفير الوقت، ثم عدل الخيارات حسب حاجتك.

انتهى. عدّل أي قيم حسب شبكة شركتك.
