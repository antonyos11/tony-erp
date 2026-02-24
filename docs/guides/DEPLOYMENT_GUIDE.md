# دليل نشر Tony ERP للإنتاج
# Tony ERP Production Deployment Guide

## 📋 المتطلبات | Requirements

### الخادم | Server Requirements
- **نظام التشغيل**: Ubuntu 22.04 LTS أو Debian 11+
- **المعالج**: 2+ vCPU
- **الذاكرة**: 4GB RAM (يُفضل 8GB)
- **التخزين**: 40GB SSD
- **Docker**: الإصدار 20.10+
- **Docker Compose**: الإصدار 2.0+

### المتطلبات الخارجية | External Services
- نطاق مسجل (Domain)
- حساب SendGrid للبريد الإلكتروني
- حساب Paymob للمدفوعات
- حساب Sentry للمراقبة (اختياري)
- حساب Google Analytics (اختياري)

---

## 🚀 خطوات النشر السريع | Quick Deployment

### 1. تجهيز الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# تثبيت Docker Compose
sudo apt install docker-compose-plugin

# تأكيد التثبيت
docker --version
docker compose version
```

### 2. تحميل الكود

```bash
# إنشاء مجلد المشروع
sudo mkdir -p /var/www/tony_erp
sudo chown -R $USER:$USER /var/www/tony_erp
cd /var/www/tony_erp

# استنساخ المشروع
git clone https://github.com/your-repo/tony_erp.git .
```

### 3. إعداد البيئة

```bash
# نسخ ملف البيئة
cp deploy/.env.production deploy/.env

# تحرير الملف وإضافة القيم الحقيقية
nano deploy/.env
```

⚠️ **هام**: تأكد من ملء جميع المتغيرات، خاصة:
- `SECRET_KEY` - مفتاح فريد وطويل
- `POSTGRES_PASSWORD` - كلمة مرور قوية
- `PAYMOB_*` - بيانات Paymob
- `EMAIL_*` - بيانات SendGrid

### 4. إنشاء المجلدات المطلوبة

```bash
mkdir -p deploy/backups
mkdir -p deploy/errors
chmod +x deploy/deploy.sh
chmod +x deploy/backup.sh
```

### 5. تشغيل التطبيق

```bash
cd deploy
./deploy.sh start
```

### 6. إعداد SSL

```bash
./deploy.sh ssl-init yourdomain.com admin@yourdomain.com
```

### 7. التحقق من التشغيل

```bash
./deploy.sh health
./deploy.sh status
```

---

## 🔧 الإعدادات التفصيلية | Detailed Configuration

### إعدادات Paymob

1. سجل دخول إلى [Paymob Dashboard](https://accept.paymob.com)
2. انتقل إلى Settings > Integration IDs
3. انسخ القيم التالية:
   - API Key
   - Integration ID (للبطاقات)
   - Wallet Integration ID
   - HMAC Secret

```env
PAYMOB_API_KEY=ZXlKaGJHY2...
PAYMOB_INTEGRATION_ID=123456
PAYMOB_IFRAME_ID=654321
PAYMOB_HMAC_SECRET=abc123...
```

### إعدادات SendGrid

1. أنشئ حساب على [SendGrid](https://sendgrid.com)
2. انتقل إلى Settings > API Keys
3. أنشئ API Key جديد
4. تحقق من النطاق (Domain Authentication)

```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxxxx...
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### إعدادات Google Analytics

1. أنشئ حساب GA4 على [Google Analytics](https://analytics.google.com)
2. انتقل إلى Admin > Data Streams
3. انسخ Measurement ID

```env
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
```

---

## 📊 أوامر الإدارة | Management Commands

### التشغيل والإيقاف

```bash
# تشغيل
./deploy.sh start

# إيقاف
./deploy.sh stop

# إعادة تشغيل
./deploy.sh restart

# حالة الخدمات
./deploy.sh status
```

### السجلات والمراقبة

```bash
# جميع السجلات
./deploy.sh logs

# سجلات خدمة معينة
./deploy.sh logs web
./deploy.sh logs celery
./deploy.sh logs nginx
```

### النسخ الاحتياطي

```bash
# نسخة يدوية
./deploy.sh backup

# استعادة نسخة
gunzip < deploy/backups/tony_erp_20260117_120000.sql.gz | \
  docker compose exec -T db psql -U tony_erp tony_erp_prod
```

### التحديث

```bash
# تحديث من Git
./deploy.sh update

# أو يدوياً
git pull origin main
./deploy.sh restart
```

### أوامر Django

```bash
# Django Shell
./deploy.sh shell

# أي أمر manage.py
./deploy.sh manage migrate
./deploy.sh manage collectstatic
./deploy.sh manage createsuperuser
```

---

## 🔐 الأمان | Security

### قائمة التحقق الأمني

- [ ] تغيير `SECRET_KEY` إلى قيمة فريدة
- [ ] تعيين كلمة مرور قوية لقاعدة البيانات
- [ ] تفعيل HTTPS مع شهادة SSL صالحة
- [ ] إخفاء مسار لوحة التحكم (ADMIN_PATH)
- [ ] تقييد الوصول بالـ IP للوحة التحكم
- [ ] تفعيل Rate Limiting
- [ ] تحديث جميع الحزم بانتظام

### Firewall

```bash
# UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### تأمين Redis

Redis يعمل داخلياً فقط. لا تعرضه للإنترنت!

---

## 📈 المراقبة والأداء | Monitoring

### Sentry للأخطاء

1. أنشئ مشروع على [Sentry](https://sentry.io)
2. انسخ DSN
3. أضفه للبيئة

```env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### مراقبة الموارد

```bash
# استخدام الموارد
docker stats

# مساحة التخزين
docker system df

# تنظيف الموارد غير المستخدمة
docker system prune -f
```

---

## 🆘 استكشاف الأخطاء | Troubleshooting

### التطبيق لا يعمل

```bash
# التحقق من السجلات
./deploy.sh logs web

# إعادة البناء
docker compose -f deploy/docker-compose.prod.yml build --no-cache
./deploy.sh restart
```

### أخطاء قاعدة البيانات

```bash
# التحقق من الاتصال
./deploy.sh dbshell

# تشغيل الـ migrations
./deploy.sh manage migrate
```

### مشاكل SSL

```bash
# تجديد الشهادة
docker compose run --rm certbot renew

# التحقق من صلاحية الشهادة
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

### ذاكرة ممتلئة

```bash
# تنظيف Docker
docker system prune -af

# تنظيف السجلات
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

---

## 📞 الدعم | Support

للمساعدة التقنية:
- 📧 البريد: support@tonyerp.com
- 📱 الواتساب: +20xxxxxxxxx
- 📖 الوثائق: https://docs.tonyerp.com

---

**تم إنشاء هذا الدليل بواسطة Tony ERP Development Team**
**آخر تحديث: يناير 2026**
