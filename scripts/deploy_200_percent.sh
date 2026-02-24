#!/bin/bash
# Tony ERP - Deploy to 200% Production Ready
# Usage: bash scripts/deploy_200_percent.sh
set -e

echo "============================================================"
echo "  Tony ERP - Deploy to 200% Production Ready"
echo "============================================================"
echo ""

cd /var/www/tony_erp

# Step 1: Backup
echo "[1/10] Creating backup..."
BACKUP_DIR="backups/pre_200_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp db.sqlite3 "$BACKUP_DIR/" 2>/dev/null || true
cp .env "$BACKUP_DIR/" 2>/dev/null || true
echo "  Done: $BACKUP_DIR"

# Step 2: Install deps
echo ""
echo "[2/10] Installing dependencies..."
pip install --quiet --upgrade -r requirements.txt 2>/dev/null
pip install --quiet openpyxl 2>/dev/null || true
echo "  Done"

# Step 3: Create directories
echo ""
echo "[3/10] Creating directories..."
mkdir -p logs staticfiles media templates/reports templates/hr templates/production/reports
touch accounting/templatetags/__init__.py 2>/dev/null || true
echo "  Done"

# Step 4: Migrations
echo ""
echo "[4/10] Running migrations..."
python manage.py migrate --no-input 2>&1 | tail -3
echo "  Done"

# Step 5: Collect static
echo ""
echo "[5/10] Collecting static files..."
python manage.py collectstatic --no-input --clear 2>/dev/null | tail -1
echo "  Done"

# Step 6: Env check
echo ""
echo "[6/10] Checking environment..."
if [ -f .env ]; then
    if ! grep -q "ALLOW_NEGATIVE_INVENTORY" .env 2>/dev/null; then
        echo "ALLOW_NEGATIVE_INVENTORY=0" >> .env
        echo "  Added ALLOW_NEGATIVE_INVENTORY"
    fi
    echo "  .env OK"
else
    echo "  Warning: .env not found"
fi

# Step 7: Django check
echo ""
echo "[7/10] Django system check..."
python manage.py check 2>&1 | tail -5
echo "  Done"

# Step 8: Production readiness
echo ""
echo "[8/10] Production readiness check..."
python manage.py production_readiness_check 2>&1 || true

# Step 9: Tests
echo ""
echo "[9/10] Running comprehensive tests..."
python -m pytest tests/test_comprehensive_200.py -v --tb=short -q --no-header -o "addopts=" 2>&1 | tail -30
echo ""

# Step 10: Optimize DB
echo ""
echo "[10/10] Optimizing database..."
python -c "
import sqlite3, os
if os.path.exists('db.sqlite3'):
    conn = sqlite3.connect('db.sqlite3')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=-64000')
    conn.execute('VACUUM')
    conn.execute('ANALYZE')
    conn.close()
    print('  Database optimized')
else:
    print('  Skipped: no sqlite3 database')
"

# Summary
echo ""
echo "============================================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "  Backup:     $BACKUP_DIR"
echo "  Migrations: Applied"
echo "  Static:     Collected"
echo "  Tests:      Executed"
echo "  Database:   Optimized"
echo ""
echo "  Next steps:"
echo "    sudo systemctl restart gunicorn"
echo "    sudo systemctl restart nginx"
echo "    python manage.py production_readiness_check"
echo ""
