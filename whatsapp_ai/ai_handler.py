"""
AI Handler - معالج الذكاء الصناعي المباشر
يعمل بدون الحاجة لـ n8n
"""
import json
import logging
import requests
from django.conf import settings
from .models import SocialPlatformConfig, ProductKnowledgeBase

logger = logging.getLogger(__name__)


class AIHandler:
    """معالج الذكاء الصناعي للرد على الرسائل"""
    
    def __init__(self, platform='whatsapp'):
        self.platform = platform
        self.config = SocialPlatformConfig.objects.filter(
            platform=platform, 
            is_active=True
        ).first()
        
        if not self.config:
            # استخدم أي إعدادات متاحة
            self.config = SocialPlatformConfig.objects.filter(is_active=True).first()
    
    def get_products_context(self):
        """الحصول على سياق المنتجات للـ AI"""
        products = ProductKnowledgeBase.objects.filter(is_active=True)[:50]
        
        products_text = "المنتجات المتوفرة:\n"
        for p in products:
            price_text = f"{p.price} {p.currency}" if p.price else "اتصل للسعر"
            stock_text = "متوفر" if p.in_stock else "غير متوفر حالياً"
            products_text += f"- {p.product_name} ({p.product_code}): {price_text} - {stock_text}\n"
            if p.description:
                products_text += f"  الوصف: {p.description[:100]}...\n"
        
        return products_text
    
    def get_system_prompt(self):
        """الحصول على التعليمات الأساسية للـ AI"""
        base_prompt = self.config.system_prompt if self.config else """
أنت مساعد مبيعات ذكي لشركة بيع منتجات.
مهمتك:
1. الترحيب بالعملاء بطريقة ودودة واحترافية
2. فهم احتياجاتهم وتقديم المنتجات المناسبة
3. الإجابة على الأسئلة بدقة
4. تشجيع العميل على الشراء بطريقة لطيفة
5. تسجيل اهتمامات العميل

كن مهذباً، سريعاً في الرد، ومفيداً.
"""
        products_context = self.get_products_context()
        
        full_prompt = f"""{base_prompt}

{products_context}

تعليمات إضافية:
- إذا سأل العميل عن منتج غير موجود، اقترح منتجات مشابهة
- إذا طلب السعر، أعطه السعر بوضوح
- إذا أراد الشراء، اطلب منه بياناته (الاسم ورقم الهاتف)
- كن مختصراً ولا تكتب ردود طويلة جداً
- استخدم الإيموجي باعتدال 🙂
"""
        return full_prompt
    
    def generate_response_openai(self, conversation_history, user_message):
        """توليد رد باستخدام OpenAI"""
        try:
            api_key = self.config.ai_api_key if self.config else settings.OPENAI_API_KEY
            model = self.config.ai_model if self.config else 'gpt-3.5-turbo'
            
            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                logger.warning("OpenAI API key not configured")
                return None, "لم يتم تكوين مفتاح OpenAI"
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            messages = [
                {'role': 'system', 'content': self.get_system_prompt()}
            ]
            
            # إضافة تاريخ المحادثة
            for msg in conversation_history[-10:]:  # آخر 10 رسائل
                role = 'assistant' if msg['direction'] == 'outbound' else 'user'
                messages.append({'role': role, 'content': msg['content']})
            
            # إضافة الرسالة الحالية
            messages.append({'role': 'user', 'content': user_message})
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': 500,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                return ai_response, None
            else:
                logger.error(f"OpenAI error: {response.status_code} - {response.text}")
                return None, f"OpenAI error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}")
            return None, str(e)
    
    def generate_response_anthropic(self, conversation_history, user_message):
        """توليد رد باستخدام Anthropic Claude"""
        try:
            api_key = self.config.ai_api_key if self.config else getattr(settings, 'ANTHROPIC_API_KEY', '')
            model = self.config.ai_model if self.config else 'claude-3-sonnet-20240229'
            
            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                logger.warning("Anthropic API key not configured")
                return None, "لم يتم تكوين مفتاح Anthropic"
            
            headers = {
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            
            messages = []
            for msg in conversation_history[-10:]:
                role = 'assistant' if msg['direction'] == 'outbound' else 'user'
                messages.append({'role': role, 'content': msg['content']})
            
            messages.append({'role': 'user', 'content': user_message})
            
            payload = {
                'model': model,
                'max_tokens': 500,
                'system': self.get_system_prompt(),
                'messages': messages
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['content'][0]['text']
                return ai_response, None
            else:
                logger.error(f"Anthropic error: {response.status_code} - {response.text}")
                return None, f"Anthropic error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error generating Anthropic response: {str(e)}")
            return None, str(e)
    
    def generate_response_gemini(self, conversation_history, user_message):
        """توليد رد باستخدام Google Gemini"""
        try:
            api_key = self.config.ai_api_key if self.config else getattr(settings, 'GEMINI_API_KEY', '')
            model = self.config.ai_model if self.config else 'gemini-pro'
            
            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                logger.warning("Gemini API key not configured")
                return None, "لم يتم تكوين مفتاح Gemini"
            
            # بناء المحادثة
            history_text = ""
            for msg in conversation_history[-10:]:
                role = "المساعد" if msg['direction'] == 'outbound' else "العميل"
                history_text += f"{role}: {msg['content']}\n"
            
            full_prompt = f"""{self.get_system_prompt()}

تاريخ المحادثة:
{history_text}

العميل: {user_message}

المساعد:"""
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            
            payload = {
                'contents': [{'parts': [{'text': full_prompt}]}],
                'generationConfig': {
                    'maxOutputTokens': 500,
                    'temperature': 0.7
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['candidates'][0]['content']['parts'][0]['text']
                return ai_response, None
            else:
                logger.error(f"Gemini error: {response.status_code} - {response.text}")
                return None, f"Gemini error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            return None, str(e)
    
    def generate_response(self, conversation_history, user_message):
        """توليد رد باستخدام المزود المحدد"""
        provider = 'openai'
        if self.config:
            provider = self.config.ai_provider
        
        if provider == 'openai':
            return self.generate_response_openai(conversation_history, user_message)
        elif provider == 'anthropic':
            return self.generate_response_anthropic(conversation_history, user_message)
        elif provider == 'gemini':
            return self.generate_response_gemini(conversation_history, user_message)
        else:
            return self.generate_response_openai(conversation_history, user_message)
    
    def extract_intent_and_products(self, message):
        """استخراج النية والمنتجات من الرسالة"""
        message_lower = message.lower()
        
        # كلمات مفتاحية للنوايا
        intents = {
            'inquiry': ['سعر', 'كم', 'متوفر', 'موجود', 'عندكم', 'اسأل', 'استفسار'],
            'purchase': ['أريد', 'عايز', 'اشتري', 'طلب', 'احجز'],
            'complaint': ['مشكلة', 'شكوى', 'سيء', 'رديء', 'متأخر'],
            'greeting': ['مرحبا', 'السلام', 'هلا', 'اهلا', 'صباح', 'مساء']
        }
        
        detected_intent = 'general'
        for intent, keywords in intents.items():
            for keyword in keywords:
                if keyword in message_lower:
                    detected_intent = intent
                    break
        
        # البحث عن المنتجات المذكورة
        products = ProductKnowledgeBase.objects.filter(is_active=True)
        mentioned_products = []
        
        for product in products:
            if product.product_name.lower() in message_lower:
                mentioned_products.append(product.product_name)
            elif product.product_code and product.product_code.lower() in message_lower:
                mentioned_products.append(product.product_name)
            # البحث في الكلمات المفتاحية
            for keyword in product.keywords or []:
                if keyword.lower() in message_lower:
                    mentioned_products.append(product.product_name)
                    break
        
        return detected_intent, list(set(mentioned_products))
    
    def calculate_conversion_probability(self, conversation):
        """حساب احتمالية التحويل"""
        score = 0.1  # نقطة بداية
        
        # عدد الرسائل
        if conversation.messages_count >= 3:
            score += 0.1
        if conversation.messages_count >= 5:
            score += 0.1
        
        # المنتجات المهتم بها
        if conversation.interested_products:
            score += 0.2
            if len(conversation.interested_products) >= 2:
                score += 0.1
        
        # إذا طلب السعر
        # (يمكن تحسين هذا بتحليل الرسائل)
        score += 0.1
        
        return min(score, 1.0)


def process_message_with_ai(conversation, message_content):
    """
    معالجة رسالة باستخدام AI وإرجاع الرد
    هذه الدالة تُستخدم مباشرة بدون n8n
    """
    try:
        handler = AIHandler(conversation.platform)
        
        # الحصول على تاريخ المحادثة
        history = list(conversation.messages.order_by('-created_at')[:10].values(
            'direction', 'content', 'created_at'
        ))
        history.reverse()
        
        # توليد الرد
        ai_response, error = handler.generate_response(history, message_content)
        
        if error:
            logger.error(f"AI generation error: {error}")
            # رد افتراضي في حالة الخطأ
            ai_response = "شكراً لتواصلك! سيتم الرد عليك في أقرب وقت من فريق المبيعات. 🙂"
        
        # استخراج النية والمنتجات
        intent, products = handler.extract_intent_and_products(message_content)
        
        # تحديث المحادثة
        if products:
            existing = conversation.interested_products or []
            conversation.interested_products = list(set(existing + products))
        
        conversation.conversion_probability = handler.calculate_conversion_probability(conversation)
        conversation.save()
        
        return {
            'response': ai_response,
            'intent': intent,
            'products': products,
            'conversion_probability': conversation.conversion_probability
        }
        
    except Exception as e:
        logger.error(f"Error in process_message_with_ai: {str(e)}", exc_info=True)
        return {
            'response': "شكراً لتواصلك! سيتم الرد عليك قريباً.",
            'intent': 'general',
            'products': [],
            'conversion_probability': 0.1
        }
