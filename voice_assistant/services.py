"""
خدمة معالجة الأوامر الصوتية
Voice Command Processing Service
"""

import re
from django.urls import reverse
from django.utils import timezone


class VoiceCommandProcessor:
    """معالج الأوامر الصوتية"""
    
    # أنماط الأوامر الشائعة
    COMMAND_PATTERNS = {
        # التنقل
        'navigation': [
            (r'(افتح|اذهب|روح)\s*(إلى|الى|ل)?\s*(.+)', 'navigate'),
            (r'(خذني|وديني)\s*(إلى|الى|ل)?\s*(.+)', 'navigate'),
        ],
        # الإنشاء
        'create': [
            (r'(أنشئ|انشئ|اعمل|سجل)\s*(فاتورة|فاتوره)\s*(جديدة|جديده)?', 'create_invoice'),
            (r'(أنشئ|انشئ|اعمل)\s*(عميل|زبون)\s*(جديد)?', 'create_customer'),
            (r'(أنشئ|انشئ|اعمل)\s*(منتج|صنف)\s*(جديد)?', 'create_product'),
            (r'(أنشئ|انشئ|اعمل)\s*(طلب|أوردر)\s*(جديد)?', 'create_order'),
            (r'(أنشئ|انشئ|اعمل)\s*(مهمة|تاسك)\s*(جديدة|جديده)?', 'create_task'),
        ],
        # البحث
        'search': [
            (r'(ابحث|دور)\s*(عن)?\s*(.+)', 'search'),
            (r'(وين|فين|أين)\s*(.+)', 'search'),
        ],
        # التقارير
        'report': [
            (r'(تقرير|ريبورت)\s*(المبيعات|البيعات)', 'sales_report'),
            (r'(تقرير|ريبورت)\s*(المخزون|الستوك)', 'inventory_report'),
            (r'(تقرير|ريبورت)\s*(الأرباح|الربحية)', 'profit_report'),
            (r'كم\s*(المبيعات|البيعات)\s*(اليوم|هذا الشهر)?', 'sales_summary'),
            (r'كم\s*(المخزون|الستوك)\s*(المتبقي)?', 'inventory_summary'),
        ],
        # الاستعلامات
        'query': [
            (r'كم\s*(رصيد|مديونية)\s*(العميل|الزبون)?\s*(.+)', 'customer_balance'),
            (r'(معلومات|بيانات)\s*(العميل|الزبون)?\s*(.+)', 'customer_info'),
            (r'(كم|ما)\s*سعر\s*(.+)', 'product_price'),
        ],
        # الإجراءات
        'action': [
            (r'(احذف|امسح)\s*(.+)', 'delete'),
            (r'(عدل|حدث)\s*(.+)', 'edit'),
            (r'(اطبع|طباعة)\s*(.+)', 'print'),
            (r'(أرسل|ارسل)\s*(.+)', 'send'),
        ],
    }
    
    # خريطة الصفحات
    PAGE_MAP = {
        'الرئيسية': 'core:dashboard',
        'لوحة التحكم': 'core:dashboard',
        'المبيعات': 'sales:dashboard',
        'الفواتير': 'sales:invoice_list',
        'العملاء': 'crm:customer_list',
        'المنتجات': 'inventory:product_list',
        'المخزون': 'inventory:dashboard',
        'المشتريات': 'purchases:dashboard',
        'الموردين': 'purchases:supplier_list',
        'الموظفين': 'hr:employee_list',
        'المحاسبة': 'accounting:dashboard',
        'التقارير': 'reports:dashboard',
        'الإعدادات': 'core:settings',
        'الملف الشخصي': 'users:profile',
        'نقطة البيع': 'pos:dashboard',
        'المهام': 'tasks:dashboard',
        'الدردشة': 'chat:inbox',
    }
    
    def __init__(self, user):
        self.user = user
    
    def process(self, text):
        """معالجة الأمر الصوتي"""
        text = self._normalize_text(text)
        
        # البحث عن نمط مطابق
        for cmd_type, patterns in self.COMMAND_PATTERNS.items():
            for pattern, action in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return self._execute_action(cmd_type, action, match, text)
        
        # البحث في الاختصارات المخصصة
        shortcut_result = self._check_shortcuts(text)
        if shortcut_result:
            return shortcut_result
        
        # لم يتم التعرف على الأمر
        return {
            'success': False,
            'response': 'عذراً، لم أفهم الأمر. يمكنك قول "افتح المبيعات" أو "أنشئ فاتورة جديدة"',
            'suggestions': self._get_suggestions()
        }
    
    def _normalize_text(self, text):
        """تطبيع النص"""
        # إزالة التشكيل
        text = re.sub(r'[\u064B-\u0652]', '', text)
        # تحويل الأرقام العربية
        arabic_nums = '٠١٢٣٤٥٦٧٨٩'
        for i, num in enumerate(arabic_nums):
            text = text.replace(num, str(i))
        return text.strip()
    
    def _execute_action(self, cmd_type, action, match, text):
        """تنفيذ الإجراء"""
        if action == 'navigate':
            destination = match.group(3) if match.lastindex >= 3 else match.group(2)
            return self._navigate(destination)
        
        elif action == 'create_invoice':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('sales:invoice_create'),
                'response': 'جاري فتح صفحة إنشاء فاتورة جديدة'
            }
        
        elif action == 'create_customer':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('crm:customer_create'),
                'response': 'جاري فتح صفحة إضافة عميل جديد'
            }
        
        elif action == 'create_product':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('inventory:product_create'),
                'response': 'جاري فتح صفحة إضافة منتج جديد'
            }
        
        elif action == 'create_task':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('tasks:task_create'),
                'response': 'جاري فتح صفحة إنشاء مهمة جديدة'
            }
        
        elif action == 'search':
            query = match.group(3) if match.lastindex >= 3 else match.group(2)
            return {
                'success': True,
                'action': 'search',
                'query': query,
                'response': f'جاري البحث عن: {query}'
            }
        
        elif action == 'sales_report':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('reports:sales_report'),
                'response': 'جاري فتح تقرير المبيعات'
            }
        
        elif action == 'inventory_report':
            return {
                'success': True,
                'action': 'redirect',
                'url': reverse('reports:inventory_report'),
                'response': 'جاري فتح تقرير المخزون'
            }
        
        elif action == 'sales_summary':
            return self._get_sales_summary()
        
        elif action == 'inventory_summary':
            return self._get_inventory_summary()
        
        return {
            'success': False,
            'response': 'عذراً، لم أتمكن من تنفيذ هذا الإجراء'
        }
    
    def _navigate(self, destination):
        """التنقل إلى صفحة"""
        destination = destination.strip()
        
        # البحث في خريطة الصفحات
        for page_name, url_name in self.PAGE_MAP.items():
            if page_name in destination or destination in page_name:
                try:
                    url = reverse(url_name)
                    return {
                        'success': True,
                        'action': 'redirect',
                        'url': url,
                        'response': f'جاري الانتقال إلى {page_name}'
                    }
                except:
                    pass
        
        return {
            'success': False,
            'response': f'عذراً، لم أجد صفحة باسم "{destination}"',
            'suggestions': list(self.PAGE_MAP.keys())[:5]
        }
    
    def _check_shortcuts(self, text):
        """التحقق من الاختصارات المخصصة"""
        from .models import VoiceShortcut
        
        shortcuts = VoiceShortcut.objects.filter(
            user=self.user,
            is_active=True
        )
        
        for shortcut in shortcuts:
            if shortcut.trigger_phrase.lower() in text.lower():
                shortcut.usage_count += 1
                shortcut.save()
                
                return {
                    'success': True,
                    'action': 'redirect',
                    'url': shortcut.action_url,
                    'response': shortcut.description or f'تنفيذ: {shortcut.trigger_phrase}'
                }
        
        return None
    
    def _get_suggestions(self):
        """اقتراحات الأوامر"""
        return [
            'افتح المبيعات',
            'أنشئ فاتورة جديدة',
            'ابحث عن عميل',
            'تقرير المبيعات',
            'كم المبيعات اليوم',
        ]
    
    def _get_sales_summary(self):
        """ملخص المبيعات"""
        try:
            from sales.models import Invoice
            from django.db.models import Sum
            from datetime import date
            
            today = date.today()
            today_sales = Invoice.objects.filter(
                date__date=today
            ).aggregate(total=Sum('total'))['total'] or 0
            
            return {
                'success': True,
                'action': 'speak',
                'response': f'إجمالي مبيعات اليوم هو {today_sales:,.2f} ج.م',
                'data': {'today_sales': float(today_sales)}
            }
        except:
            return {
                'success': False,
                'response': 'عذراً، لم أتمكن من الحصول على بيانات المبيعات'
            }
    
    def _get_inventory_summary(self):
        """ملخص المخزون"""
        try:
            from inventory.models import Product
            
            total_products = Product.objects.count()
            low_stock = Product.objects.filter(
                quantity__lte=models.F('min_quantity')
            ).count()
            
            return {
                'success': True,
                'action': 'speak',
                'response': f'لديك {total_products} منتج، منها {low_stock} منتجات بمخزون منخفض',
                'data': {
                    'total_products': total_products,
                    'low_stock': low_stock
                }
            }
        except:
            return {
                'success': False,
                'response': 'عذراً، لم أتمكن من الحصول على بيانات المخزون'
            }
