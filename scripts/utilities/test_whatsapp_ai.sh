#!/bin/bash
# اختبار سريع لـ WhatsApp AI Integration

echo "🧪 اختبار WhatsApp AI Integration"
echo "=================================="

# URL الأساسي
BASE_URL="http://localhost:8000"

echo ""
echo "✅ 1. اختبار: جلب معلومات المنتجات للـ AI"
echo "-------------------------------------------"
curl -s "${BASE_URL}/api/whatsapp-ai/ai/context/" | python3 -m json.tool | head -30

echo ""
echo ""
echo "✅ 2. اختبار: إرسال رسالة واتساب للنظام"
echo "-------------------------------------------"
curl -X POST "${BASE_URL}/api/whatsapp-ai/webhook/whatsapp/" \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+966501234567",
    "message_id": "test_msg_'$(date +%s)'",
    "message_type": "text",
    "text_body": "السلام عليكم، عندكم مراتب طبية؟",
    "customer_name": "أحمد محمد"
  }' | python3 -m json.tool

echo ""
echo ""
echo "✅ 3. اختبار: البحث في المنتجات"
echo "-------------------------------------------"
curl -s "${BASE_URL}/api/whatsapp-ai/products-knowledge/search/?q=مرتبة" | python3 -m json.tool

echo ""
echo ""
echo "✅ 4. اختبار: عرض المحادثات (يحتاج Token)"
echo "-------------------------------------------"
echo "⚠️  يجب إضافة Authorization Token للاختبار الكامل"
echo "مثال: curl -H 'Authorization: Token YOUR_TOKEN' ..."

echo ""
echo ""
echo "🎉 انتهى الاختبار!"
echo "==================="
echo ""
echo "📋 الخطوات التالية:"
echo "1. أضف منتجات في /admin/whatsapp_ai/productknowledgebase/"
echo "2. أضف إعدادات WhatsApp في /admin/whatsapp_ai/whatsappconfiguration/"
echo "3. زامن المنتجات من المخزون"
echo "4. استورد workflow في n8n"
echo ""
