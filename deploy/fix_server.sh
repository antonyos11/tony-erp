#!/usr/bin/env bash
# ============================================================
# Tony ERP - Server Fix Script
# bash deploy/fix_server.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

PROJECT_DIR="/var/www/tony_erp"
PY="python3"

echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  Tony ERP - Server Fix${NC}"
echo -e "${BLUE}  $(date)${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

cd "$PROJECT_DIR" || { err "Cannot cd to $PROJECT_DIR"; exit 1; }
ok "Directory: $(pwd)"

# ===== 1. Directories =====
info "[1/7] Creating directories..."
mkdir -p logs media staticfiles backups templates/errors
ok "Directories ready"

# ===== 2. Migrations =====
info "[2/7] Running migrations..."
$PY manage.py migrate --noinput 2>&1 | tail -3
ok "Migrations applied"

# ===== 3. Static Files =====
info "[3/7] Collecting static files..."
$PY manage.py collectstatic --noinput -q 2>/dev/null || true
ok "Static files collected"

# ===== 4. Django Check =====
info "[4/7] Django system check..."
$PY manage.py check 2>&1 || true

# ===== 5. SSL Certificate =====
info "[5/7] SSL Certificate..."
if [ -f "/etc/ssl/certs/tony_erp.crt" ]; then
    ok "SSL certificate exists"
else
    warn "Creating self-signed SSL certificate..."
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "72.62.176.249")
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/tony_erp.key \
        -out /etc/ssl/certs/tony_erp.crt \
        -subj "/CN=${SERVER_IP}/O=TonyERP/C=SA" \
        2>/dev/null && ok "SSL certificate created" || warn "SSL creation failed (run manually)"
fi

# ===== 6. Nginx =====
info "[6/7] Nginx configuration..."
if command -v nginx &>/dev/null; then
    if [ -f "deploy/nginx/tony_erp.conf" ]; then
        sudo cp deploy/nginx/tony_erp.conf /etc/nginx/sites-available/tony_erp
        sudo ln -sf /etc/nginx/sites-available/tony_erp /etc/nginx/sites-enabled/tony_erp 2>/dev/null || true
        sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

        if sudo nginx -t 2>&1; then
            sudo systemctl reload nginx
            ok "Nginx reloaded"
        else
            err "Nginx config test failed"
            sudo nginx -t
        fi
    else
        warn "deploy/nginx/tony_erp.conf not found"
    fi
else
    warn "Nginx not installed: sudo apt install nginx"
fi

# ===== 7. Production Check =====
info "[7/7] Production readiness check..."
$PY manage.py fix_production --check 2>&1 || true

# ===== Done =====
echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}  Done!${NC}"
echo -e "${GREEN}=============================================${NC}"
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "72.62.176.249")
echo ""
echo "  HTTP:   http://${SERVER_IP}/"
echo "  HTTPS:  https://${SERVER_IP}/"
echo "  Admin:  https://${SERVER_IP}/admin/"
echo "  Health: https://${SERVER_IP}/health/live/"
echo ""
