#!/bin/bash
# TestSprite Fixes - Verification Script
# تشغيل هذا السكريبت للتحقق من أن جميع الإصلاحات مطبقة بشكل صحيح

echo "=========================================="
echo "TestSprite Fixes - التحقق من التطبيق"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd /var/www/tony_erp

# 1. Check migrations
echo "1. فحص Migrations..."
if python3 manage.py showmigrations sales | grep -q "\[X\] 0030_add_accounting_integration"; then
    echo -e "${GREEN}✓ Migration 0030_add_accounting_integration مطبقة${NC}"
else
    echo -e "${RED}✗ Migration غير مطبقة!${NC}"
    echo "   قم بتشغيل: python3 manage.py migrate sales"
fi
echo ""

# 2. Check settings
echo "2. فحص الإعدادات..."
if grep -q "ALLOW_NEGATIVE_INVENTORY" accountant_pro/settings.py; then
    echo -e "${GREEN}✓ ALLOW_NEGATIVE_INVENTORY موجود في settings.py${NC}"
else
    echo -e "${RED}✗ ALLOW_NEGATIVE_INVENTORY غير موجود!${NC}"
fi

if [ -f .env ] && grep -q "ALLOW_NEGATIVE_INVENTORY" .env; then
    echo -e "${GREEN}✓ ALLOW_NEGATIVE_INVENTORY موجود في .env${NC}"
else
    echo -e "${YELLOW}⚠ ALLOW_NEGATIVE_INVENTORY غير موجود في .env${NC}"
    echo "   قم بإضافة: echo 'ALLOW_NEGATIVE_INVENTORY=0' >> .env"
fi
echo ""

# 3. Check files exist
echo "3. فحص الملفات الجديدة..."
files_to_check=(
    "api/test_views.py"
    "sales/services/accounting_integration.py"
    "sales/migrations/0030_add_accounting_integration.py"
    "TESTSPRITE_README.md"
    "TESTSPRITE_FINAL_SUMMARY.md"
    "TESTSPRITE_FIXES_IMPLEMENTATION.md"
    "TESTSPRITE_FIXES_SETUP_GUIDE.md"
    "TESTSPRITE_QUICK_REFERENCE.md"
    "NEXT_STEPS.md"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file غير موجود!${NC}"
    fi
done
echo ""

# 4. Check imports
echo "4. فحص الاستيرادات..."
if python3 manage.py shell -c "from sales.services.accounting_integration import post_invoice_to_accounting; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${GREEN}✓ accounting_integration يمكن استيراده${NC}"
else
    echo -e "${RED}✗ خطأ في استيراد accounting_integration${NC}"
fi

if python3 manage.py shell -c "from api.test_views import TestResourceViewSet; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${GREEN}✓ test_views يمكن استيراده${NC}"
else
    echo -e "${RED}✗ خطأ في استيراد test_views${NC}"
fi
echo ""

# 5. Check Django
echo "5. فحص Django..."
if python3 manage.py check --deploy 2>&1 | grep -q "System check identified no issues"; then
    echo -e "${GREEN}✓ Django check passed${NC}"
else
    echo -e "${YELLOW}⚠ توجد تحذيرات في Django check${NC}"
    echo "   قم بتشغيل: python3 manage.py check --deploy"
fi
echo ""

# 6. Check URL patterns
echo "6. فحص URL patterns..."
if grep -q "invoice_post_accounting" sales/urls.py; then
    echo -e "${GREEN}✓ invoice_post_accounting URL موجود${NC}"
else
    echo -e "${RED}✗ invoice_post_accounting URL غير موجود!${NC}"
fi

if grep -q "test_views" api_app/urls.py; then
    echo -e "${GREEN}✓ test_views URLs موجودة${NC}"
else
    echo -e "${RED}✗ test_views URLs غير موجودة!${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "الخلاصة"
echo "=========================================="
echo ""
echo "إذا رأيت علامات ✓ خضراء، فالإصلاحات مطبقة بشكل صحيح."
echo "إذا رأيت علامات ✗ حمراء أو ⚠ صفراء، راجع الخطوات في:"
echo "  - NEXT_STEPS.md"
echo "  - TESTSPRITE_FIXES_SETUP_GUIDE.md"
echo ""
echo "=========================================="
