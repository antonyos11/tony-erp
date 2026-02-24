#!/bin/bash
# سكريبت اختبار سريع لنظام POS

echo "======================================"
echo "🧪 اختبار نظام POS"
echo "======================================"
echo ""

# فحص الخادم
echo "1️⃣  فحص حالة الخادم..."
if pgrep -f "manage.py runserver" > /dev/null; then
    echo "   ✅ الخادم يعمل"
else
    echo "   ❌ الخادم متوقف - يتم تشغيله..."
    cd /var/www/tony_erp
    nohup python3 manage.py runserver 0.0.0.0:8000 > /dev/null 2>&1 &
    sleep 2
    echo "   ✅ تم تشغيل الخادم"
fi

echo ""
echo "2️⃣  اختبار الاتصال بالنظام..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/pos/)
if [ "$response" = "200" ] || [ "$response" = "302" ]; then
    echo "   ✅ النظام يستجيب - HTTP $response"
else
    echo "   ⚠️  استجابة غير متوقعة - HTTP $response"
fi

echo ""
echo "3️⃣  فحص قاعدة البيانات..."
cd /var/www/tony_erp
product_count=$(python3 manage.py shell -c "from inventory.models import Product; print(Product.objects.count())" 2>/dev/null)
stock_count=$(python3 manage.py shell -c "from inventory.models import Stock; print(Stock.objects.count())" 2>/dev/null)
batch_count=$(python3 manage.py shell -c "from inventory.models import StockBatch; print(StockBatch.objects.count())" 2>/dev/null)

echo "   📦 عدد المنتجات: $product_count"
echo "   📊 عدد المخزونات: $stock_count"
echo "   🔢 عدد الـBatches: $batch_count"

if [ "$product_count" -gt "0" ] && [ "$stock_count" -gt "0" ] && [ "$batch_count" -gt "0" ]; then
    echo "   ✅ قاعدة البيانات جاهزة"
else
    echo "   ⚠️  قد تحتاج لتشغيل سكريبتات الإعداد"
fi

echo ""
echo "======================================"
echo "📱 روابط الاختبار"
echo "======================================"
echo ""
echo "🏪 نقطة البيع:"
echo "   http://72.62.176.249:8000/pos/order/new/"
echo ""
echo "🏠 لوحة التحكم:"
echo "   http://72.62.176.249:8000/pos/"
echo ""
echo "📊 فتح جلسة:"
echo "   http://72.62.176.249:8000/pos/session/open/"
echo ""
echo "======================================"
echo "✅ الاختبار اكتمل!"
echo "======================================"
