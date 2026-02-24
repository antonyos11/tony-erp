# -*- coding: utf-8 -*-
"""
ملف الإعدادات لنظام الطباعة
يمكنك تعديل هذه الإعدادات حسب احتياجاتك
"""

# ============================================
# إعدادات الاتصال
# ============================================

# المنفذ الذي ستعمل عليه الخدمة
PORT = 9876

# العنوان (استخدم localhost للأمان)
HOST = 'localhost'

# هل تريد السماح بالاتصالات من أجهزة أخرى؟
# تحذير: لا تفعّل هذا إلا إذا كنت متأكدًا (مخاطر أمنية)
ALLOW_REMOTE = False

# إذا فعّلت ALLOW_REMOTE، استخدم هذا:
# HOST = '0.0.0.0'  # للسماح من أي جهاز في الشبكة
# أو حدد IP معين:
# HOST = '192.168.1.100'


# ============================================
# إعدادات الطباعة
# ============================================

# الطابعة الافتراضية (اتركها فارغة لاستخدام طابعة النظام الافتراضية)
DEFAULT_PRINTER = None

# أو حدد طابعة محددة:
# DEFAULT_PRINTER = "EPSON TM-T88V"

# حجم الورق الافتراضي
PAPER_SIZE = 'A4'  # A4, Letter, 80mm (للطابعات الحرارية)

# هوامش الصفحة (بالملليمتر)
MARGINS = {
    'top': 10,
    'bottom': 10,
    'left': 10,
    'right': 10
}

# ترميز النص للطابعات الحرارية
# cp864 = للعربية في معظم الطابعات
# cp720 = بديل للعربية
# utf-8 = للطابعات الحديثة
THERMAL_ENCODING = 'cp864'


# ============================================
# إعدادات الطابعات الحرارية (ESC/POS)
# ============================================

# هل تريد تفعيل قص الورق التلقائي؟
AUTO_CUT = True

# هل تريد فتح درج النقود بعد الطباعة؟
OPEN_CASH_DRAWER = False

# عدد النسخ المطبوعة افتراضيًا
DEFAULT_COPIES = 1

# سرعة الطباعة (0-9، 9 = أسرع)
PRINT_SPEED = 5

# كثافة الطباعة (0-9، 9 = أغمق)
PRINT_DENSITY = 7


# ============================================
# إعدادات السجلات (Logging)
# ============================================

# مستوى السجلات
# DEBUG = كل شيء
# INFO = معلومات عامة
# WARNING = تحذيرات فقط
# ERROR = أخطاء فقط
LOG_LEVEL = 'INFO'

# ملف السجل
LOG_FILE = 'print_agent.log'

# حجم السجل الأقصى (بالميجابايت)
MAX_LOG_SIZE = 10

# عدد ملفات السجل الاحتياطية
LOG_BACKUP_COUNT = 5


# ============================================
# إعدادات الأمان
# ============================================

# هل تريد تفعيل المصادقة؟ (للمستقبل)
REQUIRE_AUTH = False

# مفتاح API (للمستقبل)
API_KEY = None

# قائمة الـ IPs المسموح لها بالاتصال
ALLOWED_IPS = ['127.0.0.1', 'localhost']

# إذا كنت تستخدم شبكة محلية:
# ALLOWED_IPS = ['192.168.1.*', '10.0.0.*']


# ============================================
# إعدادات متقدمة
# ============================================

# مهلة الانتظار (ثواني)
TIMEOUT = 30

# الحد الأقصى لحجم الطباعة (بالميجابايت)
MAX_PRINT_SIZE = 5

# إعادة المحاولة عند فشل الطباعة
RETRY_ON_FAILURE = True
MAX_RETRIES = 3

# الوقت بين المحاولات (ثواني)
RETRY_DELAY = 2

# حفظ نسخة من كل طباعة (للتدقيق)
SAVE_PRINT_HISTORY = True
PRINT_HISTORY_DIR = 'print_history'

# مدة حفظ السجل (أيام)
HISTORY_RETENTION_DAYS = 30


# ============================================
# إعدادات الطابعات الحرارية المتقدمة
# ============================================

# أوامر ESC/POS المخصصة
CUSTOM_COMMANDS = {
    # أمر فتح درج النقود
    'open_drawer': [0x1B, 0x70, 0x00, 0x19, 0xFA],
    
    # أمر قص الورق
    'cut_paper': [0x1D, 0x56, 0x41, 0x00],
    
    # أمر صوت التنبيه
    'beep': [0x1B, 0x42, 0x05, 0x09],
}


# ============================================
# إعدادات التحويل HTML → Print
# ============================================

# أداة تحويل HTML لـ PDF
# wkhtmltopdf = مجاني وجيد
# chrome = يحتاج Chrome/Chromium
# weasyprint = مكتبة Python
HTML_CONVERTER = 'wkhtmltopdf'

# مسار wkhtmltopdf (اتركه فارغًا للبحث التلقائي)
WKHTMLTOPDF_PATH = None

# أو حدد المسار:
# Windows:
# WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
# Linux:
# WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'


# ============================================
# إعدادات الأداء
# ============================================

# عدد العمليات المتزامنة
MAX_CONCURRENT_JOBS = 5

# حجم المخزن المؤقت (KB)
BUFFER_SIZE = 4096

# استخدام الذاكرة المؤقتة للطابعات
CACHE_PRINTERS = True

# تحديث قائمة الطابعات كل (ثواني)
REFRESH_PRINTERS_INTERVAL = 60


# ============================================
# إعدادات إضافية حسب نوع النظام
# ============================================

import sys

if sys.platform == 'win32':
    # إعدادات Windows
    USE_WIN32_PRINT = True
    
elif sys.platform.startswith('linux'):
    # إعدادات Linux
    USE_CUPS = True
    CUPS_SERVER = 'localhost'
    
elif sys.platform == 'darwin':
    # إعدادات macOS
    USE_CUPS = True
    CUPS_SERVER = 'localhost'


# ============================================
# قراءة الإعدادات من ملف .env (اختياري)
# ============================================

try:
    from dotenv import load_dotenv  # type: ignore[import-unresolved]
    import os
    
    load_dotenv()
    
    # تجاوز الإعدادات من المتغيرات البيئية
    PORT = int(os.getenv('PRINT_PORT', PORT))
    HOST = os.getenv('PRINT_HOST', HOST)
    DEFAULT_PRINTER = os.getenv('DEFAULT_PRINTER', DEFAULT_PRINTER)
    
except ImportError:
    # python-dotenv غير مثبت
    pass


# ============================================
# التحقق من صحة الإعدادات
# ============================================

def validate_config():
    """التحقق من صحة الإعدادات"""
    errors = []
    
    if not (1024 <= PORT <= 65535):
        errors.append(f"المنفذ {PORT} غير صالح (يجب أن يكون بين 1024-65535)")
    
    if MAX_PRINT_SIZE > 100:
        errors.append("حجم الطباعة الأقصى كبير جدًا (أكثر من 100 MB)")
    
    if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        errors.append(f"مستوى السجل {LOG_LEVEL} غير صالح")
    
    if errors:
        print("⚠️ تحذيرات في الإعدادات:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


if __name__ == '__main__':
    # اختبار الإعدادات
    print("🔧 إعدادات نظام الطباعة:")
    print(f"  المنفذ: {PORT}")
    print(f"  العنوان: {HOST}")
    print(f"  الطابعة الافتراضية: {DEFAULT_PRINTER or 'طابعة النظام'}")
    print(f"  قص تلقائي: {'نعم' if AUTO_CUT else 'لا'}")
    print(f"  فتح درج النقود: {'نعم' if OPEN_CASH_DRAWER else 'لا'}")
    print(f"  مستوى السجلات: {LOG_LEVEL}")
    print()
    
    if validate_config():
        print("✓ الإعدادات صحيحة")
    else:
        print("✗ يوجد مشاكل في الإعدادات")
