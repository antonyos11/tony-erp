# اختبار الأداء تحت الحمل - Tony ERP Load Testing

## نظرة عامة

نظام اختبار الأداء تحت الحمل لـ Tony ERP باستخدام **Locust** - أداة مفتوحة المصدر لاختبار الأداء.

## المتطلبات

```bash
pip install locust
```

أو تثبيت من `requirements.txt`:
```bash
pip install -r requirements.txt
```

## أنواع المستخدمين

### 1. AuthenticatedUser (60%)
المستخدم العادي الذي يتصفح النظام:
- لوحة التحكم
- قوائم المبيعات والمخزون
- التقارير الأساسية

### 2. APIUser (25%)
مستخدم يستخدم API:
- استعلامات REST API
- JWT authentication
- عمليات CRUD عبر API

### 3. HeavyOperationsUser (10%)
مستخدم يقوم بعمليات ثقيلة:
- إنشاء تقارير معقدة
- تصدير إلى Excel/PDF
- القوائم المالية

### 4. SequentialUser (5%)
مستخدم ينفذ إجراءات متسلسلة:
- تدفقات عمل محددة
- سيناريوهات واقعية

## طرق التشغيل

### 1. التشغيل البسيط

```bash
# Linux/Mac
./load_tests/run_load_test.sh

# Windows
load_tests\run_load_test.bat
```

### 2. التشغيل بواجهة الويب

```bash
locust -f load_tests/locustfile.py --host=http://localhost:8000
```

ثم افتح: http://localhost:8089

### 3. التشغيل Headless (بدون واجهة)

```bash
locust -f load_tests/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless \
    --html=report.html
```

### 4. سيناريوهات محددة

#### اختبار خفيف (Development)
```bash
locust -f load_tests/locustfile.py \
    --host=http://localhost:8000 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 2m \
    --headless
```

#### اختبار متوسط (Staging)
```bash
locust -f load_tests/locustfile.py \
    --host=http://staging.tony-erp.com \
    --users 50 \
    --spawn-rate 5 \
    --run-time 5m \
    --headless
```

#### اختبار ثقيل (Production Simulation)
```bash
locust -f load_tests/locustfile.py \
    --host=http://localhost:8000 \
    --users 200 \
    --spawn-rate 10 \
    --run-time 15m \
    --headless \
    --html=load_tests/results/production_test.html
```

## تفسير النتائج

### Metrics المهمة

#### 1. Response Time
- **P50 (Median)**: نصف الطلبات أسرع من هذا الوقت
- **P95**: 95% من الطلبات أسرع من هذا الوقت
- **P99**: 99% من الطلبات أسرع من هذا الوقت

**الهدف المثالي:**
- P50 < 200ms
- P95 < 1000ms
- P99 < 2000ms

#### 2. Requests per Second (RPS)
عدد الطلبات في الثانية. كلما زاد كان أفضل.

**الهدف المثالي:**
- Development: 100+ RPS
- Production: 500+ RPS

#### 3. Failure Rate
نسبة الطلبات الفاشلة.

**الهدف المثالي:**
- < 0.1% في الظروف العادية
- < 1% تحت حمل شديد

### مثال على نتائج جيدة

```
Type     Name                          # reqs  # fails  Avg   Min   Max  Median  req/s
------------------------------------------------------------------------
GET      /dashboard/                    5000      0    120    50   800    110    83.3
GET      /sales/                        3000      0    180    80  1200    150    50.0
GET      /inventory/products/           3000      0    200   100  1500    180    50.0
POST     /api/reports/overview/         1500      0    350   150  2000    300    25.0
------------------------------------------------------------------------
Aggregated                             12500      0    180    50  2000    150   208.3
```

## التحليل والتحسين

### إذا كانت Response Times عالية:

1. **فحص Database Queries**
   ```bash
   # تفعيل Django Debug Toolbar
   # فحص عدد الاستعلامات وزمنها
   ```

2. **تفعيل Caching**
   ```python
   # في settings.py
   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
       }
   }
   ```

3. **فحص N+1 Queries**
   ```python
   # استخدام select_related و prefetch_related
   products = Product.objects.select_related('category').all()
   ```

### إذا كانت Failure Rate عالية:

1. **فحص Logs**
   ```bash
   tail -f logs/app.log
   tail -f logs/errors.log
   ```

2. **زيادة Workers**
   ```bash
   # في gunicorn
   gunicorn --workers 4 --threads 2 accountant_pro.wsgi
   ```

3. **تحسين Database Connections**
   ```python
   # في settings.py
   DATABASES = {
       'default': {
           'CONN_MAX_AGE': 600,
       }
   }
   ```

## أفضل الممارسات

### 1. الاختبار التدريجي
```bash
# ابدأ بـ 10 users
locust --users 10 --spawn-rate 2

# ثم زيادة تدريجية
# 50 users -> 100 users -> 200 users
```

### 2. الاختبار في بيئة مشابهة
- نفس المواصفات التقنية
- نفس حجم قاعدة البيانات
- نفس الشبكة

### 3. المراقبة أثناء الاختبار
```bash
# مراقبة CPU و Memory
htop

# مراقبة Database
pg_top

# مراقبة Redis
redis-cli --stat
```

### 4. توثيق النتائج
احفظ النتائج لكل اختبار للمقارنة:
```bash
# تسمية ذات معنى
report_v1.0_50users_5min.html
report_v1.1_50users_5min.html  # بعد التحسينات
```

## الأتمتة مع CI/CD

### مثال GitHub Actions

```yaml
name: Load Testing

on:
  schedule:
    - cron: '0 2 * * 0'  # أسبوعياً يوم الأحد 2 صباحاً

jobs:
  load_test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install locust
      - name: Run load test
        run: |
          locust -f load_tests/locustfile.py \
            --host=${{ secrets.STAGING_URL }} \
            --users 50 \
            --spawn-rate 5 \
            --run-time 5m \
            --headless \
            --html=report.html
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: load-test-report
          path: report.html
```

## استكشاف الأخطاء

### مشكلة: Connection Errors

```bash
# زيادة open files limit
ulimit -n 10000

# تحقق من الاتصال
curl -I http://localhost:8000
```

### مشكلة: Too Many Requests (429)

```python
# تعديل Rate Limiting في settings.py
RATELIMIT_ENABLE = False  # للاختبار فقط
```

### مشكلة: Out of Memory

```bash
# زيادة Swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## الموارد المفيدة

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://docs.locust.io/en/stable/testing-other-systems.html)
- [Django Performance Tips](https://docs.djangoproject.com/en/stable/topics/performance/)

## الدعم

للمساعدة أو الاستفسارات، راجع التوثيق الرئيسي أو تواصل مع فريق التطوير.
