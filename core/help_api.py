"""
API للمساعدة السياقية
Contextual Help API
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# قاموس المساعدة السياقية
HELP_CONTENT = {
    # لوحة المعلومات
    'dashboard': {
        'title': 'لوحة المعلومات',
        'content': 'لوحة المعلومات الرئيسية تعرض ملخص شامل لأداء الشركة',
        'tips': [
            'انقر على أي مؤشر للحصول على تفاصيل أكثر',
            'استخدم الفلاتر لتخصيص البيانات',
            'اضغط Ctrl+Shift+K لفتح اختصارات لوحة المفاتيح'
        ]
    },
    
    # المبيعات
    'sales': {
        'title': 'نظام المبيعات',
        'content': 'إدارة جميع عمليات البيع والفواتير',
        'tips': [
            'اضغط Ctrl+S لحفظ الفاتورة',
            'استخدم F2 للتعديل السريع',
            'اضغط Tab للتنقل بين الحقول'
        ]
    },
    
    # المخزون
    'inventory': {
        'title': 'إدارة المخزون',
        'content': 'تتبع المنتجات والكميات والحركات',
        'tips': [
            'راقب التنبيهات الحمراء للمنتجات المنخفضة',
            'استخدم البحث السريع للعثور على المنتجات',
            'راجع حركة المخزون بانتظام'
        ]
    },
    
    # المشتريات
    'purchases': {
        'title': 'إدارة المشتريات',
        'content': 'طلبات الشراء والموردين',
        'tips': [
            'تابع مؤشر SLA للطلبات المتأخرة',
            'قارن أسعار الموردين',
            'استخدم الموافقات الجماعية لتوفير الوقت'
        ]
    },
    
    # المحاسبة
    'accounting': {
        'title': 'النظام المحاسبي',
        'content': 'القيود والحسابات والتقارير المالية',
        'tips': [
            'استخدم القوالب للقيود المتكررة',
            'راجع التقارير اليومية',
            'تأكد من توازن القيود'
        ]
    },
    
    # الموارد البشرية
    'hr': {
        'title': 'الموارد البشرية',
        'content': 'إدارة الموظفين والرواتب',
        'tips': [
            'حدث بيانات الموظفين بانتظام',
            'راجع الحضور يومياً',
            'خطط للإجازات مسبقاً'
        ]
    },
    
    # الإنتاج
    'production': {
        'title': 'إدارة الإنتاج',
        'content': 'أوامر الإنتاج والتصنيع',
        'tips': [
            'تابع التقدم اليومي',
            'راقب استهلاك المواد الخام',
            'سجل المشاكل فوراً'
        ]
    },
    
    # نقاط البيع
    'pos': {
        'title': 'نقاط البيع',
        'content': 'نظام البيع السريع',
        'tips': [
            'استخدم الباركود للسرعة',
            'F1 للبحث عن منتج',
            'Ctrl+P للطباعة المباشرة'
        ]
    },
    
    # التقارير
    'reports': {
        'title': 'التقارير',
        'content': 'تقارير شاملة لجميع الأقسام',
        'tips': [
            'صدّر التقارير لـ Excel',
            'جدول التقارير الدورية',
            'استخدم الرسوم البيانية'
        ]
    },
    
    # الموافقات
    'approvals': {
        'title': 'نظام الموافقات',
        'content': 'مراجعة واعتماد الطلبات',
        'tips': [
            'استخدم الموافقة/الرفض الجماعي',
            'أضف ملاحظات توضيحية',
            'تابع الطلبات المعلقة'
        ]
    },
    
    # الإشعارات
    'notifications': {
        'title': 'الإشعارات',
        'content': 'جميع التنبيهات والإشعارات',
        'tips': [
            'خصص إعدادات الإشعارات',
            'فعّل إشعارات البريد الإلكتروني',
            'راجع الإشعارات المهمة أولاً'
        ]
    },
    
    # عام - افتراضي
    'default': {
        'title': 'مساعدة Tony ERP',
        'content': 'نظام إدارة الأعمال الشامل',
        'tips': [
            'اضغط Ctrl+Shift+K لاختصارات لوحة المفاتيح',
            'استخدم البحث السريع للتنقل',
            'راجع الوثائق للمزيد'
        ]
    }
}

# اختصارات لوحة المفاتيح
KEYBOARD_SHORTCUTS = {
    'global': [
        {'keys': 'Ctrl+Shift+K', 'action': 'إظهار/إخفاء اختصارات لوحة المفاتيح'},
        {'keys': 'Ctrl+/', 'action': 'البحث السريع'},
        {'keys': 'Alt+1', 'action': 'الذهاب للرئيسية'},
        {'keys': 'Alt+S', 'action': 'الذهاب للمبيعات'},
        {'keys': 'Alt+I', 'action': 'الذهاب للمخزون'},
        {'keys': 'Alt+P', 'action': 'الذهاب للمشتريات'},
        {'keys': 'Alt+A', 'action': 'الذهاب للمحاسبة'},
        {'keys': 'Escape', 'action': 'إغلاق النوافذ المنبثقة'},
    ],
    'forms': [
        {'keys': 'Ctrl+S', 'action': 'حفظ'},
        {'keys': 'Ctrl+Enter', 'action': 'حفظ وإغلاق'},
        {'keys': 'Tab', 'action': 'الحقل التالي'},
        {'keys': 'Shift+Tab', 'action': 'الحقل السابق'},
        {'keys': 'F2', 'action': 'تعديل'},
    ],
    'tables': [
        {'keys': '↑/↓', 'action': 'التنقل بين الصفوف'},
        {'keys': 'Enter', 'action': 'فتح التفاصيل'},
        {'keys': 'Delete', 'action': 'حذف (إذا مسموح)'},
        {'keys': 'Ctrl+A', 'action': 'تحديد الكل'},
    ],
    'pos': [
        {'keys': 'F1', 'action': 'بحث منتج'},
        {'keys': 'F4', 'action': 'فتح الآلة الحاسبة'},
        {'keys': 'F8', 'action': 'تعليق الفاتورة'},
        {'keys': 'F12', 'action': 'إنهاء البيع'},
        {'keys': 'Ctrl+P', 'action': 'طباعة'},
    ]
}


class ContextualHelpAPIView(APIView):
    """API للمساعدة السياقية"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على محتوى المساعدة"""
        context = request.query_params.get('context', 'default')
        
        # البحث عن المحتوى المناسب
        help_data = HELP_CONTENT.get(context, HELP_CONTENT['default'])
        
        return Response({
            'success': True,
            'data': help_data,
            'context': context
        })


class KeyboardShortcutsAPIView(APIView):
    """API لاختصارات لوحة المفاتيح"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على اختصارات لوحة المفاتيح"""
        category = request.query_params.get('category', None)
        
        if category and category in KEYBOARD_SHORTCUTS:
            data = {category: KEYBOARD_SHORTCUTS[category]}
        else:
            data = KEYBOARD_SHORTCUTS
        
        return Response({
            'success': True,
            'data': data
        })


class HelpTooltipsAPIView(APIView):
    """API لـ tooltips المساعدة للحقول"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على tooltips المساعدة لجميع الحقول"""
        tooltips = {}
        for key, help_data in HELP_CONTENT.items():
            if key == 'default':
                continue
            tooltips[key] = {
                'title': help_data.get('title', ''),
                'content': help_data.get('content', ''),
                'tips': help_data.get('tips', [])
            }
        return Response(tooltips)


class HelpSearchAPIView(APIView):
    """البحث في المساعدة"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """البحث في محتوى المساعدة"""
        query = request.query_params.get('q', '').strip().lower()
        
        if not query:
            return Response({
                'success': False,
                'error': 'يرجى إدخال كلمة بحث'
            })
        
        results = []
        for key, help_data in HELP_CONTENT.items():
            if key == 'default':
                continue
            
            # البحث في العنوان والمحتوى
            if query in help_data['title'].lower() or query in help_data['content'].lower():
                results.append({
                    'key': key,
                    'title': help_data['title'],
                    'content': help_data['content']
                })
            else:
                # البحث في النصائح
                for tip in help_data.get('tips', []):
                    if query in tip.lower():
                        results.append({
                            'key': key,
                            'title': help_data['title'],
                            'content': tip
                        })
                        break
        
        return Response({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
