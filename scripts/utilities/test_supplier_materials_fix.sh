#!/bin/bash

# ===========================================
# اختبار سريع لإصلاح قسم مواد المورد
# ===========================================

echo "🔍 اختبار إصلاح قسم مواد المورد..."
echo ""

# 1. التحقق من صحة Django
echo "1️⃣ التحقق من صحة المشروع..."
cd /var/www/tony_erp
python3 manage.py check
if [ $? -eq 0 ]; then
    echo "✅ المشروع صحيح بدون أخطاء"
else
    echo "❌ يوجد أخطاء في المشروع"
    exit 1
fi

echo ""

# 2. التحقق من وجود الملفات
echo "2️⃣ التحقق من الملفات..."
if [ -f "/var/www/tony_erp/templates/inventory/raw_material_form.html" ]; then
    echo "✅ ملف raw_material_form.html موجود"
else
    echo "❌ الملف غير موجود"
    exit 1
fi

echo ""

# 3. التحقق من API endpoint
echo "3️⃣ التحقق من API endpoint..."
grep -q "api/supplier.*price-info" /var/www/tony_erp/inventory/urls.py
if [ $? -eq 0 ]; then
    echo "✅ API endpoint موجود في urls.py"
else
    echo "❌ API endpoint غير موجود"
    exit 1
fi

echo ""

# 4. التحقق من دالة loadSupplierMaterials
echo "4️⃣ التحقق من دالة loadSupplierMaterials..."
grep -q "window.loadSupplierMaterials = function()" /var/www/tony_erp/templates/inventory/raw_material_form.html
if [ $? -eq 0 ]; then
    echo "✅ دالة loadSupplierMaterials موجودة"
else
    echo "❌ دالة loadSupplierMaterials غير موجودة"
    exit 1
fi

echo ""

# 5. التحقق من CSS classes
echo "5️⃣ التحقق من CSS classes..."
grep -q "\.material-item" /var/www/tony_erp/templates/inventory/raw_material_form.html
if [ $? -eq 0 ]; then
    echo "✅ CSS classes موجودة"
else
    echo "❌ CSS classes غير موجودة"
    exit 1
fi

echo ""

# 6. عرض تعليمات الاختبار اليدوي
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 تعليمات الاختبار اليدوي:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. افتح المتصفح واذهب إلى:"
echo "   http://72.62.176.249/inventory/products/raw-material/create/"
echo ""
echo "2. اختر مورد من قائمة 'المورد الرئيسي/المفضل'"
echo ""
echo "3. تحقق من:"
echo "   ✓ ظهور قائمة المواد المتاحة"
echo "   ✓ إمكانية اختيار مادة"
echo "   ✓ تطبيق البيانات تلقائياً (السعر، الوحدة، المعامل)"
echo "   ✓ القسم لا يختفي"
echo "   ✓ التأثيرات البصرية (hover, selection)"
echo ""
echo "4. جرب:"
echo "   ✓ اختيار مادة مختلفة"
echo "   ✓ زر 'تحديث'"
echo "   ✓ زر 'إلغاء' في المادة المختارة"
echo "   ✓ تغيير المورد"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ جميع الفحوصات التلقائية نجحت!"
echo "📝 راجع الملف: FIX_SUPPLIER_MATERIALS_SECTION.md"
echo ""
