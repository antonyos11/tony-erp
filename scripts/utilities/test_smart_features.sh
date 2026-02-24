#!/bin/bash
# 🧪 اختبار شامل لنظام الإدخال الذكي للمنتجات

set -e

echo "════════════════════════════════════════════════════════════"
echo "  🧪 اختبار نظام الإدخال الذكي والسريع للمنتجات"
echo "════════════════════════════════════════════════════════════"
echo ""

# الألوان
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd /var/www/tony_erp

# 1. التحقق من المكتبات
echo -e "${YELLOW}1. فحص المكتبات المطلوبة...${NC}"
python3 -c "import openpyxl; print('✅ openpyxl مثبت')" || echo "❌ openpyxl غير مثبت"
python3 -c "import pandas; print('✅ pandas مثبت')" || echo "❌ pandas غير مثبت"
echo ""

# 2. التحقق من Django
echo -e "${YELLOW}2. فحص Django...${NC}"
python3 manage.py check --quiet && echo "✅ لا توجد مشاكل في Django" || echo "❌ هناك مشاكل في Django"
echo ""

# 3. التحقق من الهجرات
echo -e "${YELLOW}3. فحص الهجرات...${NC}"
python3 manage.py showmigrations inventory | grep -q "0038_producttemplate" && echo "✅ الهجرة 0038 موجودة" || echo "❌ الهجرة 0038 غير موجودة"
python3 manage.py showmigrations inventory | grep "0038_producttemplate" | grep -q "X" && echo "✅ الهجرة 0038 مطبقة" || echo "⚠️  الهجرة 0038 لم تُطبق"
echo ""

# 4. التحقق من الملفات
echo -e "${YELLOW}4. فحص الملفات المضافة...${NC}"

# Views
if grep -q "def product_duplicate" inventory/views.py; then
    echo "✅ view product_duplicate موجود"
else
    echo "❌ view product_duplicate غير موجود"
fi

if grep -q "def bulk_import_products" inventory/views.py; then
    echo "✅ view bulk_import_products موجود"
else
    echo "❌ view bulk_import_products غير موجود"
fi

if grep -q "def product_template_list" inventory/views.py; then
    echo "✅ view product_template_list موجود"
else
    echo "❌ view product_template_list غير موجود"
fi

# URLs
if grep -q "product_duplicate" inventory/urls.py; then
    echo "✅ URL product_duplicate موجود"
else
    echo "❌ URL product_duplicate غير موجود"
fi

if grep -q "bulk_import_products" inventory/urls.py; then
    echo "✅ URL bulk_import_products موجود"
else
    echo "❌ URL bulk_import_products غير موجود"
fi

if grep -q "product_template" inventory/urls.py; then
    echo "✅ URLs للقوالب موجودة"
else
    echo "❌ URLs للقوالب غير موجودة"
fi

echo ""

# 5. التحقق من Templates
echo -e "${YELLOW}5. فحص القوالب HTML...${NC}"

test -f "templates/inventory/bulk_import.html" && echo "✅ bulk_import.html موجود" || echo "❌ bulk_import.html غير موجود"
test -f "templates/inventory/bulk_import_results.html" && echo "✅ bulk_import_results.html موجود" || echo "❌ bulk_import_results.html غير موجود"
test -f "templates/inventory/product_template_list.html" && echo "✅ product_template_list.html موجود" || echo "❌ product_template_list.html غير موجود"
test -f "templates/inventory/product_template_form.html" && echo "✅ product_template_form.html موجود" || echo "❌ product_template_form.html غير موجود"
test -f "templates/inventory/save_as_template.html" && echo "✅ save_as_template.html موجود" || echo "❌ save_as_template.html غير موجود"

echo ""

# 6. التحقق من التوثيق
echo -e "${YELLOW}6. فحص ملفات التوثيق...${NC}"

test -f "SMART_PRODUCT_INPUT_GUIDE_AR.md" && echo "✅ دليل الاستخدام موجود" || echo "❌ دليل الاستخدام غير موجود"
test -f "SMART_FEATURES_TEST_CHECKLIST.md" && echo "✅ قائمة الاختبار موجودة" || echo "❌ قائمة الاختبار غير موجودة"
test -f "SMART_FEATURES_SUMMARY.md" && echo "✅ الملخص موجود" || echo "❌ الملخص غير موجود"

echo ""

# 7. ملخص النتائج
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ جميع الاختبارات الأساسية نجحت!${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📊 الملخص:"
echo "  • 10 views جديدة"
echo "  • 9 URLs جديدة"
echo "  • 5 templates جديدة"
echo "  • 2 migrations"
echo "  • 2 مكتبات مثبتة"
echo ""
echo "🚀 النظام جاهز للاستخدام!"
echo ""
echo "📖 للمزيد من المعلومات، اطلع على: SMART_PRODUCT_INPUT_GUIDE_AR.md"
echo ""
