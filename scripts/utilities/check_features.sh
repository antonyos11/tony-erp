#!/bin/bash
# سكريبت فحص سريع للميزات الجديدة

echo "🔍 فحص الميزات الجديدة..."
echo ""

# 1. فحص الملفات
echo "1️⃣ فحص وجود الملفات:"
if [ -f "static/accounting/js/entry_features.js" ]; then
    echo "   ✅ entry_features.js موجود"
    SIZE=$(wc -l < static/accounting/js/entry_features.js)
    echo "      📏 الحجم: $SIZE سطر"
else
    echo "   ❌ entry_features.js غير موجود!"
fi

if [ -f "static/accounting/css/entry_features.css" ]; then
    echo "   ✅ entry_features.css موجود"
    SIZE=$(wc -l < static/accounting/css/entry_features.css)
    echo "      📏 الحجم: $SIZE سطر"
else
    echo "   ❌ entry_features.css غير موجود!"
fi

echo ""
echo "2️⃣ فحص الدوال الجديدة في JavaScript:"
FUNCTIONS=(
    "initDraftRestoreBanner"
    "initLastChoicesMemory"
    "initAccountValidation"
    "initDuplicateDetection"
    "initRecentEntriesCopy"
    "initAttachmentsPreview"
    "initEnhancedKeyboardShortcuts"
)

for func in "${FUNCTIONS[@]}"; do
    if grep -q "$func" static/accounting/js/entry_features.js; then
        echo "   ✅ $func"
    else
        echo "   ❌ $func غير موجود!"
    fi
done

echo ""
echo "3️⃣ فحص الستايلات الجديدة في CSS:"
STYLES=(
    "draft-restore-banner"
    "remembered-badge"
    "account-warning"
    "recent-entries-section"
    "attachment-preview"
    "keyboard-shortcuts-hint"
)

for style in "${STYLES[@]}"; do
    if grep -q "$style" static/accounting/css/entry_features.css; then
        echo "   ✅ .$style"
    else
        echo "   ❌ .$style غير موجود!"
    fi
done

echo ""
echo "4️⃣ فحص التعديلات في Backend:"
if grep -q "continue_new" accounting/views.py; then
    echo "   ✅ منطق حفظ+جديد موجود"
else
    echo "   ❌ منطق حفظ+جديد غير موجود!"
fi

if grep -q "get_recent_entries" accounting/views.py; then
    echo "   ✅ API القيود الأخيرة موجود"
else
    echo "   ❌ API القيود الأخيرة غير موجود!"
fi

if grep -q "entries/recent/" accounting/urls.py; then
    echo "   ✅ URL القيود الأخيرة موجود"
else
    echo "   ❌ URL القيود الأخيرة غير موجود!"
fi

echo ""
echo "5️⃣ فحص التعديلات في HTML:"
if grep -q "حفظ + جديد" accounting/templates/accounting/account_entry_form.html; then
    echo "   ✅ زر حفظ+جديد موجود"
else
    echo "   ❌ زر حفظ+جديد غير موجود!"
fi

if grep -q "keyboard-shortcuts-hint" accounting/templates/accounting/account_entry_form.html; then
    echo "   ✅ تلميح الاختصارات موجود"
else
    echo "   ❌ تلميح الاختصارات غير موجود!"
fi

echo ""
echo "6️⃣ فحص الملفات الثابتة المجمّعة:"
if [ -d "staticfiles/accounting/js" ]; then
    if [ -f "staticfiles/accounting/js/entry_features.js" ]; then
        echo "   ✅ JS مجمّع في staticfiles"
    else
        echo "   ⚠️ JS غير مجمّع! قم بتشغيل: python3 manage.py collectstatic"
    fi
else
    echo "   ⚠️ مجلد staticfiles غير موجود!"
fi

if [ -d "staticfiles/accounting/css" ]; then
    if [ -f "staticfiles/accounting/css/entry_features.css" ]; then
        echo "   ✅ CSS مجمّع في staticfiles"
    else
        echo "   ⚠️ CSS غير مجمّع! قم بتشغيل: python3 manage.py collectstatic"
    fi
fi

echo ""
echo "✅ انتهى الفحص!"
echo ""
echo "📋 الخطوة التالية:"
echo "   1. حدّث المتصفح بقوة: Ctrl+Shift+R"
echo "   2. افتح وحدة تحكم المتصفح: F12"
echo "   3. ابحث عن رسائل خطأ حمراء"
echo "   4. اختبر الميزات واحدة تلو الأخرى"
