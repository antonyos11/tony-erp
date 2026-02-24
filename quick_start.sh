#!/usr/bin/env bash
# =============================================================
# Tony ERP - Quick Start Script
# بدء سريع للنظام
# =============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

echo "============================================="
echo "  Tony ERP - Quick Start"
echo "============================================="
echo ""

# -----------------------------------------------------------
# 1. Check Python
# -----------------------------------------------------------
info "Checking Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    err "Python not found. Please install Python 3.10+."
    exit 1
fi
PY_VER=$($PY --version 2>&1)
ok "Found $PY_VER"

# -----------------------------------------------------------
# 2. Check .env
# -----------------------------------------------------------
info "Checking .env file..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        warn ".env not found — copying from .env.example"
        cp .env.example .env
        ok "Created .env (edit it with your settings)"
    else
        err "No .env or .env.example found!"
        exit 1
    fi
else
    ok ".env exists"
fi

# -----------------------------------------------------------
# 3. Install dependencies
# -----------------------------------------------------------
info "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    $PY -m pip install -q -r requirements.txt 2>&1 | tail -1
    ok "Dependencies installed"
else
    warn "requirements.txt not found — skipping"
fi

# -----------------------------------------------------------
# 4. Run migrations
# -----------------------------------------------------------
info "Running database migrations..."
$PY manage.py migrate --run-syncdb 2>&1 | tail -3
ok "Migrations applied"

# -----------------------------------------------------------
# 5. Collect static files
# -----------------------------------------------------------
info "Collecting static files..."
$PY manage.py collectstatic --noinput -q 2>/dev/null || true
ok "Static files collected"

# -----------------------------------------------------------
# 6. System check
# -----------------------------------------------------------
info "Running Django system check..."
$PY manage.py check --fail-level WARNING 2>&1 || true
ok "System checked"

# -----------------------------------------------------------
# 7. Production readiness (optional)
# -----------------------------------------------------------
if $PY manage.py help setup_production &>/dev/null 2>&1; then
    info "Running production readiness check..."
    $PY manage.py setup_production --check 2>&1 || true
fi

# -----------------------------------------------------------
# 8. Create superuser (interactive)
# -----------------------------------------------------------
echo ""
read -p "Create superuser now? (y/N): " CREATE_SUPER
if [[ "$CREATE_SUPER" =~ ^[Yy]$ ]]; then
    $PY manage.py createsuperuser
fi

# -----------------------------------------------------------
# Done!
# -----------------------------------------------------------
echo ""
echo "============================================="
ok "Tony ERP is ready!"
echo "============================================="
echo ""
info "Start the development server:"
echo "    $PY manage.py runserver"
echo ""
info "Or start with Docker:"
echo "    docker-compose up -d"
echo ""
info "Run tests:"
echo "    pytest -x"
echo ""
