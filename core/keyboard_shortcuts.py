"""
اختصارات لوحة المفاتيح للنظام
Keyboard Shortcuts System
"""

KEYBOARD_SHORTCUTS = {
    # اختصارات عامة
    'general': {
        'Ctrl+S': {'action': 'save', 'description': 'حفظ'},
        'Ctrl+N': {'action': 'new', 'description': 'جديد'},
        'Ctrl+F': {'action': 'search', 'description': 'بحث'},
        'Ctrl+P': {'action': 'print', 'description': 'طباعة'},
        'Escape': {'action': 'cancel', 'description': 'إلغاء'},
        'F1': {'action': 'help', 'description': 'مساعدة'},
    },
    
    # اختصارات القيود المحاسبية
    'accounting': {
        'Ctrl+S': {'action': 'save_entry', 'description': 'حفظ القيد'},
        'Ctrl+D': {'action': 'duplicate_entry', 'description': 'نسخ القيد'},
        'Ctrl+E': {'action': 'edit_entry', 'description': 'تعديل القيد'},
        'F2': {'action': 'next_field', 'description': 'الحقل التالي'},
        'F3': {'action': 'search_account', 'description': 'بحث عن حساب'},
        'F4': {'action': 'calculator', 'description': 'الآلة الحاسبة'},
        'Ctrl+T': {'action': 'add_template', 'description': 'حفظ كقالب'},
        'Ctrl+L': {'action': 'load_template', 'description': 'تحميل قالب'},
        'Ctrl+B': {'action': 'balance_check', 'description': 'فحص التوازن'},
    },
    
    # اختصارات الفواتير
    'invoices': {
        'Ctrl+S': {'action': 'save_invoice', 'description': 'حفظ الفاتورة'},
        'Ctrl+P': {'action': 'print_invoice', 'description': 'طباعة'},
        'F5': {'action': 'add_item', 'description': 'إضافة صنف'},
        'F6': {'action': 'scan_barcode', 'description': 'مسح باركود'},
        'F7': {'action': 'select_customer', 'description': 'اختيار عميل'},
        'F8': {'action': 'payment', 'description': 'الدفع'},
        'F9': {'action': 'discount', 'description': 'خصم'},
        'F12': {'action': 'submit', 'description': 'إنهاء وحفظ'},
    },
    
    # اختصارات POS
    'pos': {
        'F1': {'action': 'cash', 'description': 'نقدي'},
        'F2': {'action': 'card', 'description': 'بطاقة'},
        'F3': {'action': 'change', 'description': 'حساب الباقي'},
        'F4': {'action': 'hold', 'description': 'تعليق'},
        'F5': {'action': 'recall', 'description': 'استرجاع'},
        'F8': {'action': 'cancel_item', 'description': 'إلغاء صنف'},
        'F9': {'action': 'cancel_all', 'description': 'إلغاء الكل'},
        'F12': {'action': 'print_receipt', 'description': 'طباعة الإيصال'},
        'Ctrl+O': {'action': 'open_cash', 'description': 'فتح الوردية'},
        'Ctrl+K': {'action': 'close_cash', 'description': 'إغلاق الوردية'},
    }
}


def get_shortcuts_for_module(module_name):
    """
    الحصول على الاختصارات لوحدة معينة
    
    Args:
        module_name: اسم الوحدة (general, accounting, invoices, pos)
    
    Returns:
        dict مع الاختصارات
    """
    shortcuts = KEYBOARD_SHORTCUTS.get('general', {}).copy()
    shortcuts.update(KEYBOARD_SHORTCUTS.get(module_name, {}))
    return shortcuts


def get_all_shortcuts():
    """الحصول على جميع الاختصارات"""
    return KEYBOARD_SHORTCUTS
