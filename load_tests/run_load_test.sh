#!/bin/bash

# Load Testing Script for Tony ERP
# سكريبت اختبار الأداء لنظام Tony ERP

echo "========================================="
echo "Tony ERP Load Testing"
echo "========================================="
echo ""

# التحقق من تثبيت Locust
if ! command -v locust &> /dev/null; then
    echo "❌ Locust غير مثبت. جاري التثبيت..."
    pip install locust
fi

# Default values
HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-50}"
SPAWN_RATE="${SPAWN_RATE:-5}"
RUN_TIME="${RUN_TIME:-5m}"

echo "📊 إعدادات الاختبار:"
echo "   Host: $HOST"
echo "   Users: $USERS"
echo "   Spawn Rate: $SPAWN_RATE users/sec"
echo "   Run Time: $RUN_TIME"
echo ""

# قائمة اختبارات محددة مسبقاً
echo "اختر نوع الاختبار:"
echo "1) اختبار خفيف (10 users, 2 min)"
echo "2) اختبار متوسط (50 users, 5 min)"
echo "3) اختبار ثقيل (100 users, 10 min)"
echo "4) اختبار شديد (200 users, 15 min)"
echo "5) مخصص"
echo ""

read -p "اختر (1-5): " choice

case $choice in
    1)
        USERS=10
        SPAWN_RATE=2
        RUN_TIME="2m"
        ;;
    2)
        USERS=50
        SPAWN_RATE=5
        RUN_TIME="5m"
        ;;
    3)
        USERS=100
        SPAWN_RATE=10
        RUN_TIME="10m"
        ;;
    4)
        USERS=200
        SPAWN_RATE=10
        RUN_TIME="15m"
        ;;
    5)
        read -p "عدد المستخدمين: " USERS
        read -p "معدل الإضافة (users/sec): " SPAWN_RATE
        read -p "مدة الاختبار (مثال: 5m): " RUN_TIME
        ;;
    *)
        echo "❌ اختيار غير صحيح. استخدام الإعدادات الافتراضية."
        ;;
esac

echo ""
echo "🚀 بدء الاختبار..."
echo ""

# إنشاء مجلد النتائج
mkdir -p load_tests/results

# تشغيل Locust
locust \
    -f load_tests/locustfile.py \
    --host="$HOST" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="$RUN_TIME" \
    --headless \
    --html="load_tests/results/report_$(date +%Y%m%d_%H%M%S).html" \
    --csv="load_tests/results/results_$(date +%Y%m%d_%H%M%S)" \
    --loglevel=INFO

echo ""
echo "✅ اكتمل الاختبار!"
echo "📄 التقارير موجودة في: load_tests/results/"
echo ""
