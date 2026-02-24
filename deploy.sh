#!/bin/bash
# ============================================================
# Tony ERP - Production Deployment Script
# ============================================================
set -e

echo "============================================================"
echo "  Tony ERP - Production Deployment"
echo "============================================================"

# ============================================================
# 1. Check .env file
# ============================================================
echo ""
echo "[1/7] Checking environment..."

if [ ! -f .env ]; then
    echo "[!] .env file not found!"
    echo "    Copy from template: cp .env.example .env"
    echo "    Then update values."
    exit 1
fi
echo "  [OK] .env file exists"

# Load environment variables
set -a
source .env
set +a

# Validate critical variables
if [ -z "$DJANGO_SECRET_KEY" ] || [ "$DJANGO_SECRET_KEY" = "your-secret-key-here-change-this-immediately" ]; then
    echo "[!] DJANGO_SECRET_KEY not configured!"
    echo "    Generate one: python manage.py setup_production --generate-secret-key"
    exit 1
fi
echo "  [OK] SECRET_KEY configured"

# ============================================================
# 2. Install dependencies
# ============================================================
echo ""
echo "[2/7] Installing dependencies..."
pip install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt
echo "  [OK] Dependencies installed"

# ============================================================
# 3. Create required directories
# ============================================================
echo ""
echo "[3/7] Creating directories..."
mkdir -p logs media staticfiles backups
echo "  [OK] Directories ready"

# ============================================================
# 4. Database migrations
# ============================================================
echo ""
echo "[4/7] Running database migrations..."

SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-accountant_pro.settings}"
python manage.py migrate --settings="$SETTINGS_MODULE" --noinput
echo "  [OK] Migrations applied"

# ============================================================
# 5. Collect static files
# ============================================================
echo ""
echo "[5/7] Collecting static files..."
python manage.py collectstatic --settings="$SETTINGS_MODULE" --noinput --clear 2>/dev/null || \
python manage.py collectstatic --settings="$SETTINGS_MODULE" --noinput
echo "  [OK] Static files collected"

# ============================================================
# 6. System checks
# ============================================================
echo ""
echo "[6/7] Running system checks..."
python manage.py setup_production --check --settings="$SETTINGS_MODULE" || true
echo ""
python manage.py check --settings="$SETTINGS_MODULE" 2>/dev/null || true

# ============================================================
# 7. Check for admin user
# ============================================================
echo ""
echo "[7/7] Checking admin user..."
python manage.py shell --settings="$SETTINGS_MODULE" -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('  [!] No admin user found!')
    print('      Create one: python manage.py createsuperuser')
else:
    count = User.objects.filter(is_superuser=True).count()
    print(f'  [OK] {count} admin user(s) exist')
"

# ============================================================
# Done
# ============================================================
echo ""
echo "============================================================"
echo "  Deployment complete!"
echo "============================================================"
echo ""
echo "  Start server:"
echo "    gunicorn accountant_pro.wsgi:application --bind 0.0.0.0:8000"
echo ""
echo "  Or with Docker:"
echo "    docker-compose -f docker-compose.production.yml up -d"
echo ""
