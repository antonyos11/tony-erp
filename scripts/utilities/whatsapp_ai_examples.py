"""
أمثلة على استخدام WhatsApp AI Integration API
================================================

هذه الأمثلة توضح كيفية التعامل مع النظام برمجياً
"""

import requests
import json

# ===========================================
# إعدادات الاتصال
# ===========================================
BASE_URL = "https://your-erp-domain.com"
API_TOKEN = "your_api_token_here"  # احصل عليه من /admin/authtoken/token/

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# ===========================================
# 1. جلب معلومات المنتجات للـ AI
# ===========================================
def get_ai_context():
    """
    جلب كل المعلومات المطلوبة للـ AI
    يستخدم هذا في n8n لتغذية الذكاء الصناعي
    """
    url = f"{BASE_URL}/api/whatsapp-ai/ai/context/"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ تم جلب {data['products_count']} منتج")
        print(f"System Prompt: {data['system_prompt'][:100]}...")
        return data
    else:
        print(f"❌ خطأ: {response.status_code}")
        return None


# ===========================================
# 2. إرسال رسالة واتساب للنظام
# ===========================================
def send_whatsapp_message(phone, message_id, text, customer_name=""):
    """
    محاكاة استقبال رسالة من WhatsApp API
    في الحقيقة، WhatsApp API سيرسل لهذا الـ endpoint مباشرة
    """
    url = f"{BASE_URL}/api/whatsapp-ai/webhook/whatsapp/"
    
    data = {
        "from_number": phone,
        "message_id": message_id,
        "message_type": "text",
        "text_body": text,
        "customer_name": customer_name
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ تم حفظ الرسالة")
        print(f"   Conversation ID: {result['conversation_id']}")
        print(f"   Message ID: {result['message_id']}")
        return result
    else:
        print(f"❌ خطأ: {response.text}")
        return None


# ===========================================
# 3. إرسال نتيجة الـ AI للنظام
# ===========================================
def send_ai_callback(conversation_id, ai_response, intent, products, sentiment, score):
    """
    بعد معالجة الـ AI في n8n، نرسل النتيجة للنظام
    """
    url = f"{BASE_URL}/api/whatsapp-ai/webhook/n8n-callback/"
    
    data = {
        "conversation_id": conversation_id,
        "ai_response": ai_response,
        "intent": intent,
        "products": products,
        "sentiment": sentiment,
        "conversion_score": score
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ تم تحديث المحادثة")
        return result
    else:
        print(f"❌ خطأ: {response.text}")
        return None


# ===========================================
# 4. البحث في المنتجات
# ===========================================
def search_products(query):
    """
    البحث في قاعدة معرفة المنتجات
    """
    url = f"{BASE_URL}/api/whatsapp-ai/products-knowledge/search/"
    
    response = requests.get(url, params={"q": query})
    
    if response.status_code == 200:
        products = response.json()
        print(f"✅ تم العثور على {len(products)} منتج")
        for p in products:
            print(f"   - {p['product_name']}: {p['price']} {p['currency']}")
        return products
    else:
        print(f"❌ خطأ: {response.text}")
        return []


# ===========================================
# 5. عرض المحادثات
# ===========================================
def list_conversations(status=None):
    """
    عرض كل المحادثات أو فلترة حسب الحالة
    """
    url = f"{BASE_URL}/api/whatsapp-ai/conversations/"
    
    params = {}
    if status:
        params['status'] = status
    
    response = requests.get(url, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        conversations = response.json()
        print(f"✅ عدد المحادثات: {len(conversations)}")
        for conv in conversations:
            print(f"\n📱 {conv['phone_number']} - {conv['customer_name_display']}")
            print(f"   الحالة: {conv['status']}")
            print(f"   عدد الرسائل: {conv['messages_count']}")
            print(f"   احتمالية الشراء: {conv['conversion_probability']*100:.0f}%")
            if conv['interested_products']:
                print(f"   المنتجات: {', '.join(conv['interested_products'])}")
        return conversations
    else:
        print(f"❌ خطأ: {response.status_code}")
        return []


# ===========================================
# 6. تحويل محادثة إلى عميل في CRM
# ===========================================
def convert_to_customer(conversation_id):
    """
    تحويل محادثة إلى عميل في CRM وإنشاء فرصة بيع
    """
    url = f"{BASE_URL}/api/whatsapp-ai/conversations/{conversation_id}/convert_to_customer/"
    
    response = requests.post(url, headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        if result.get('customer_id'):
            print(f"   Customer ID: {result['customer_id']}")
        if result.get('opportunity_id'):
            print(f"   Opportunity ID: {result['opportunity_id']}")
        return result
    else:
        print(f"❌ خطأ: {response.text}")
        return None


# ===========================================
# 7. مزامنة المنتجات من المخزون
# ===========================================
def sync_products():
    """
    مزامنة كل المنتجات من المخزون إلى قاعدة معرفة الـ AI
    """
    url = f"{BASE_URL}/api/whatsapp-ai/sync/products/"
    
    response = requests.post(url, headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        print(f"   تمت مزامنة {result['synced_count']} منتج")
        return result
    else:
        print(f"❌ خطأ: {response.text}")
        return None


# ===========================================
# 8. إضافة منتج للـ AI Knowledge Base يدوياً
# ===========================================
def add_product_knowledge(product_data):
    """
    إضافة منتج جديد لقاعدة معرفة الـ AI
    """
    url = f"{BASE_URL}/api/whatsapp-ai/products-knowledge/"
    
    response = requests.post(url, headers=HEADERS, json=product_data)
    
    if response.status_code == 201:
        product = response.json()
        print(f"✅ تمت إضافة المنتج: {product['product_name']}")
        return product
    else:
        print(f"❌ خطأ: {response.text}")
        return None


# ===========================================
# 9. سيناريو كامل: محادثة واتساب
# ===========================================
def full_whatsapp_conversation_example():
    """
    مثال كامل على محادثة واتساب من البداية للنهاية
    """
    print("\n" + "="*60)
    print("🤖 سيناريو كامل: محادثة واتساب مع AI")
    print("="*60)
    
    # 1. جلب context للـ AI
    print("\n📚 جلب معلومات المنتجات...")
    context = get_ai_context()
    
    # 2. استقبال رسالة من العميل
    print("\n📱 استقبال رسالة من العميل...")
    message_result = send_whatsapp_message(
        phone="+966501234567",
        message_id="msg_12345",
        text="السلام عليكم، عندكم مراتب طبية؟",
        customer_name="أحمد محمد"
    )
    
    if not message_result:
        return
    
    conversation_id = message_result['conversation_id']
    
    # 3. محاكاة رد الـ AI (في الواقع يتم في n8n)
    print("\n🤖 معالجة بالذكاء الصناعي...")
    ai_response = """مرحباً أحمد! نعم، لدينا مجموعة ممتازة من المراتب الطبية:
    
1. مرتبة سليب كومفورت الطبية - 2500 ج.م
   • طبقة ميموري فوم طبية
   • دعم كامل للعمود الفقري
   • ضمان 10 سنوات

2. مرتبة أورثو ميديكال - 3200 ج.م
   • تقنية الزنبرك المنفصل
   • خامات طبية معتمدة
   • ضمان 15 سنة

أيهما تفضل؟ أو تريد مزيد من التفاصيل؟"""
    
    # 4. إرسال نتيجة AI للنظام
    print("\n💾 حفظ تحليل الـ AI...")
    callback_result = send_ai_callback(
        conversation_id=conversation_id,
        ai_response=ai_response,
        intent="inquiry",
        products=["مرتبة سليب كومفورت الطبية", "مرتبة أورثو ميديكال"],
        sentiment="positive",
        score=0.7
    )
    
    # 5. عرض المحادثة
    print("\n📊 عرض المحادثة...")
    list_conversations(status="active")
    
    # 6. إذا كانت احتمالية عالية، تحويل لعميل
    print("\n✨ تحويل إلى عميل في CRM...")
    convert_result = convert_to_customer(conversation_id)
    
    print("\n" + "="*60)
    print("✅ انتهى السيناريو بنجاح!")
    print("="*60)


# ===========================================
# 10. أمثلة على بيانات المنتجات
# ===========================================
PRODUCT_EXAMPLES = [
    {
        "product_name": "مرتبة سليب كومفورت الطبية",
        "product_code": "MAT-001",
        "description": "مرتبة طبية فاخرة مع طبقة ميموري فوم تتكيف مع شكل الجسم",
        "features": [
            "طبقة ميموري فوم 5 سم",
            "دعم كامل للعمود الفقري",
            "مضادة للحساسية",
            "قماش قابل للفك والغسل"
        ],
        "specifications": {
            "المقاسات": ["سنجل", "دبل", "كينج", "كينج XL"],
            "الارتفاع": "30 سم",
            "الوزن": "45 كجم",
            "المادة": "ميموري فوم + زنبرك منفصل"
        },
        "price": 2500.00,
        "currency": "SAR",
        "keywords": ["مرتبة", "طبية", "ميموري فوم", "ظهر", "نوم"],
        "common_questions": [
            {
                "q": "هل مناسبة لآلام الظهر؟",
                "a": "نعم، مصممة خصيصاً لدعم العمود الفقري وتخفيف آلام الظهر"
            },
            {
                "q": "كم مدة الضمان؟",
                "a": "ضمان شامل لمدة 10 سنوات"
            }
        ],
        "in_stock": True,
        "stock_quantity": 25,
        "category": "مراتب طبية",
        "tags": ["طبي", "ميموري فوم", "الأكثر مبيعاً"]
    },
    {
        "product_name": "وسادة طبية ميموري فوم",
        "product_code": "PIL-001",
        "description": "وسادة طبية لدعم الرقبة والرأس أثناء النوم",
        "features": [
            "ميموري فوم عالي الكثافة",
            "دعم طبي للرقبة",
            "غطاء قطني قابل للإزالة",
            "مضادة للبكتيريا"
        ],
        "specifications": {
            "المقاس": "50x30x10 سم",
            "الوزن": "1.2 كجم"
        },
        "price": 250.00,
        "currency": "SAR",
        "keywords": ["وسادة", "طبية", "رقبة", "ميموري فوم"],
        "common_questions": [
            {
                "q": "مناسبة لآلام الرقبة؟",
                "a": "نعم، مصممة خصيصاً لتخفيف آلام الرقبة"
            }
        ],
        "in_stock": True,
        "stock_quantity": 100,
        "category": "إكسسوارات النوم",
        "tags": ["طبي", "رقبة", "جديد"]
    }
]


# ===========================================
# تشغيل الأمثلة
# ===========================================
if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║   WhatsApp AI Integration - أمثلة الاستخدام              ║
╚════════════════════════════════════════════════════════════╝

اختر مثال:
1. جلب معلومات المنتجات للـ AI
2. إرسال رسالة واتساب
3. البحث في المنتجات
4. عرض المحادثات
5. مزامنة المنتجات
6. سيناريو كامل
7. إضافة منتج للـ AI
0. خروج
    """)
    
    choice = input("اختر رقم: ").strip()
    
    if choice == "1":
        get_ai_context()
    elif choice == "2":
        phone = input("رقم الهاتف: ")
        text = input("نص الرسالة: ")
        send_whatsapp_message(phone, f"msg_{int(time.time())}", text)
    elif choice == "3":
        query = input("كلمة البحث: ")
        search_products(query)
    elif choice == "4":
        list_conversations()
    elif choice == "5":
        sync_products()
    elif choice == "6":
        full_whatsapp_conversation_example()
    elif choice == "7":
        # مثال على إضافة منتج
        add_product_knowledge(PRODUCT_EXAMPLES[0])
    else:
        print("👋 إلى اللقاء!")
