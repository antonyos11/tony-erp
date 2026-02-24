# نظام المراقبة - Tony ERP Monitoring

## نظرة عامة

تم إضافة نظام مراقبة متكامل لـ Tony ERP باستخدام **Prometheus** و **Grafana**.

## المكونات

### 1. Prometheus
- **الوظيفة**: جمع وتخزين metrics من التطبيق
- **المنفذ**: 9090
- **الوصول**: http://localhost:9090

### 2. Grafana
- **الوظيفة**: لوحات معلومات مرئية وتقارير
- **المنفذ**: 3000
- **الوصول**: http://localhost:3000
- **المستخدم الافتراضي**: admin
- **كلمة المرور الافتراضية**: admin123

### 3. Django Prometheus
- **الوظيفة**: تصدير metrics من Django
- **Endpoint**: http://localhost:8000/metrics

## التشغيل

### تشغيل نظام المراقبة كامل:

```bash
docker-compose --profile monitoring up -d
```

### تشغيل بدون المراقبة:

```bash
docker-compose up -d
```

## المقاييس المتاحة (Metrics)

### 1. Django Metrics
- **HTTP Requests**: عدد وزمن الطلبات
- **Response Times**: زمن الاستجابة لكل endpoint
- **Status Codes**: توزيع أكواد الاستجابة (200, 404, 500, إلخ)
- **Database Queries**: عدد وزمن استعلامات قاعدة البيانات
- **Cache Hits/Misses**: فعالية الـ cache
- **Exceptions**: الأخطاء والاستثناءات

### 2. System Metrics
- **CPU Usage**: استخدام المعالج
- **Memory Usage**: استخدام الذاكرة
- **Disk I/O**: عمليات القراءة والكتابة
- **Network Traffic**: حركة الشبكة

### 3. Business Metrics
يمكن إضافة مقاييس خاصة بالعمل مثل:
- عدد المبيعات اليومية
- قيمة الطلبات
- عدد المستخدمين النشطين
- معدلات التحويل

## لوحات المعلومات الجاهزة

### Dashboard 1: System Overview
- نظرة عامة على صحة النظام
- استخدام الموارد (CPU, Memory, Disk)
- عدد الطلبات النشطة

### Dashboard 2: Application Performance
- زمن الاستجابة لكل endpoint
- معدلات الأخطاء
- استخدام قاعدة البيانات

### Dashboard 3: Business KPIs
- المبيعات والإيرادات
- المستخدمين النشطين
- الطلبات والفواتير

## إضافة Metrics مخصصة

### مثال: تتبع عدد المبيعات

```python
from prometheus_client import Counter

sales_counter = Counter(
    'tony_erp_sales_total',
    'Total number of sales',
    ['payment_method', 'customer_type']
)

# في view المبيعات
def create_sale(request):
    # ... إنشاء البيع
    sales_counter.labels(
        payment_method='cash',
        customer_type='retail'
    ).inc()
    # ...
```

### مثال: قياس زمن العمليات

```python
from prometheus_client import Histogram

processing_time = Histogram(
    'tony_erp_processing_seconds',
    'Time spent processing request',
    ['operation']
)

@processing_time.labels(operation='invoice_generation').time()
def generate_invoice(data):
    # ... منطق إنشاء الفاتورة
    pass
```

## التنبيهات (Alerts)

يمكن إضافة تنبيهات في `monitoring/alerts.yml`:

```yaml
groups:
  - name: tony_erp_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total_by_status_total{status="500"}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighResponseTime
        expr: django_http_request_duration_seconds_sum / django_http_request_duration_seconds_count > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time"
          description: "Average response time is {{ $value }} seconds"
```

## الصيانة

### تنظيف البيانات القديمة

Prometheus يحتفظ بالبيانات لمدة 15 يوم افتراضياً. لتغيير المدة:

```yaml
# في docker-compose.yml
command:
  - '--storage.tsdb.retention.time=30d'
```

### النسخ الاحتياطي

```bash
# نسخ احتياطي لبيانات Prometheus
docker run --rm -v tony_erp_prometheus_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/prometheus_backup.tar.gz -C /data .

# نسخ احتياطي لبيانات Grafana
docker run --rm -v tony_erp_grafana_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/grafana_backup.tar.gz -C /data .
```

## الموارد المفيدة

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [django-prometheus Documentation](https://github.com/korfuri/django-prometheus)

## الدعم

للمساعدة أو الاستفسارات، راجع التوثيق الرئيسي أو تواصل مع فريق التطوير.
