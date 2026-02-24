"""
أمر إنشاء بيانات افتراضية للمساعد الذكي
"""
from django.core.management.base import BaseCommand
from ai_assistant.models import AIAssistantSettings, FAQ, QuickReply


class Command(BaseCommand):
    help = 'إنشاء بيانات افتراضية للمساعد الذكي'

    def handle(self, *args, **options):
        self.stdout.write('جاري إنشاء بيانات المساعد الذكي...')
        
        # ===== إعدادات المساعد =====
        store_settings, created = AIAssistantSettings.objects.get_or_create(
            assistant_type='store',
            defaults={
                'name': 'مساعد المتجر الذكي',
                'welcome_message': 'أهلاً بك في متجرنا! 🛍️ أنا مساعدك الذكي، كيف يمكنني مساعدتك اليوم؟',
                'system_prompt': '''أنت مساعد ذكي لمتجر إلكتروني عربي متخصص في المراتب والمفروشات.
مهامك:
- مساعدة العملاء في البحث عن المنتجات
- الإجابة على أسئلة الشحن والدفع والمرتجعات
- تقديم توصيات مخصصة
- المساعدة في تتبع الطلبات

كن ودوداً واستخدم العربية الفصحى أو العامية المصرية حسب أسلوب العميل.''',
                'is_active': True,
                'enable_product_search': True,
                'enable_order_tracking': True,
                'enable_faq': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✅ تم إنشاء إعدادات مساعد المتجر'))
        
        system_settings, created = AIAssistantSettings.objects.get_or_create(
            assistant_type='system',
            defaults={
                'name': 'مساعد Tony ERP',
                'welcome_message': 'مرحباً بك في مساعد Tony ERP الذكي! 💼 أنا هنا لمساعدتك في استخدام النظام.',
                'system_prompt': '''أنت مساعد ذكي لنظام Tony ERP المحاسبي.
مهامك:
- شرح وظائف النظام المختلفة (المبيعات، المشتريات، المخزون، المحاسبة، إلخ)
- إرشاد المستخدمين للقوائم والصفحات المناسبة
- المساعدة في حل المشكلات الشائعة
- تقديم نصائح لاستخدام النظام بفعالية

تحدث بالعربية وكن واضحاً ومحدداً في إجاباتك.''',
                'is_active': True,
                'enable_faq': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✅ تم إنشاء إعدادات مساعد النظام'))
        
        # ===== أسئلة شائعة للمتجر =====
        store_faqs = [
            {
                'category': 'shipping',
                'question': 'كم مدة التوصيل؟',
                'answer': '🚚 مدة التوصيل من 2-5 أيام عمل حسب موقعك.\n\n• القاهرة والجيزة: 2-3 أيام\n• المحافظات: 3-5 أيام\n• يمكنك تتبع طلبك من صفحة "طلباتي"',
                'keywords': 'توصيل,شحن,مدة,كام يوم,وصول',
            },
            {
                'category': 'shipping',
                'question': 'هل الشحن مجاني؟',
                'answer': '📦 نعم! الشحن مجاني للطلبات فوق 2000 جنيه.\n\nللطلبات أقل من ذلك، تكلفة الشحن:\n• داخل القاهرة: 50 جنيه\n• المحافظات: 75-100 جنيه',
                'keywords': 'شحن مجاني,تكلفة الشحن,سعر التوصيل,مصاريف الشحن',
            },
            {
                'category': 'payment',
                'question': 'ما هي طرق الدفع المتاحة؟',
                'answer': '💳 طرق الدفع المتاحة:\n\n• الدفع عند الاستلام (كاش)\n• بطاقات الائتمان (Visa/Mastercard)\n• التحويل البنكي\n• المحافظ الإلكترونية (فودافون كاش، إلخ)\n\nجميع المعاملات آمنة ومشفرة 🔒',
                'keywords': 'دفع,فلوس,فيزا,كاش,تحويل,طريقة الدفع',
            },
            {
                'category': 'returns',
                'question': 'ما هي سياسة الإرجاع؟',
                'answer': '↩️ سياسة الإرجاع والاستبدال:\n\n• يمكنك إرجاع المنتج خلال 14 يوم من الاستلام\n• المنتج يجب أن يكون بحالته الأصلية مع العبوة\n• الاسترداد خلال 3-5 أيام عمل\n• للمراتب: يمكن الاستبدال خلال 30 يوم (تجربة النوم)\n\nتواصل معنا لبدء طلب الإرجاع.',
                'keywords': 'إرجاع,رد,استبدال,مرتجع,ترجيع',
            },
            {
                'category': 'products',
                'question': 'ما الفرق بين المراتب الطبية والعادية؟',
                'answer': '🛏️ الفرق بين المراتب:\n\n**المراتب الطبية:**\n• دعم أفضل للعمود الفقري\n• مناسبة لمن يعانون من آلام الظهر\n• عمر افتراضي أطول\n• سعر أعلى\n\n**المراتب العادية:**\n• مريحة للاستخدام اليومي\n• سعر اقتصادي\n• متوفرة بأحجام متنوعة\n\nتريد مساعدة في اختيار المرتبة المناسبة؟',
                'keywords': 'مرتبة طبية,فرق,مقارنة,أفضل مرتبة',
            },
        ]
        
        for faq_data in store_faqs:
            faq, created = FAQ.objects.get_or_create(
                assistant_type='store',
                question=faq_data['question'],
                defaults={
                    'category': faq_data['category'],
                    'answer': faq_data['answer'],
                    'keywords': faq_data['keywords'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✅ سؤال: {faq_data["question"][:30]}...')
        
        # ===== أسئلة شائعة للنظام =====
        system_faqs = [
            {
                'category': 'general',
                'question': 'كيف أضيف فاتورة مبيعات جديدة؟',
                'answer': '📝 لإضافة فاتورة مبيعات جديدة:\n\n1. اذهب إلى قائمة "المبيعات"\n2. اختر "فواتير المبيعات"\n3. اضغط زر "فاتورة جديدة"\n4. اختر العميل وأضف المنتجات\n5. راجع البيانات واضغط "حفظ"\n\nنصيحة: يمكنك استخدام الباركود لإضافة المنتجات بسرعة.',
                'keywords': 'فاتورة,مبيعات,بيع,إضافة فاتورة',
            },
            {
                'category': 'general',
                'question': 'أين أجد التقارير المالية؟',
                'answer': '📊 للوصول للتقارير المالية:\n\n1. اذهب إلى قائمة "المحاسبة"\n2. اختر "التقارير المالية"\n3. ستجد:\n   • الميزانية العمومية\n   • قائمة الدخل\n   • التدفقات النقدية\n   • ميزان المراجعة\n\nيمكنك تصدير أي تقرير لـ PDF أو Excel.',
                'keywords': 'تقارير,مالية,ميزانية,دخل,محاسبة',
            },
            {
                'category': 'general',
                'question': 'كيف أضيف منتج جديد للمخزون؟',
                'answer': '📦 لإضافة منتج جديد:\n\n1. اذهب إلى "المخزون" > "المنتجات"\n2. اضغط "منتج جديد"\n3. أدخل البيانات:\n   • اسم المنتج والوصف\n   • السعر والتكلفة\n   • الفئة والوحدة\n   • الباركود (اختياري)\n4. اضغط "حفظ"\n\nلإضافة كمية، استخدم "إذن إضافة للمخزون".',
                'keywords': 'منتج,مخزون,إضافة,جديد,صنف',
            },
            {
                'category': 'general',
                'question': 'كيف أطبع فاتورة؟',
                'answer': '🖨️ لطباعة فاتورة:\n\n1. افتح الفاتورة المراد طباعتها\n2. اضغط زر "طباعة" أو أيقونة الطابعة\n3. اختر:\n   • طباعة مباشرة: للطباعة الفورية\n   • تحميل PDF: لحفظها وطباعتها لاحقاً\n\nيمكنك تخصيص شكل الفاتورة من "الإعدادات" > "قوالب الطباعة".',
                'keywords': 'طباعة,فاتورة,طبع,pdf,printer',
            },
        ]
        
        for faq_data in system_faqs:
            faq, created = FAQ.objects.get_or_create(
                assistant_type='system',
                question=faq_data['question'],
                defaults={
                    'category': faq_data['category'],
                    'answer': faq_data['answer'],
                    'keywords': faq_data['keywords'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  ✅ سؤال: {faq_data["question"][:30]}...')
        
        # ===== ردود سريعة للمتجر =====
        store_quick_replies = [
            {'title': 'البحث عن منتج', 'content': 'أريد البحث عن منتج', 'icon': 'bi-search'},
            {'title': 'العروض', 'content': 'ما هي العروض المتاحة؟', 'icon': 'bi-percent'},
            {'title': 'تتبع الطلب', 'content': 'أريد تتبع طلبي', 'icon': 'bi-box-seam'},
            {'title': 'الشحن', 'content': 'ما هي طرق الشحن؟', 'icon': 'bi-truck'},
            {'title': 'الدفع', 'content': 'ما هي طرق الدفع؟', 'icon': 'bi-credit-card'},
        ]
        
        for i, qr_data in enumerate(store_quick_replies):
            qr, created = QuickReply.objects.get_or_create(
                assistant_type='store',
                title=qr_data['title'],
                defaults={
                    'content': qr_data['content'],
                    'icon': qr_data['icon'],
                    'order': i,
                    'is_active': True,
                }
            )
        
        # ===== ردود سريعة للنظام =====
        system_quick_replies = [
            {'title': 'إضافة فاتورة', 'content': 'كيف أضيف فاتورة جديدة؟', 'icon': 'bi-receipt'},
            {'title': 'التقارير', 'content': 'أين أجد التقارير المالية؟', 'icon': 'bi-graph-up'},
            {'title': 'المنتجات', 'content': 'كيف أضيف منتج جديد؟', 'icon': 'bi-box'},
            {'title': 'المخزون', 'content': 'أريد مساعدة في إدارة المخزون', 'icon': 'bi-boxes'},
            {'title': 'الطباعة', 'content': 'كيف أطبع فاتورة؟', 'icon': 'bi-printer'},
        ]
        
        for i, qr_data in enumerate(system_quick_replies):
            qr, created = QuickReply.objects.get_or_create(
                assistant_type='system',
                title=qr_data['title'],
                defaults={
                    'content': qr_data['content'],
                    'icon': qr_data['icon'],
                    'order': i,
                    'is_active': True,
                }
            )
        
        self.stdout.write(self.style.SUCCESS('\n✅ تم إنشاء بيانات المساعد الذكي بنجاح!'))
