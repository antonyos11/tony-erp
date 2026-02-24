# دليل المطور - متجر Tony ERP الإلكتروني
## Developer Guide - Tony ERP E-commerce

---

## 📋 جدول المحتويات

1. [نظرة عامة على المشروع](#project-overview)
2. [المتطلبات والتثبيت](#requirements)
3. [هيكل المشروع](#project-structure)
4. [قاعدة البيانات](#database)
5. [المصادقة والأمان](#authentication)
6. [نظام المدفوعات](#payment-system)
7. [نظام الإشعارات](#notifications)
8. [PWA والأداء](#pwa-performance)
9. [الاختبارات](#testing)
10. [النشر والإنتاج](#deployment)

---

## 🏗️ نظرة عامة على المشروع {#project-overview}

### التقنيات المستخدمة

| التقنية | الإصدار | الاستخدام |
|---------|---------|-----------|
| Django | 5.2.5 | Backend Framework |
| Django REST Framework | 3.14+ | API Development |
| PostgreSQL | 15+ | قاعدة البيانات |
| Redis | 7+ | Caching & Sessions |
| Celery | 5.3+ | Background Tasks |
| Bootstrap | 5.3.2 | Frontend CSS (RTL) |
| Web Push | 3.0+ | Push Notifications |

### بوابات الدفع المدعومة

- **Paymob**: بطاقات ائتمان، محافظ إلكترونية، تقسيط (ValU, Souhoola)
- **Fawry**: الدفع عند فروع فوري
- **InstaPay**: التحويلات البنكية الفورية
- **COD**: الدفع عند الاستلام

---

## ⚙️ المتطلبات والتثبيت {#requirements}

### متطلبات النظام

```bash
Python >= 3.11
PostgreSQL >= 15
Redis >= 7
Node.js >= 18 (للـ frontend build)
```

### التثبيت

```bash
# 1. استنساخ المشروع
git clone https://github.com/your-repo/tony_erp.git
cd tony_erp

# 2. إنشاء البيئة الافتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
.\venv\Scripts\activate  # Windows

# 3. تثبيت المتطلبات
pip install -r requirements.txt

# 4. إعداد ملف البيئة
cp .env.example .env
# عدّل الملف بإعداداتك

# 5. تشغيل الـ migrations
python manage.py migrate

# 6. إنشاء مستخدم إداري
python manage.py createsuperuser

# 7. تشغيل السيرفر
python manage.py runserver
```

### ملف .env

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/tony_erp

# Security
SECRET_KEY=your-secret-key-here
FERNET_KEYS=your-fernet-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Paymob
PAYMOB_API_KEY=your-api-key
PAYMOB_INTEGRATION_ID=123456
PAYMOB_IFRAME_ID=789012
PAYMOB_HMAC_SECRET=your-hmac-secret
PAYMOB_WALLET_INTEGRATION_ID=123457
PAYMOB_VALU_INTEGRATION_ID=123458

# Fawry
FAWRY_MERCHANT_CODE=your-merchant-code
FAWRY_SECURITY_KEY=your-security-key
FAWRY_SANDBOX=False

# Email
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Redis
REDIS_URL=redis://localhost:6379/0

# Push Notifications
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_ADMIN_EMAIL=admin@yourdomain.com
```

---

## 📁 هيكل المشروع {#project-structure}

```
tony_erp/
├── ecommerce/                    # تطبيق المتجر الإلكتروني
│   ├── models.py                 # نماذج البيانات
│   ├── api_views.py              # API ViewSets
│   ├── api_views_optimized.py    # Optimized API with caching
│   ├── api_urls.py               # API routes
│   ├── serializers.py            # DRF Serializers
│   ├── payment_integrations.py   # Paymob, Fawry integration
│   ├── payment_webhooks.py       # Webhook handlers
│   ├── email_service.py          # Email notifications
│   ├── push_notifications.py     # Push notification service
│   ├── permissions.py            # Custom permissions
│   ├── filters.py                # API filters
│   ├── templates/
│   │   └── ecommerce/
│   │       ├── store_base.html   # Base template with PWA
│   │       ├── emails/           # Email templates
│   │       └── offline.html      # Offline page
│   └── tests/                    # Test suite
│       ├── test_api_comprehensive.py
│       ├── test_payments.py
│       ├── test_integration.py
│       ├── test_e2e.py
│       ├── test_performance.py
│       └── test_security.py
│
├── static/
│   └── ecommerce/
│       ├── css/
│       │   ├── store.css         # Main store styles
│       │   ├── product-detail.css
│       │   ├── checkout.css
│       │   └── search-filters.css
│       ├── js/
│       │   ├── store.js          # Core functionality
│       │   ├── product-detail.js
│       │   ├── checkout.js       # 27 Egypt governorates
│       │   └── search-filters.js
│       ├── manifest.json         # PWA manifest
│       ├── sw.js                 # Service Worker
│       └── icons/                # PWA icons
│
├── docs/
│   ├── API_DOCUMENTATION.md      # API reference
│   └── DEVELOPER_GUIDE.md        # This file
│
├── manage.py
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

---

## 🗃️ قاعدة البيانات {#database}

### النماذج الرئيسية

```python
# ecommerce/models.py

class Product(models.Model):
    """منتج"""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_price = models.DecimalField(null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    # Indexes for performance
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
        ]


class Order(models.Model):
    """طلب"""
    STATUSES = [
        ('pending', 'قيد الانتظار'),
        ('confirmed', 'مؤكد'),
        ('processing', 'جاري التجهيز'),
        ('shipped', 'تم الشحن'),
        ('delivered', 'تم التوصيل'),
        ('cancelled', 'ملغي'),
        ('refunded', 'مسترد'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUSES)
    payment_status = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=50)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)


class PaymentTransaction(models.Model):
    """معاملة دفع"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    gateway = models.ForeignKey('PaymentGateway', on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict)  # Store gateway-specific data
```

### الـ Migrations

```bash
# إنشاء migrations جديدة
python manage.py makemigrations ecommerce

# تطبيق الـ migrations
python manage.py migrate

# عرض SQL للـ migration
python manage.py sqlmigrate ecommerce 0001
```

---

## 🔐 المصادقة والأمان {#authentication}

### JWT Authentication

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### Custom Permissions

```python
# ecommerce/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """السماح للمالك فقط بالتعديل"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsOrderOwner(permissions.BasePermission):
    """السماح لصاحب الطلب فقط"""
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

### تشفير البيانات الحساسة

```python
# استخدام Fernet للتشفير
from fernet_fields import EncryptedTextField

class PaymentGateway(models.Model):
    name = models.CharField(max_length=50)
    api_key_encrypted = EncryptedTextField()
    secret_key_encrypted = EncryptedTextField()
```

---

## 💳 نظام المدفوعات {#payment-system}

### Paymob Integration

```python
# ecommerce/payment_integrations.py

class PaymobPayment:
    """تكامل بوابة Paymob"""
    
    BASE_URL = 'https://accept.paymob.com/api'
    
    def __init__(self):
        self.api_key = settings.PAYMOB_API_KEY
        
    def authenticate(self):
        """الحصول على auth token"""
        response = requests.post(
            f'{self.BASE_URL}/auth/tokens',
            json={'api_key': self.api_key}
        )
        return response.json()['token']
    
    def create_order(self, auth_token, order):
        """تسجيل الطلب في Paymob"""
        response = requests.post(
            f'{self.BASE_URL}/ecommerce/orders',
            json={
                'auth_token': auth_token,
                'delivery_needed': 'false',
                'amount_cents': int(order.total * 100),
                'currency': 'EGP',
                'merchant_order_id': order.order_number,
                'items': self._format_items(order)
            }
        )
        return response.json()['id']
    
    def get_payment_key(self, auth_token, order_id, order):
        """الحصول على payment key"""
        response = requests.post(
            f'{self.BASE_URL}/acceptance/payment_keys',
            json={
                'auth_token': auth_token,
                'amount_cents': int(order.total * 100),
                'expiration': 3600,
                'order_id': order_id,
                'billing_data': self._get_billing_data(order),
                'currency': 'EGP',
                'integration_id': settings.PAYMOB_INTEGRATION_ID
            }
        )
        return response.json()['token']
```

### Webhook Handler

```python
# ecommerce/payment_webhooks.py

class PaymobWebhookView(APIView):
    """معالجة Paymob webhooks"""
    
    permission_classes = []
    
    def post(self, request):
        # التحقق من HMAC
        received_hmac = request.headers.get('Hmac')
        calculated_hmac = self._calculate_hmac(request.data)
        
        if not hmac.compare_digest(received_hmac, calculated_hmac):
            return Response({'error': 'Invalid signature'}, status=401)
        
        # معالجة البيانات
        obj = request.data.get('obj', {})
        order_id = obj.get('order', {}).get('merchant_order_id')
        
        if obj.get('success'):
            self._handle_success(order_id, obj)
        else:
            self._handle_failure(order_id, obj)
        
        return Response({'status': 'ok'})
```

---

## 🔔 نظام الإشعارات {#notifications}

### Push Notifications

```python
# ecommerce/push_notifications.py

class PushNotificationService:
    """خدمة الإشعارات الفورية"""
    
    def send_order_update(self, user, order, status):
        """إشعار تحديث الطلب"""
        messages = {
            'confirmed': f'تم تأكيد طلبك #{order.order_number}',
            'shipped': f'تم شحن طلبك #{order.order_number}',
            'delivered': f'تم توصيل طلبك #{order.order_number}',
        }
        
        subscriptions = PushSubscription.objects.filter(
            user=user,
            is_active=True
        )
        
        for sub in subscriptions:
            self._send_notification(sub, {
                'title': 'تحديث الطلب',
                'body': messages.get(status),
                'icon': '/static/icons/order.png',
                'url': f'/orders/{order.id}/'
            })
```

### Email Notifications

```python
# ecommerce/email_service.py

class EmailService:
    """خدمة البريد الإلكتروني"""
    
    def send_order_confirmation(self, order):
        """إرسال تأكيد الطلب"""
        context = {
            'order': order,
            'items': order.items.select_related('product'),
            'store_name': 'متجر Tony'
        }
        
        mail.send(
            recipients=[order.user.email],
            template='order_confirmation',
            context=context,
            priority='now'
        )
```

---

## ⚡ PWA والأداء {#pwa-performance}

### Service Worker

```javascript
// static/ecommerce/sw.js

const CACHE_NAME = 'tony-store-v2.0.0';
const STATIC_CACHE = 'tony-static-v2.0.0';
const DYNAMIC_CACHE = 'tony-dynamic-v2.0.0';

// Precache static assets
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/ecommerce/css/store.css',
    '/static/ecommerce/js/store.js',
    '/static/ecommerce/manifest.json'
];

// Cache strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // API requests: Network first
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
    }
    // Static assets: Cache first
    else if (request.destination === 'image' || 
             request.destination === 'style' ||
             request.destination === 'script') {
        event.respondWith(cacheFirst(request));
    }
    // HTML pages: Stale while revalidate
    else {
        event.respondWith(staleWhileRevalidate(request));
    }
});
```

### Performance Optimization

```python
# ecommerce/api_views_optimized.py

class OptimizedProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet محسّن للمنتجات"""
    
    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'brand'
        ).prefetch_related(
            'images', 'variants'
        ).filter(
            is_active=True
        ).only(
            'id', 'name', 'slug', 'price', 'compare_price',
            'stock', 'category_id', 'brand_id'
        )
    
    @method_decorator(cache_page(60 * 5))  # Cache 5 minutes
    def list(self, request):
        return super().list(request)
```

---

## 🧪 الاختبارات {#testing}

### تشغيل الاختبارات

```bash
# جميع الاختبارات
python manage.py test ecommerce.tests

# اختبارات محددة
python manage.py test ecommerce.tests.test_api_comprehensive
python manage.py test ecommerce.tests.test_payments
python manage.py test ecommerce.tests.test_security

# مع التغطية
pip install coverage
coverage run --source='ecommerce' manage.py test ecommerce.tests
coverage report
coverage html  # HTML report
```

### كتابة اختبار جديد

```python
# ecommerce/tests/test_example.py

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

class ProductAPITests(APITestCase):
    """اختبارات API المنتجات"""
    
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        cls.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=Decimal('100.00'),
            category=cls.category
        )
    
    def test_list_products(self):
        """اختبار قائمة المنتجات"""
        url = reverse('ecommerce_api:product-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
```

---

## 🚀 النشر والإنتاج {#deployment}

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "accountant_pro.wsgi"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tony_erp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=tony_erp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
  
  redis:
    image: redis:7-alpine
    
  celery:
    build: .
    command: celery -A accountant_pro worker -l info
    depends_on:
      - redis

volumes:
  postgres_data:
```

### Production Checklist

- [ ] `DEBUG = False`
- [ ] `ALLOWED_HOSTS` configured
- [ ] `SECRET_KEY` is unique and secret
- [ ] HTTPS enabled
- [ ] Database backups configured
- [ ] Static files served via CDN
- [ ] Logging configured
- [ ] Error monitoring (Sentry)
- [ ] Rate limiting enabled
- [ ] CORS configured properly

---

## 📞 الدعم

- 📧 dev-support@tonyerp.com
- 📖 https://docs.tonyerp.com
- 💬 Slack: #tony-erp-dev

---

**آخر تحديث:** يناير 2026
**الإصدار:** 2.0.0
