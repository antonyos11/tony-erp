#!/bin/bash

# ========================================
# فحص استخدام BASE_TEMPLATE في القوالب
# ========================================
# هذا السكريبت يتحقق من أن جميع القوالب تستخدم
# {% extends BASE_TEMPLATE %} بدلاً من {% extends 'base.html' %}
#
# الاستخدام:
#   ./scripts/check_template_extends.sh
#
# Exit Codes:
#   0 - جميع القوالب صحيحة
#   1 - وجدت قوالب تستخدم 'base.html' مباشرة
# ========================================

set -e

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "فحص استخدام BASE_TEMPLATE في القوالب"
echo "========================================="
echo ""

# البحث عن القوالب التي تستخدم 'base.html' مباشرة
echo "🔍 البحث عن القوالب التي تستخدم {% extends 'base.html' %}..."
echo ""

FOUND_FILES=$(find templates/ -name "*.html" -type f -exec grep -l "{% extends 'base.html' %}" {} \; 2>/dev/null || true)

if [ -z "$FOUND_FILES" ]; then
    echo -e "${GREEN}✅ ممتاز! جميع القوالب تستخدم BASE_TEMPLATE${NC}"
    echo ""
    
    # إحصائيات
    TOTAL_TEMPLATES=$(find templates/ -name "*.html" -type f | wc -l)
    BASE_TEMPLATE_COUNT=$(find templates/ -name "*.html" -type f -exec grep -l "{% extends BASE_TEMPLATE %}" {} \; 2>/dev/null | wc -l)
    
    echo "📊 الإحصائيات:"
    echo "  - إجمالي القوالب: $TOTAL_TEMPLATES"
    echo "  - القوالب التي تستخدم BASE_TEMPLATE: $BASE_TEMPLATE_COUNT"
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ خطأ! وجدت قوالب تستخدم {% extends 'base.html' %} مباشرة:${NC}"
    echo ""
    
    # عرض الملفات المخالفة
    COUNT=0
    while IFS= read -r file; do
        COUNT=$((COUNT + 1))
        echo -e "${YELLOW}  $COUNT. $file${NC}"
    done <<< "$FOUND_FILES"
    
    echo ""
    echo -e "${YELLOW}⚠️  يجب تحويل هذه القوالب لاستخدام {% extends BASE_TEMPLATE %}${NC}"
    echo ""
    echo "💡 لتحويل جميع القوالب تلقائياً، استخدم:"
    echo "   ./scripts/convert_template_extends.sh"
    echo ""
    
    exit 1
fi

