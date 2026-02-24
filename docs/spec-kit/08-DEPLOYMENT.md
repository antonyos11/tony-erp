# 🚀 08 - النشر والتشغيل

## 📋 نظرة عامة

يدعم النظام عدة بيئات نشر من التطوير المحلي إلى الإنتاج السحابي.

---

## 🖥️ بيئات التشغيل

```
┌─────────────────────────────────────────────────────────────┐
│                      Development                             │
│              (Local Machine / VS Code)                       │
├─────────────────────────────────────────────────────────────┤
│                        Testing                               │
│              (Docker Compose / CI/CD)                        │
├─────────────────────────────────────────────────────────────┤
│                        Staging                               │
│              (Cloud VM / Kubernetes)                         │
├─────────────────────────────────────────────────────────────┤
│                       Production                             │
│       (Kubernetes / Docker Swarm / Cloud Services)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 التشغيل المحلي

### 1. المتطلبات

```bash
# Python 3.11+
python --version

# pip
pip --version

# Git
git --version
```

### 2. الإعداد

```bash
# استنساخ المشروع
git clone https://github.com/user/tony-erp.git
cd tony-erp

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
.\venv\Scripts\activate   # Windows

# تثبيت المتطلبات
pip install -r requirements.txt

# نسخ ملف البيئة
cp .env.example .env
# تحرير .env وإضافة المتغيرات المطلوبة

# تهيئة قاعدة البيانات
python manage.py migrate

# إنشاء مستخدم إداري
python manage.py createsuperuser

# تجميع الملفات الثابتة
python manage.py collectstatic

# تشغيل الخادم
python manage.py runserver
```

### 3. التشغيل السريع (Windows)

```batch
# انقر نقراً مزدوجاً على:
start_server.bat

# أو للتشغيل المتقدم:
start_advanced.bat
```

### 4. التشغيل السريع (Linux/Mac)

```bash
chmod +x start_server.sh
./start_server.sh
```

---

## 🐳 Docker

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=0
      - DATABASE_URL=postgres://user:pass@db:5432/tony_erp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=tony_erp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A accountant_pro worker -l INFO
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/tony_erp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A accountant_pro beat -l INFO
    depends_on:
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - web

  flower:
    build: .
    command: celery -A accountant_pro flower
    ports:
      - "5555:5555"
    depends_on:
      - celery

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### أوامر Docker

```bash
# بناء وتشغيل
docker-compose up -d --build

# عرض السجلات
docker-compose logs -f web

# تنفيذ أمر
docker-compose exec web python manage.py migrate

# إيقاف
docker-compose down

# إيقاف مع حذف البيانات
docker-compose down -v
```

---

## ☸️ Kubernetes

### هيكل الملفات

```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── deployment.yaml
├── service.yaml
├── ingress.yaml
├── hpa.yaml
└── pvc.yaml
```

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tony-erp
  namespace: tony-erp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tony-erp
  template:
    metadata:
      labels:
        app: tony-erp
    spec:
      containers:
      - name: web
        image: tony-erp:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: tony-erp-config
        - secretRef:
            name: tony-erp-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: tony-erp
  namespace: tony-erp
spec:
  selector:
    app: tony-erp
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### ingress.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tony-erp
  namespace: tony-erp
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - erp.domain.com
    secretName: tony-erp-tls
  rules:
  - host: erp.domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tony-erp
            port:
              number: 80
```

### أوامر Kubernetes

```bash
# تطبيق الإعدادات
kubectl apply -f k8s/

# عرض الـ Pods
kubectl get pods -n tony-erp

# عرض السجلات
kubectl logs -f deployment/tony-erp -n tony-erp

# تنفيذ أمر
kubectl exec -it deployment/tony-erp -n tony-erp -- python manage.py migrate

# تحديث الصورة
kubectl set image deployment/tony-erp web=tony-erp:v2 -n tony-erp
```

---

## ⚙️ إعدادات الإنتاج

### .env للإنتاج

```bash
# Django
DEBUG=0
DJANGO_SECRET_KEY=your-very-long-and-secure-secret-key
ALLOWED_HOSTS=erp.domain.com,www.erp.domain.com
ENVIRONMENT=production

# Database
DATABASE_URL=postgres://user:password@db-host:5432/tony_erp

# Redis
REDIS_URL=redis://redis-host:6379/0

# Security
SECURE_SSL_REDIRECT=1
CSRF_COOKIE_SECURE=1
SESSION_COOKIE_SECURE=1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=noreply@domain.com
EMAIL_HOST_PASSWORD=app-password

# Storage
AWS_S3_BUCKET=tony-erp-media
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### settings_production.py

```python
from .settings import *

DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/tony-erp/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

---

## 📊 Nginx Configuration

```nginx
upstream tony_erp {
    server web:8000;
}

server {
    listen 80;
    server_name erp.domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name erp.domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    client_max_body_size 100M;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://tony_erp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://tony_erp;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 🔍 Health Checks

### Endpoints

| Endpoint | الوصف |
|----------|-------|
| `/health/` | فحص صحة التطبيق |
| `/health/ready/` | جاهزية التطبيق |
| `/health/live/` | حياة التطبيق |
| `/health/db/` | اتصال قاعدة البيانات |
| `/health/cache/` | اتصال Redis |

### health_check.sh

```bash
#!/bin/bash
curl -f http://localhost:8000/health/ || exit 1
```

---

## 📈 Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tony-erp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tony-erp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 🔄 CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python manage.py test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /var/www/tony_erp
            git pull
            source venv/bin/activate
            pip install -r requirements.txt
            python manage.py migrate
            python manage.py collectstatic --noinput
            sudo systemctl restart tony-erp
```

---

## 📝 Makefile

```makefile
.PHONY: install migrate run test deploy

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

run:
	python manage.py runserver

test:
	python manage.py test

collectstatic:
	python manage.py collectstatic --noinput

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

deploy:
	git pull
	make install
	make migrate
	make collectstatic
	sudo systemctl restart tony-erp
```

---

*الوثيقة التالية: [09-DEPENDENCIES.md](09-DEPENDENCIES.md)*
