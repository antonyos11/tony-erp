# Tony ERP - Makefile
# اختصارات سريعة للأوامر الشائعة

.PHONY: help install run test migrate makemigrations shell clean backup restore format lint docker-up docker-down load-test monitoring smoke-test health p1-tests p1-tests-cov

# الأمر الافتراضي - عرض المساعدة
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Tony ERP - اختصارات الأوامر السريعة"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "التطوير:"
	@echo "  make run          - تشغيل الخادم"
	@echo "  make shell        - فتح Django shell"
	@echo "  make migrate      - تطبيق المهاجرات"
	@echo "  make makemigrations - إنشاء مهاجرات جديدة"
	@echo "  make createsuperuser - إنشاء مستخدم admin"
	@echo ""
	@echo "الاختبار:"
	@echo "  make test         - تشغيل جميع الاختبارات"
	@echo "  make test-fast    - اختبارات سريعة (بدون coverage)"
	@echo "  make test-verbose - اختبارات مفصلة"
	@echo "  make coverage     - تقرير التغطية"
	@echo "  make load-test    - اختبار الأداء"
	@echo ""
	@echo "جودة الكود:"
	@echo "  make format       - تنسيق الكود (black + isort)"
	@echo "  make lint         - فحص الكود (flake8 + mypy)"
	@echo "  make check        - فحص Django + migrations"
	@echo ""
	@echo "قاعدة البيانات:"
	@echo "  make backup       - نسخة احتياطية"
	@echo "  make restore      - استعادة من نسخة احتياطية"
	@echo "  make reset-db     - إعادة تعيين قاعدة البيانات"
	@echo "  make seed-data    - إضافة بيانات تجريبية"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - تشغيل Docker"
	@echo "  make docker-down  - إيقاف Docker"
	@echo "  make docker-logs  - عرض السجلات"
	@echo "  make docker-build - بناء الصور"
	@echo ""
	@echo "المراقبة:"
	@echo "  make monitoring   - تشغيل Prometheus + Grafana"
	@echo "  make metrics      - عرض المقاييس"
	@echo ""
	@echo "التنظيف:"
	@echo "  make clean        - تنظيف الملفات المؤقتة"
	@echo "  make clean-pyc    - حذف ملفات .pyc"
	@echo "  make clean-logs   - تنظيف السجلات"
	@echo ""

# التثبيت والإعداد
install:
	@echo "🔧 تثبيت المتطلبات..."
	pip install -r requirements.txt
	@echo "✅ تم التثبيت بنجاح"

install-dev:
	@echo "🔧 تثبيت أدوات التطوير..."
	pip install -r requirements.txt
	pip install black isort flake8 mypy pylint pre-commit
	pre-commit install
	@echo "✅ تم تثبيت أدوات التطوير"

# التشغيل
run:
	@echo "🚀 تشغيل الخادم..."
	python manage.py runserver

run-network:
	@echo "🌐 تشغيل الخادم على الشبكة..."
	python start_network_server.py

# الهجرات
migrate:
	@echo "📦 تطبيق المهاجرات..."
	python manage.py migrate

makemigrations:
	@echo "📝 إنشاء مهاجرات جديدة..."
	python manage.py makemigrations

showmigrations:
	@echo "📋 عرض حالة المهاجرات..."
	python manage.py showmigrations

# Django Shell
shell:
	@echo "🐚 فتح Django shell..."
	python manage.py shell_plus

shell-basic:
	@echo "🐚 فتح Django shell..."
	python manage.py shell

# المستخدمون
createsuperuser:
	@echo "👤 إنشاء مستخدم admin..."
	python manage.py createsuperuser

# الاختبارات
test:
	@echo "🧪 تشغيل الاختبارات مع التغطية..."
	pytest --cov=. --cov-report=html --cov-report=term

test-fast:
	@echo "⚡ اختبارات سريعة..."
	pytest --no-cov -x

test-verbose:
	@echo "🔍 اختبارات مفصلة..."
	pytest -vv --tb=short

test-failed:
	@echo "🔴 إعادة الاختبارات الفاشلة..."
	pytest --lf

coverage:
	@echo "📊 تقرير التغطية..."
	coverage report
	coverage html
	@echo "✅ التقرير في: htmlcov/index.html"

# اختبار الأداء
load-test:
	@echo "🚀 اختبار الأداء..."
	./load_tests/run_load_test.sh

load-test-light:
	@echo "⚡ اختبار خفيف..."
	locust -f load_tests/locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 2m --headless

# جودة الكود
format:
	@echo "🎨 تنسيق الكود..."
	black . --exclude="/(\.git|\.venv|venv|migrations|node_modules)/"
	isort . --skip-glob="*/migrations/*" --skip-glob="venv/*"
	@echo "✅ تم التنسيق"

lint:
	@echo "🔍 فحص الكود..."
	flake8 . --exclude=migrations,venv,.venv,node_modules --max-line-length=120
	@echo "✅ لا توجد أخطاء"

check:
	@echo "✅ فحص Django..."
	python manage.py check
	python manage.py makemigrations --check --dry-run

# قاعدة البيانات
backup:
	@echo "💾 إنشاء نسخة احتياطية..."
	python backup_manager.py

restore:
	@echo "♻️  استعادة من نسخة احتياطية..."
	@echo "قائمة النسخ المتاحة:"
	@ls -lh backups/*.sql 2>/dev/null || echo "لا توجد نسخ احتياطية"

reset-db:
	@echo "⚠️  إعادة تعيين قاعدة البيانات..."
	@read -p "هل أنت متأكد؟ (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	rm -f db.sqlite3
	python manage.py migrate
	@echo "✅ تم إعادة التعيين"

seed-data:
	@echo "🌱 إضافة بيانات تجريبية..."
	python create_sample_data.py

# Docker
docker-up:
	@echo "🐳 تشغيل Docker..."
	docker-compose up -d

docker-down:
	@echo "🛑 إيقاف Docker..."
	docker-compose down

docker-logs:
	@echo "📜 عرض السجلات..."
	docker-compose logs -f

docker-build:
	@echo "🔨 بناء الصور..."
	docker-compose build

docker-restart:
	@echo "🔄 إعادة تشغيل Docker..."
	docker-compose restart

# المراقبة
monitoring:
	@echo "📊 تشغيل نظام المراقبة..."
	docker-compose --profile monitoring up -d
	@echo "✅ Grafana: http://localhost:3000"
	@echo "✅ Prometheus: http://localhost:9090"

metrics:
	@echo "📈 عرض المقاييس..."
	@curl -s http://localhost:8000/metrics | head -20

# التنظيف
clean:
	@echo "🧹 تنظيف الملفات المؤقتة..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "✅ تم التنظيف"

clean-pyc:
	@echo "🧹 حذف ملفات .pyc..."
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ تم الحذف"

clean-logs:
	@echo "🧹 تنظيف السجلات..."
	find logs/ -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ تم التنظيف"

# الملفات الثابتة
collectstatic:
	@echo "📦 جمع الملفات الثابتة..."
	python manage.py collectstatic --noinput

# التحديث
update:
	@echo "🔄 تحديث المتطلبات..."
	pip install --upgrade -r requirements.txt
	python manage.py migrate
	python manage.py collectstatic --noinput
	@echo "✅ تم التحديث"

# الفحص والاختبارات السريعة
smoke-test:
	@echo "🔥 تشغيل Smoke Tests..."
	python manage.py smoke_test

health:
	@echo "🏥 فحص صحة النظام..."
	python manage.py health_check

health-json:
	@echo "🏥 فحص صحة النظام (JSON)..."
	python manage.py health_check --json

p1-tests:
	@echo "🚀 تشغيل اختبارات P1..."
	python manage.py run_p1_tests

p1-tests-cov:
	@echo "🚀 تشغيل اختبارات P1 مع Coverage..."
	python manage.py run_p1_tests --coverage

# معلومات النظام
info:
	@echo "ℹ️  معلومات النظام:"
	@echo "Python: $$(python --version)"
	@echo "Django: $$(python -c 'import django; print(django.get_version())')"
	@echo "Database: $$(python manage.py showmigrations | grep -c '\[X\]') migrations applied"
	@echo "Users: $$(python manage.py shell -c 'from django.contrib.auth import get_user_model; print(get_user_model().objects.count())')"

# فحص شامل للنظام
system-check:
	@echo "🔍 فحص شامل للنظام..."
	python3 manage.py system_check

# تجهيز الإنتاج
prepare-prod:
	@echo "🚀 فحص جاهزية الإنتاج..."
	python3 tools/prepare_production.py

# تنظيف المستندات المكررة (معاينة)
clean-docs:
	@echo "📄 تحليل المستندات المكررة..."
	python3 tools/cleanup_docs.py

# تنظيف المستندات المكررة (تنفيذ فعلي)
clean-docs-execute:
	@echo "🔴 تنظيف المستندات المكررة (تنفيذ)..."
	python3 tools/cleanup_docs.py --execute

# تقرير التطبيقات
apps-report:
	@echo "📊 تقرير التطبيقات..."
	python3 manage.py apps_report

# فحص صحي موسّع
health-extended:
	@echo "🏥 فحص صحي موسّع..."
	python3 manage.py health_check_extended

# ============================================================
# Production & Readiness (جاهزية الإنتاج)
# ============================================================

# إعداد سريع
quick-start:
	@echo "🚀 بدء سريع..."
	bash quick_start.sh

# فحص جاهزية الإنتاج
prod-check:
	@echo "🔍 فحص جاهزية الإنتاج..."
	python3 manage.py setup_production --check

# اختبارات الجاهزية
test-ready:
	@echo "✅ اختبارات جاهزية النظام..."
	pytest tests/test_system_ready.py tests/test_api_auth.py tests/test_api_endpoints.py -v -o "addopts="

# اختبار المصادقة فقط
test-auth:
	@echo "🔐 اختبارات المصادقة..."
	pytest tests/test_api_auth.py -v -o "addopts="

# نشر الإنتاج عبر Docker
prod-deploy:
	@echo "🚀 نشر الإنتاج..."
	docker-compose -f docker-compose.production.yml up --build -d
	@echo "✅ تم النشر بنجاح"

# إيقاف الإنتاج
prod-down:
	@echo "🛑 إيقاف بيئة الإنتاج..."
	docker-compose -f docker-compose.production.yml down

# سجلات الإنتاج
prod-logs:
	@echo "📜 سجلات الإنتاج..."
	docker-compose -f docker-compose.production.yml logs -f --tail=100

# فحص شامل (check + tests + prod-check)
full-check:
	@echo "🔍 فحص شامل للنظام..."
	python3 manage.py check
	pytest tests/test_system_ready.py tests/test_api_auth.py tests/test_api_endpoints.py -v -o "addopts="
	python3 manage.py setup_production --check
	@echo "✅ اكتمل الفحص الشامل"

# ============================================================
# 200% Production Ready Commands
# ============================================================

# نشر 200%
deploy-200:
	@echo "🚀 نشر لجاهزية 200%..."
	bash scripts/deploy_200_percent.sh

# فحص جاهزية الإنتاج الشامل
readiness-check:
	@echo "🔍 فحص الجاهزية الشامل..."
	python3 manage.py production_readiness_check

# فحص جاهزية الإنتاج (JSON)
readiness-check-json:
	python3 manage.py production_readiness_check --json

# اختبارات 200%
test-200:
	@echo "🧪 اختبارات 200%..."
	pytest tests/test_comprehensive_200.py -v --tb=short -o "addopts="

# اختبارات شاملة مع تغطية
test-full-coverage:
	@echo "📊 اختبارات شاملة مع تغطية..."
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html -o "addopts="

# فحص أمان شامل
security-audit:
	@echo "🛡️ فحص أمان شامل..."
	python3 manage.py check --deploy
	pytest tests/test_comprehensive_200.py::TestAuthenticationSecurity -v -o "addopts="


