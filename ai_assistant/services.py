"""
خدمة الذكاء الاصطناعي
====================
تتعامل مع مزودي خدمات AI المختلفين
"""
import json
import time
import re
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.db.models import Q


class AIService:
    """خدمة الذكاء الاصطناعي الموحدة"""
    
    def __init__(self, assistant_settings):
        self.settings = assistant_settings
        self.provider = assistant_settings.provider
        self.api_key = assistant_settings.api_key
        self.model = assistant_settings.model_name
        self.max_tokens = assistant_settings.max_tokens
        self.temperature = assistant_settings.temperature
        self.system_prompt = assistant_settings.system_prompt
    
    def get_response(self, messages: List[Dict], context: Dict = None) -> Dict:
        """الحصول على رد من نموذج AI"""
        start_time = time.time()
        
        # إذا لم يكن هناك API key، استخدم الردود المحلية
        if not self.api_key:
            response = self._get_local_response(messages, context)
        elif self.provider == 'openai':
            response = self._call_openai(messages, context)
        elif self.provider == 'anthropic':
            response = self._call_anthropic(messages, context)
        elif self.provider == 'google':
            response = self._call_google(messages, context)
        else:
            response = self._get_local_response(messages, context)
        
        processing_time = time.time() - start_time
        response['processing_time'] = processing_time
        
        return response
    
    def _call_openai(self, messages: List[Dict], context: Dict = None) -> Dict:
        """استدعاء OpenAI API"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            # إضافة system prompt
            full_messages = []
            if self.system_prompt:
                full_messages.append({
                    "role": "system",
                    "content": self._build_system_prompt(context)
                })
            full_messages.extend(messages)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens if response.usage else 0
            }
        except Exception as e:
            return {
                'success': False,
                'content': f'عذراً، حدث خطأ في الاتصال بالمساعد الذكي. يرجى المحاولة لاحقاً.',
                'error': str(e),
                'tokens_used': 0
            }
    
    def _call_anthropic(self, messages: List[Dict], context: Dict = None) -> Dict:
        """استدعاء Anthropic API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # تحويل الرسائل لتنسيق Anthropic
            anthropic_messages = []
            for msg in messages:
                if msg['role'] != 'system':
                    anthropic_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            response = client.messages.create(
                model=self.model or "claude-3-sonnet-20240229",
                max_tokens=self.max_tokens,
                system=self._build_system_prompt(context),
                messages=anthropic_messages
            )
            
            return {
                'success': True,
                'content': response.content[0].text,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
            }
        except Exception as e:
            return {
                'success': False,
                'content': f'عذراً، حدث خطأ في الاتصال بالمساعد الذكي.',
                'error': str(e),
                'tokens_used': 0
            }
    
    def _call_google(self, messages: List[Dict], context: Dict = None) -> Dict:
        """استدعاء Google Gemini API"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model or 'gemini-pro')
            
            # تحويل الرسائل
            chat = model.start_chat(history=[])
            
            # إضافة السياق
            if self.system_prompt:
                chat.send_message(self._build_system_prompt(context))
            
            # إرسال آخر رسالة
            last_message = messages[-1]['content'] if messages else ''
            response = chat.send_message(last_message)
            
            return {
                'success': True,
                'content': response.text,
                'tokens_used': 0  # Google doesn't provide token count easily
            }
        except Exception as e:
            return {
                'success': False,
                'content': f'عذراً، حدث خطأ في الاتصال بالمساعد الذكي.',
                'error': str(e),
                'tokens_used': 0
            }
    
    def _get_local_response(self, messages: List[Dict], context: Dict = None) -> Dict:
        """ردود محلية ذكية بدون API"""
        from .models import FAQ, QuickReply
        
        last_message = messages[-1]['content'].lower() if messages else ''
        assistant_type = self.settings.assistant_type
        
        # البحث في الأسئلة الشائعة
        faq_response = self._search_faqs(last_message, assistant_type)
        if faq_response:
            return {
                'success': True,
                'content': faq_response,
                'tokens_used': 0
            }
        
        # البحث في المنتجات (للمتجر)
        if assistant_type == 'store' and context:
            product_response = self._search_products(last_message, context)
            if product_response:
                return product_response
        
        # ردود افتراضية ذكية
        response = self._get_smart_default_response(last_message, assistant_type, context)
        
        return {
            'success': True,
            'content': response,
            'tokens_used': 0
        }
    
    def _search_faqs(self, query: str, assistant_type: str) -> Optional[str]:
        """البحث في الأسئلة الشائعة"""
        from .models import FAQ
        
        # البحث بالكلمات المفتاحية
        words = query.split()
        
        faqs = FAQ.objects.filter(
            assistant_type=assistant_type,
            is_active=True
        )
        
        for faq in faqs:
            keywords = faq.get_keywords_list()
            # تحقق من تطابق الكلمات
            if any(word in query for word in keywords):
                faq.views_count += 1
                faq.save(update_fields=['views_count'])
                return faq.answer
            
            # تحقق من تشابه السؤال
            if self._similarity_check(query, faq.question.lower()):
                faq.views_count += 1
                faq.save(update_fields=['views_count'])
                return faq.answer
        
        return None
    
    def _similarity_check(self, text1: str, text2: str) -> bool:
        """فحص بسيط للتشابه"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        common = words1.intersection(words2)
        similarity = len(common) / min(len(words1), len(words2))
        
        return similarity > 0.4
    
    def _search_products(self, query: str, context: Dict) -> Optional[Dict]:
        """البحث في المنتجات"""
        try:
            from ecommerce.models import Product
            
            # كلمات البحث عن المنتجات
            search_triggers = ['منتج', 'سعر', 'أبحث', 'ابحث', 'عايز', 'عاوز', 'محتاج', 'فين', 'أين', 'كم']
            
            if any(trigger in query for trigger in search_triggers):
                # استخراج كلمات البحث
                search_terms = query
                for trigger in search_triggers:
                    search_terms = search_terms.replace(trigger, '')
                search_terms = search_terms.strip()
                
                if search_terms:
                    products = Product.objects.filter(
                        Q(name__icontains=search_terms) |
                        Q(description__icontains=search_terms) |
                        Q(category__name__icontains=search_terms),
                        is_active=True,
                        stock__gt=0
                    )[:5]
                    
                    if products:
                        response = f"وجدت {products.count()} منتج متعلق بـ \"{search_terms}\":\n\n"
                        product_data = []
                        
                        for product in products:
                            response += f"🔹 **{product.name}**\n"
                            response += f"   السعر: {product.price} ج.م\n"
                            if product.sale_price:
                                response += f"   سعر العرض: {product.sale_price} ج.م\n"
                            response += "\n"
                            
                            product_data.append({
                                'id': str(product.id),
                                'name': product.name,
                                'price': float(product.price),
                                'sale_price': float(product.sale_price) if product.sale_price else None,
                                'url': f"/shop/product/{product.slug}/"
                            })
                        
                        response += "\nهل تريد معرفة المزيد عن أي منتج؟"
                        
                        return {
                            'success': True,
                            'content': response,
                            'tokens_used': 0,
                            'related_products': product_data
                        }
        except Exception:
            pass
        
        return None
    
    def _get_smart_default_response(self, query: str, assistant_type: str, context: Dict = None) -> str:
        """ردود افتراضية ذكية"""
        
        # تحيات
        greetings = ['مرحبا', 'اهلا', 'السلام', 'صباح', 'مساء', 'هاي', 'hi', 'hello']
        if any(g in query for g in greetings):
            if assistant_type == 'store':
                return "أهلاً وسهلاً بك في متجرنا! 🛍️\n\nأنا مساعدك الذكي، يمكنني مساعدتك في:\n• البحث عن المنتجات\n• معرفة الأسعار والعروض\n• تتبع طلباتك\n• الإجابة على استفساراتك\n\nكيف يمكنني مساعدتك اليوم؟"
            else:
                return "أهلاً بك! 👋\n\nأنا مساعدك الذكي في نظام Tony ERP.\n\nيمكنني مساعدتك في:\n• شرح وظائف النظام\n• إرشادك للقوائم والصفحات\n• حل المشكلات الشائعة\n• تقديم النصائح\n\nما الذي تحتاج مساعدة فيه؟"
        
        # أسئلة الشحن
        shipping_words = ['شحن', 'توصيل', 'delivery', 'shipping']
        if any(w in query for w in shipping_words):
            return "🚚 **معلومات الشحن والتوصيل:**\n\n• التوصيل متاح لجميع المحافظات\n• مدة التوصيل: 2-5 أيام عمل\n• الشحن مجاني للطلبات فوق 2000 ج.م\n• يمكنك تتبع طلبك من صفحة 'طلباتي'\n\nهل لديك استفسار آخر؟"
        
        # أسئلة الدفع
        payment_words = ['دفع', 'فلوس', 'payment', 'فيزا', 'كاش']
        if any(w in query for w in payment_words):
            return "💳 **طرق الدفع المتاحة:**\n\n• الدفع عند الاستلام (كاش)\n• البطاقات الائتمانية (Visa/Mastercard)\n• التحويل البنكي\n• المحافظ الإلكترونية\n\nجميع المعاملات آمنة ومشفرة 🔒"
        
        # أسئلة المرتجعات
        return_words = ['إرجاع', 'ارجاع', 'مرتجع', 'استبدال', 'return']
        if any(w in query for w in return_words):
            return "↩️ **سياسة الإرجاع والاستبدال:**\n\n• يمكنك إرجاع المنتج خلال 14 يوم\n• المنتج يجب أن يكون بحالته الأصلية\n• الاسترداد خلال 3-5 أيام عمل\n• للاستبدال، تواصل معنا عبر خدمة العملاء\n\nهل تحتاج مساعدة في إرجاع منتج؟"
        
        # طلب
        order_words = ['طلب', 'order', 'طلبي', 'تتبع']
        if any(w in query for w in order_words):
            if assistant_type == 'store':
                return "📦 **بخصوص طلبك:**\n\nلتتبع طلبك:\n1. اذهب إلى 'حسابي'\n2. اختر 'طلباتي'\n3. اضغط على الطلب لمعرفة حالته\n\nأو أخبرني برقم الطلب وسأساعدك في تتبعه."
        
        # شكر
        thanks_words = ['شكر', 'thanks', 'thank', 'مشكور']
        if any(w in query for w in thanks_words):
            return "العفو! 😊 سعيد بمساعدتك.\n\nهل هناك شيء آخر يمكنني مساعدتك فيه؟"
        
        # رد افتراضي
        if assistant_type == 'store':
            return "شكراً لتواصلك معنا! 🌟\n\nللأسف لم أفهم طلبك بشكل واضح.\n\nيمكنك:\n• البحث عن منتج معين (مثال: أريد مرتبة)\n• السؤال عن الشحن والتوصيل\n• الاستفسار عن طلباتك\n\nأو تواصل مع خدمة العملاء للمساعدة المباشرة."
        else:
            return "شكراً لتواصلك! 💼\n\nلم أستطع فهم طلبك بشكل واضح.\n\nيمكنك:\n• السؤال عن كيفية استخدام وظيفة معينة\n• طلب شرح لقائمة أو صفحة\n• الاستفسار عن تقرير معين\n\nحاول صياغة سؤالك بشكل مختلف."
    
    def _build_system_prompt(self, context: Dict = None) -> str:
        """بناء تعليمات النظام"""
        base_prompt = self.system_prompt or self._get_default_system_prompt()
        
        if context:
            base_prompt += f"\n\nمعلومات إضافية:\n{json.dumps(context, ensure_ascii=False)}"
        
        return base_prompt
    
    def _get_default_system_prompt(self) -> str:
        """تعليمات النظام الافتراضية"""
        if self.settings.assistant_type == 'store':
            return """أنت مساعد ذكي لمتجر إلكتروني عربي. 
            
مهامك:
- مساعدة العملاء في البحث عن المنتجات
- الإجابة على أسئلة حول الشحن والدفع والمرتجعات
- تقديم توصيات للمنتجات
- المساعدة في تتبع الطلبات

قواعد:
- تحدث بالعربية الفصحى أو العامية حسب طريقة العميل
- كن ودوداً ومحترفاً
- أجب بإيجاز ووضوح
- إذا لم تعرف الإجابة، اقترح التواصل مع خدمة العملاء"""
        else:
            return """أنت مساعد ذكي لنظام Tony ERP المحاسبي.

مهامك:
- شرح وظائف النظام المختلفة
- إرشاد المستخدمين للقوائم والصفحات
- المساعدة في حل المشكلات
- تقديم نصائح لاستخدام النظام بفعالية

قواعد:
- تحدث بالعربية
- كن واضحاً ومحدداً
- قدم خطوات عملية
- إذا كان السؤال تقنياً جداً، اقترح التواصل مع الدعم الفني"""
