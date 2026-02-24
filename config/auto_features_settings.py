"""
إعدادات الميزات التلقائية
Auto Features Settings

أضف هذا الملف إلى settings.py الرئيسي
"""

# ===== نظام التسعير المرن =====
# Flexible Pricing System
SHOWROOM_PRICING = {
    'ENABLED': True,
    'AUTO_APPLY_IN_POS': True,  # تطبيق تلقائي في POS
    'ALLOW_MANUAL_OVERRIDE': True,  # السماح بالتعديل اليدوي
}

# ===== نظام الإنتاج التلقائي =====
# Auto Production Orders System
AUTO_PRODUCTION_SETTINGS = {
    'ENABLED': True,
    'MIN_SHORTAGE_TO_TRIGGER': 1,  # الحد الأدنى للنقص لإنشاء أمر
    'SAFETY_STOCK_MULTIPLIER': 1.2,  # نسبة مخزون الأمان (20% إضافي)
    'LEAD_TIME_BUFFER_DAYS': 2,  # أيام أمان للتسليم
    'AUTO_APPROVE_ORDERS': False,  # الموافقة التلقائية على الأوامر
    'PRIORITY_HIGH_THRESHOLD': 10,  # الكمية التي تحدد الأولوية العالية
    'CREATE_ON_POS_PAID': True,  # إنشاء عند الدفع فقط
    'NOTIFY_MANAGER_ON_CREATE': True,  # إشعار المدير
}

# ===== نظام الرسائل التلقائية =====
# Auto Messaging System
AUTO_MESSAGING_SETTINGS = {
    'ENABLED': True,
    
    # SMS Settings
    'SMS_ENABLED': False,  # تفعيل SMS
    'SMS_PROVIDER': 'twilio',  # المزود (twilio, nexmo, etc.)
    
    # WhatsApp Settings
    'WHATSAPP_ENABLED': False,  # تفعيل WhatsApp
    'WHATSAPP_PROVIDER': 'twilio',  # المزود
    
    # Twilio Credentials (مثال)
    'TWILIO_ACCOUNT_SID': 'your_account_sid_here',
    'TWILIO_AUTH_TOKEN': 'your_auth_token_here',
    'TWILIO_PHONE_NUMBER': '+1234567890',  # رقم SMS
    'TWILIO_WHATSAPP_NUMBER': '+1234567890',  # رقم WhatsApp
    
    # Message Templates Language
    'DEFAULT_LANGUAGE': 'ar',
    
    # Sending Rules
    'SEND_ORDER_CONFIRMATION': True,
    'SEND_PRODUCTION_READY': True,
    'SEND_PAYMENT_REMINDERS': True,
    'SEND_FEEDBACK_REQUEST': True,
    
    # Timing
    'PAYMENT_REMINDER_DAYS_BEFORE': 3,  # إرسال التذكير قبل 3 أيام
    'FEEDBACK_REQUEST_DAYS_AFTER': 7,  # طلب الرأي بعد 7 أيام
}

# ===== نظام حساب وعد التسليم =====
# Delivery Date Calculator Settings
DELIVERY_CALCULATOR_SETTINGS = {
    'ENABLED': True,
    'DEFAULT_LEAD_TIME_DAYS': 7,  # الافتراضي للمنتجات بدون BOM
    'WORKING_HOURS_PER_DAY': 8,  # ساعات العمل اليومية
    'CONSIDER_FACTORY_CAPACITY': True,  # الأخذ بعين الاعتبار طاقة المصنع
    'CAPACITY_THRESHOLD_WARNING': 0.85,  # تحذير عند 85% طاقة
    'CAPACITY_THRESHOLD_CRITICAL': 0.95,  # حرج عند 95% طاقة
}

# ===== نظام التحويلات الذكية =====
# Smart Transfer Suggestions
SMART_TRANSFER_SETTINGS = {
    'ENABLED': True,
    'AUTO_CREATE_THRESHOLD_SAVINGS': 500,  # إنشاء تلقائي عند توفير أكثر من 500 ج.م
    'MIN_STOCK_MULTIPLIER': 2,  # اعتبار المعرض لديه فائض عند ضعف الحد الأدنى
    'TRANSFER_COST_PER_KM': 5,  # تكلفة النقل للكيلومتر
    'RUN_DAILY_ANALYSIS': True,  # تشغيل التحليل اليومي
    'DAILY_ANALYSIS_TIME': '00:00',  # وقت التشغيل اليومي
}

# ===== محرك القرارات الذكي =====
# Smart Decision Engine
DECISION_ENGINE_SETTINGS = {
    'ENABLED': True,
    'DEAD_STOCK_DAYS': 90,  # المنتج راكد بعد 90 يوم بدون بيع
    'DEAD_STOCK_VALUE_THRESHOLD': 5000,  # تنبيه للمنتجات الراكدة بقيمة أكثر من 5000 ج.م
    'HIGH_DEMAND_THRESHOLD': 50,  # طلب عالي عند بيع أكثر من 50 قطعة شهرياً
    'LOW_MARGIN_THRESHOLD': 10,  # هامش ربح منخفض أقل من 10%
    'SHOWROOM_LOSS_ALERT': True,  # تنبيه للمعارض الخاسرة
    'RUN_DAILY_ANALYSIS': True,
    'DAILY_ANALYSIS_TIME': '01:00',
}

# ===== إعدادات عامة =====
# General Settings
AUTO_FEATURES_GENERAL = {
    'ENABLE_LOGGING': True,  # تفعيل السجلات التفصيلية
    'LOG_LEVEL': 'INFO',  # مستوى السجل (DEBUG, INFO, WARNING, ERROR)
    'ENABLE_NOTIFICATIONS': True,  # إشعارات داخلية للمديرين
    'NOTIFICATION_USERS': ['admin', 'manager'],  # المستخدمين المستلمين للإشعارات
}


# ===== Celery Tasks Configuration =====
# إذا كنت تستخدم Celery للمهام الدورية
CELERY_BEAT_SCHEDULE = {
    'deactivate-expired-pricing-rules': {
        'task': 'showrooms.tasks.deactivate_expired_pricing_rules',
        'schedule': 86400.0,  # يومياً (24 ساعة)
    },
    'daily-transfer-suggestions': {
        'task': 'inventory.tasks.daily_transfer_suggestions',
        'schedule': 86400.0,  # يومياً
    },
    'daily-decision-analysis': {
        'task': 'core.tasks.daily_decision_analysis',
        'schedule': 86400.0,  # يومياً
    },
    'send-payment-reminders': {
        'task': 'notifications.tasks.send_payment_reminders',
        'schedule': 86400.0,  # يومياً
    },
}
