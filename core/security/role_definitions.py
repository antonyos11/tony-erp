"""
تعريفات الأدوار الثابتة في النظام
Role Definitions Constants
"""

# ============================================================================
# Role Constants - استخدم هذه الثوابت في كل مكان بدلاً من النصوص المباشرة
# ============================================================================

ROLE_OWNER = 'super_admin'
ROLE_GM = 'general_manager'
ROLE_SYS_ADMIN = 'system_admin'

# فروع
ROLE_BRANCHES_MANAGER = 'branches_manager'
ROLE_BRANCH_SUPERVISOR = 'branch_supervisor'
ROLE_BRANCH_MANAGER = 'branch_manager'
ROLE_BRANCH_VICE_MANAGER = 'branch_vice_manager'

# مالية
ROLE_FIN_MANAGER = 'accounting_manager'
ROLE_SENIOR_ACCOUNTANT = 'senior_accountant'
ROLE_ACCOUNTANT = 'accounting_staff'
ROLE_COST_ACCOUNTANT = 'cost_accountant'
ROLE_TREASURY_OFFICER = 'treasury_officer'
ROLE_BRANCH_ACCOUNTANT = 'branch_accountant'
ROLE_INTERNAL_AUDITOR = 'internal_auditor'

# موارد بشرية
ROLE_HR_MANAGER = 'hr_manager'
ROLE_HR_RECRUITER = 'hr_recruiter'
ROLE_HR_PAYROLL = 'hr_payroll'
ROLE_HR_ATTENDANCE = 'hr_attendance'
ROLE_HR_TRAINING = 'hr_training'
ROLE_HR_GOV_RELATIONS = 'hr_gov_relations'
ROLE_HR_STAFF = 'hr_staff'

# مشتريات
ROLE_PROCUREMENT_MANAGER = 'procurement_manager'
ROLE_PROCUREMENT_LEAD = 'procurement_lead'
ROLE_PROCUREMENT_OFFICER = 'procurement_officer'
ROLE_PO_OFFICER = 'po_officer'
ROLE_SUPPLIER_FOLLOWUP = 'supplier_followup'

# مخازن
ROLE_WAREHOUSE_MANAGER = 'warehouse_manager'
ROLE_STORE_SUPERVISOR = 'store_supervisor'
ROLE_STORE_KEEPER = 'inventory_staff'
ROLE_BRANCH_STORE_KEEPER = 'branch_store_keeper'
ROLE_INVENTORY_CONTROLLER = 'inventory_controller'
ROLE_WAREHOUSE_WORKER = 'warehouse_worker'

# تقنية معلومات
ROLE_IT_MANAGER = 'it_manager'
ROLE_IT_DEVELOPER = 'it_developer'
ROLE_IT_NETWORK = 'it_network'
ROLE_IT_SUPPORT = 'it_support'

# تسويق ومبيعات
ROLE_SALES_MARKETING_MANAGER = 'sales_marketing_manager'
ROLE_MARKETING_MANAGER = 'marketing_manager'
ROLE_CAMPAIGN_TEAM = 'campaign_team'
ROLE_GRAPHIC_DESIGNER = 'graphic_designer'
ROLE_CONTENT_CREATOR = 'content_creator'
ROLE_SOCIAL_MEDIA_SPECIALIST = 'social_media_specialist'
ROLE_SALES_MANAGER = 'sales_manager'
ROLE_SALES_SUPERVISOR = 'sales_supervisor'
ROLE_SALES_REP_INTERNAL = 'sales_rep_internal'
ROLE_SALES_REP_EXTERNAL = 'sales_rep_external'
ROLE_CASHIER = 'cashier'
ROLE_PRICING_OFFICER = 'pricing_officer'

# جودة وخدمة عملاء
ROLE_QUALITY_MANAGER = 'quality_manager'
ROLE_QUALITY_INSPECTOR = 'quality_inspector'
ROLE_CUSTOMER_CARE_LEAD = 'customer_care_lead'
ROLE_CUSTOMER_SERVICE_LEAD = 'customer_service_lead'
ROLE_CS_AGENT = 'cs_agent'
ROLE_CS_ORDER_FOLLOWUP = 'cs_order_followup'
ROLE_CS_COMPLAINTS = 'cs_complaints'

# تشغيل/مصنع/إنتاج
ROLE_OPERATIONS_MANAGER = 'operations_manager'
ROLE_FACTORY_MANAGER = 'factory_manager'
ROLE_FACTORY_VICE_MANAGER = 'factory_vice_manager'
ROLE_PROD_MANAGER = 'production_manager'
ROLE_PRODUCTION_SUPERVISOR = 'production_supervisor'
ROLE_FOAM_LINE_SUPERVISOR = 'foam_line_supervisor'
ROLE_SPRING_LINE_SUPERVISOR = 'spring_line_supervisor'
ROLE_UPHOLSTERY_SUPERVISOR = 'upholstery_supervisor'
ROLE_SHIFT_LEAD = 'shift_lead'
ROLE_PROD_TECHNICIAN = 'production_technician'
ROLE_PROD_STAFF = 'production_staff'
ROLE_PACKAGING_WORKER = 'packaging_worker'
ROLE_DISPATCH_CONTROLLER = 'dispatch_controller'
ROLE_MAINTENANCE_MANAGER = 'maintenance_manager'
ROLE_MECH_TECH = 'mech_tech'
ROLE_ELEC_TECH = 'elec_tech'
ROLE_LINE_MAINT_TECH = 'line_maint_tech'
ROLE_SPAREPARTS_CONTROLLER = 'spareparts_controller'
ROLE_QA_LAB_CHEMIST = 'qa_lab_chemist'
ROLE_QA_RAW_TESTER = 'qa_raw_tester'
ROLE_QA_FINAL_TESTER = 'qa_final_tester'
ROLE_QA_SPEC_MATCHER = 'qa_spec_matcher'
ROLE_HSE_OFFICER = 'hse_officer'
ROLE_HSE_SUPERVISOR = 'hse_supervisor'
ROLE_HSE_EMERGENCY = 'hse_emergency'
ROLE_RAW_STORE_KEEPER = 'raw_store_keeper'
ROLE_SEMI_STORE_KEEPER = 'semi_store_keeper'
ROLE_FG_STORE_KEEPER = 'fg_store_keeper'
ROLE_LABOR_CONTROLLER = 'labor_controller'
ROLE_PORTER = 'porter'
ROLE_TEA_BOY = 'tea_boy'
ROLE_CLEANER = 'cleaner'
ROLE_SECURITY_GUARD = 'security_guard'

ROLE_VIEWER = 'viewer'

# ============================================================================
# Role Display Names & Descriptions
# ============================================================================

ROLE_DISPLAY_NAMES = {
    ROLE_OWNER: 'صاحب الشركة / رئيس مجلس الإدارة',
    ROLE_GM: 'المدير العام',
    ROLE_SYS_ADMIN: 'مشرف نظام',

    ROLE_BRANCHES_MANAGER: 'مدير إدارة الفروع',
    ROLE_BRANCH_SUPERVISOR: 'مشرف فروع',
    ROLE_BRANCH_MANAGER: 'مدير فرع',
    ROLE_BRANCH_VICE_MANAGER: 'نائب مدير فرع',

    ROLE_FIN_MANAGER: 'المدير المالي',
    ROLE_SENIOR_ACCOUNTANT: 'كبير محاسبين',
    ROLE_ACCOUNTANT: 'محاسب عام',
    ROLE_COST_ACCOUNTANT: 'محاسب تكاليف',
    ROLE_TREASURY_OFFICER: 'محاسب خزنة',
    ROLE_BRANCH_ACCOUNTANT: 'محاسب فروع',
    ROLE_INTERNAL_AUDITOR: 'مراجع داخلي',

    ROLE_HR_MANAGER: 'مدير الموارد البشرية',
    ROLE_HR_RECRUITER: 'مسؤول توظيف',
    ROLE_HR_PAYROLL: 'مسؤول رواتب',
    ROLE_HR_ATTENDANCE: 'مسؤول حضور وانصراف',
    ROLE_HR_TRAINING: 'مسؤول تدريب وتطوير',
    ROLE_HR_GOV_RELATIONS: 'علاقات حكومية',
    ROLE_HR_STAFF: 'موظف موارد بشرية',

    ROLE_PROCUREMENT_MANAGER: 'مدير مشتريات',
    ROLE_PROCUREMENT_LEAD: 'مشتري رئيسي',
    ROLE_PROCUREMENT_OFFICER: 'مشتري فرعي',
    ROLE_PO_OFFICER: 'مسؤول أوامر شراء',
    ROLE_SUPPLIER_FOLLOWUP: 'متابعة الموردين',

    ROLE_WAREHOUSE_MANAGER: 'مدير المخازن',
    ROLE_STORE_SUPERVISOR: 'مشرف مخازن',
    ROLE_STORE_KEEPER: 'أمين مخزن رئيسي',
    ROLE_BRANCH_STORE_KEEPER: 'أمين مخزن فرع',
    ROLE_INVENTORY_CONTROLLER: 'مسؤول جرد',
    ROLE_WAREHOUSE_WORKER: 'عامل مخزن / شيال',

    ROLE_IT_MANAGER: 'مدير تقنية المعلومات',
    ROLE_IT_DEVELOPER: 'مبرمج',
    ROLE_IT_NETWORK: 'مسؤول شبكات',
    ROLE_IT_SUPPORT: 'فني صيانة أجهزة',

    ROLE_SALES_MARKETING_MANAGER: 'مدير التسويق والمبيعات',
    ROLE_MARKETING_MANAGER: 'مدير التسويق',
    ROLE_CAMPAIGN_TEAM: 'فريق حملات إعلانية',
    ROLE_GRAPHIC_DESIGNER: 'مصمم جرافيك',
    ROLE_CONTENT_CREATOR: 'صانع محتوى',
    ROLE_SOCIAL_MEDIA_SPECIALIST: 'مسؤول سوشيال ميديا',
    ROLE_SALES_MANAGER: 'مدير المبيعات',
    ROLE_SALES_SUPERVISOR: 'مشرف مبيعات',
    ROLE_SALES_REP_INTERNAL: 'مندوب مبيعات داخلي',
    ROLE_SALES_REP_EXTERNAL: 'مندوب مبيعات خارجي',
    ROLE_CASHIER: 'كاشير / نقطة بيع',
    ROLE_PRICING_OFFICER: 'مسؤول تسعير',

    ROLE_QUALITY_MANAGER: 'مدير الجودة',
    ROLE_QUALITY_INSPECTOR: 'مفتش جودة',
    ROLE_CUSTOMER_CARE_LEAD: 'مسؤول شكاوى ورضا العملاء',
    ROLE_CUSTOMER_SERVICE_LEAD: 'مسؤول خدمة العملاء',
    ROLE_CS_AGENT: 'موظف خدمة عملاء',
    ROLE_CS_ORDER_FOLLOWUP: 'متابعة الأوردرات',
    ROLE_CS_COMPLAINTS: 'حل الشكاوى',

    ROLE_OPERATIONS_MANAGER: 'مدير التشغيل/الإنتاج',
    ROLE_FACTORY_MANAGER: 'مدير المصنع',
    ROLE_FACTORY_VICE_MANAGER: 'نائب مدير المصنع',
    ROLE_PROD_MANAGER: 'مدير الإنتاج',
    ROLE_PRODUCTION_SUPERVISOR: 'مشرف إنتاج',
    ROLE_FOAM_LINE_SUPERVISOR: 'مشرف خط الإسفنج',
    ROLE_SPRING_LINE_SUPERVISOR: 'مشرف خط السوست',
    ROLE_UPHOLSTERY_SUPERVISOR: 'مشرف خط التنجيد',
    ROLE_SHIFT_LEAD: 'قائد وردية',
    ROLE_PROD_TECHNICIAN: 'فني إنتاج',
    ROLE_PROD_STAFF: 'عامل إنتاج',
    ROLE_PACKAGING_WORKER: 'عامل تغليف',
    ROLE_DISPATCH_CONTROLLER: 'مسؤول تسليمات المصنع',
    ROLE_MAINTENANCE_MANAGER: 'مدير الصيانة',
    ROLE_MECH_TECH: 'فني ميكانيكا',
    ROLE_ELEC_TECH: 'فني كهرباء',
    ROLE_LINE_MAINT_TECH: 'فني صيانة خطوط',
    ROLE_SPAREPARTS_CONTROLLER: 'مسؤول قطع غيار',
    ROLE_QA_LAB_CHEMIST: 'كيميائي المصنع',
    ROLE_QA_RAW_TESTER: 'اختبار المواد الخام',
    ROLE_QA_FINAL_TESTER: 'فحص المنتج النهائي',
    ROLE_QA_SPEC_MATCHER: 'مطابقة المواصفات',
    ROLE_HSE_OFFICER: 'مسؤول سلامة',
    ROLE_HSE_SUPERVISOR: 'مشرف وقاية',
    ROLE_HSE_EMERGENCY: 'مسؤول طوارئ',
    ROLE_RAW_STORE_KEEPER: 'أمين مخزن مواد خام',
    ROLE_SEMI_STORE_KEEPER: 'أمين مخزن مواد نصف مصنعة',
    ROLE_FG_STORE_KEEPER: 'أمين مخزن منتج نهائي',
    ROLE_LABOR_CONTROLLER: 'مراقب عمال',
    ROLE_PORTER: 'شيال',
    ROLE_TEA_BOY: 'عامل بوفيه',
    ROLE_CLEANER: 'عامل نظافة',
    ROLE_SECURITY_GUARD: 'أمن المصنع',

    ROLE_VIEWER: 'مستخدم عرض فقط',
}

ROLE_DESCRIPTIONS = {
    ROLE_OWNER: 'صلاحيات كاملة على كل شيء في النظام',
    ROLE_GM: 'إدارة عامة لكل الوحدات',
    ROLE_SYS_ADMIN: 'دعم وصيانة النظام',

    ROLE_BRANCHES_MANAGER: 'إدارة شبكة الفروع',
    ROLE_BRANCH_SUPERVISOR: 'متابعة الفروع ميدانياً',
    ROLE_BRANCH_MANAGER: 'إدارة فرع محدد',
    ROLE_BRANCH_VICE_MANAGER: 'نائب لمدير الفرع',

    ROLE_FIN_MANAGER: 'إدارة مالية كاملة وموافقات عليا',
    ROLE_SENIOR_ACCOUNTANT: 'إشراف محاسبي وتنفيذ متقدم',
    ROLE_ACCOUNTANT: 'محاسب عمليات يومية',
    ROLE_COST_ACCOUNTANT: 'تحليل التكاليف',
    ROLE_TREASURY_OFFICER: 'خزنة وبنوك',
    ROLE_BRANCH_ACCOUNTANT: 'محاسبة الفروع',
    ROLE_INTERNAL_AUDITOR: 'مراجعة داخلية ورقابة',

    ROLE_HR_MANAGER: 'إدارة الموارد البشرية',
    ROLE_HR_RECRUITER: 'توظيف',
    ROLE_HR_PAYROLL: 'رواتب',
    ROLE_HR_ATTENDANCE: 'حضور وانصراف',
    ROLE_HR_TRAINING: 'تدريب وتطوير',
    ROLE_HR_GOV_RELATIONS: 'علاقات حكومية',
    ROLE_HR_STAFF: 'تنفيذ HR عام',

    ROLE_PROCUREMENT_MANAGER: 'إدارة المشتريات',
    ROLE_PROCUREMENT_LEAD: 'قيادة التفاوض والشراء',
    ROLE_PROCUREMENT_OFFICER: 'تنفيذ أوامر شراء',
    ROLE_PO_OFFICER: 'إنشاء ومتابعة أوامر الشراء',
    ROLE_SUPPLIER_FOLLOWUP: 'متابعة الموردين',

    ROLE_WAREHOUSE_MANAGER: 'إدارة المخازن الرئيسية',
    ROLE_STORE_SUPERVISOR: 'إشراف مخازن',
    ROLE_STORE_KEEPER: 'استلام وصرف رئيسي',
    ROLE_BRANCH_STORE_KEEPER: 'استلام وصرف بالفروع',
    ROLE_INVENTORY_CONTROLLER: 'جرد ورقابة مخزون',
    ROLE_WAREHOUSE_WORKER: 'تشغيل المخزن',

    ROLE_IT_MANAGER: 'إدارة تقنية المعلومات',
    ROLE_IT_DEVELOPER: 'تطوير وبرمجة',
    ROLE_IT_NETWORK: 'شبكات وبنية تحتية',
    ROLE_IT_SUPPORT: 'صيانة ودعم أجهزة',

    ROLE_SALES_MARKETING_MANAGER: 'إدارة التسويق والمبيعات',
    ROLE_MARKETING_MANAGER: 'إدارة التسويق',
    ROLE_CAMPAIGN_TEAM: 'تنفيذ الحملات',
    ROLE_GRAPHIC_DESIGNER: 'تصميم جرافيك',
    ROLE_CONTENT_CREATOR: 'إنتاج المحتوى',
    ROLE_SOCIAL_MEDIA_SPECIALIST: 'إدارة السوشيال ميديا',
    ROLE_SALES_MANAGER: 'قيادة المبيعات',
    ROLE_SALES_SUPERVISOR: 'إشراف مبيعات',
    ROLE_SALES_REP_INTERNAL: 'مبيعات داخلية',
    ROLE_SALES_REP_EXTERNAL: 'مبيعات خارجية',
    ROLE_CASHIER: 'تحصيل ونقطة بيع',
    ROLE_PRICING_OFFICER: 'تسعير وعروض',

    ROLE_QUALITY_MANAGER: 'إدارة الجودة',
    ROLE_QUALITY_INSPECTOR: 'تفتيش جودة',
    ROLE_CUSTOMER_CARE_LEAD: 'شكاوى ورضا العملاء',
    ROLE_CUSTOMER_SERVICE_LEAD: 'إشراف خدمة العملاء',
    ROLE_CS_AGENT: 'خدمة عملاء',
    ROLE_CS_ORDER_FOLLOWUP: 'متابعة أوردرات',
    ROLE_CS_COMPLAINTS: 'حل الشكاوى',

    ROLE_OPERATIONS_MANAGER: 'إدارة التشغيل',
    ROLE_FACTORY_MANAGER: 'إدارة المصنع',
    ROLE_FACTORY_VICE_MANAGER: 'نائب مدير المصنع',
    ROLE_PROD_MANAGER: 'إدارة الإنتاج',
    ROLE_PRODUCTION_SUPERVISOR: 'إشراف الإنتاج',
    ROLE_FOAM_LINE_SUPERVISOR: 'مشرف خط الإسفنج',
    ROLE_SPRING_LINE_SUPERVISOR: 'مشرف خط السوست',
    ROLE_UPHOLSTERY_SUPERVISOR: 'مشرف خط التنجيد',
    ROLE_SHIFT_LEAD: 'قائد وردية',
    ROLE_PROD_TECHNICIAN: 'فني إنتاج',
    ROLE_PROD_STAFF: 'عامل إنتاج',
    ROLE_PACKAGING_WORKER: 'تغليف وتعبئة',
    ROLE_DISPATCH_CONTROLLER: 'مسؤول التسليمات',
    ROLE_MAINTENANCE_MANAGER: 'إدارة الصيانة',
    ROLE_MECH_TECH: 'فني ميكانيكا',
    ROLE_ELEC_TECH: 'فني كهرباء',
    ROLE_LINE_MAINT_TECH: 'فني صيانة خطوط',
    ROLE_SPAREPARTS_CONTROLLER: 'مسؤول قطع الغيار',
    ROLE_QA_LAB_CHEMIST: 'كيميائي المعمل',
    ROLE_QA_RAW_TESTER: 'اختبار المواد الخام',
    ROLE_QA_FINAL_TESTER: 'اختبار المنتج النهائي',
    ROLE_QA_SPEC_MATCHER: 'مطابقة المواصفات',
    ROLE_HSE_OFFICER: 'سلامة وصحة مهنية',
    ROLE_HSE_SUPERVISOR: 'إشراف السلامة',
    ROLE_HSE_EMERGENCY: 'طوارئ',
    ROLE_RAW_STORE_KEEPER: 'أمين مخزن مواد خام',
    ROLE_SEMI_STORE_KEEPER: 'أمين مخزن مواد نصف مصنعة',
    ROLE_FG_STORE_KEEPER: 'أمين مخزن منتج نهائي',
    ROLE_LABOR_CONTROLLER: 'مراقب عمال',
    ROLE_PORTER: 'شيال',
    ROLE_TEA_BOY: 'عامل بوفيه',
    ROLE_CLEANER: 'عامل نظافة',
    ROLE_SECURITY_GUARD: 'أمن المصنع',

    ROLE_VIEWER: 'عرض فقط',
}

# ============================================================================
# Default Approval Limits
# ============================================================================

DEFAULT_APPROVAL_LIMITS = {
    ROLE_OWNER: None,
    ROLE_GM: None,
    ROLE_SYS_ADMIN: 0,

    ROLE_BRANCHES_MANAGER: 30000,
    ROLE_BRANCH_MANAGER: 15000,
    ROLE_BRANCH_VICE_MANAGER: 10000,
    ROLE_BRANCH_SUPERVISOR: 5000,

    ROLE_FIN_MANAGER: 100000,
    ROLE_SENIOR_ACCOUNTANT: 50000,
    ROLE_ACCOUNTANT: 0,
    ROLE_COST_ACCOUNTANT: 0,
    ROLE_TREASURY_OFFICER: 0,
    ROLE_BRANCH_ACCOUNTANT: 0,
    ROLE_INTERNAL_AUDITOR: 0,

    ROLE_HR_MANAGER: 15000,
    ROLE_HR_RECRUITER: 0,
    ROLE_HR_PAYROLL: 0,
    ROLE_HR_ATTENDANCE: 0,
    ROLE_HR_TRAINING: 0,
    ROLE_HR_GOV_RELATIONS: 0,
    ROLE_HR_STAFF: 0,

    ROLE_PROCUREMENT_MANAGER: 50000,
    ROLE_PROCUREMENT_LEAD: 20000,
    ROLE_PROCUREMENT_OFFICER: 0,
    ROLE_PO_OFFICER: 0,
    ROLE_SUPPLIER_FOLLOWUP: 0,

    ROLE_WAREHOUSE_MANAGER: 30000,
    ROLE_STORE_SUPERVISOR: 10000,
    ROLE_STORE_KEEPER: 0,
    ROLE_BRANCH_STORE_KEEPER: 0,
    ROLE_INVENTORY_CONTROLLER: 0,
    ROLE_WAREHOUSE_WORKER: 0,

    ROLE_IT_MANAGER: 0,
    ROLE_IT_DEVELOPER: 0,
    ROLE_IT_NETWORK: 0,
    ROLE_IT_SUPPORT: 0,

    ROLE_SALES_MARKETING_MANAGER: 50000,
    ROLE_MARKETING_MANAGER: 20000,
    ROLE_CAMPAIGN_TEAM: 0,
    ROLE_GRAPHIC_DESIGNER: 0,
    ROLE_CONTENT_CREATOR: 0,
    ROLE_SOCIAL_MEDIA_SPECIALIST: 0,
    ROLE_SALES_MANAGER: 50000,
    ROLE_SALES_SUPERVISOR: 10000,
    ROLE_SALES_REP_INTERNAL: 0,
    ROLE_SALES_REP_EXTERNAL: 0,
    ROLE_CASHIER: 0,
    ROLE_PRICING_OFFICER: 25000,

    ROLE_QUALITY_MANAGER: 20000,
    ROLE_QUALITY_INSPECTOR: 0,
    ROLE_CUSTOMER_CARE_LEAD: 0,
    ROLE_CUSTOMER_SERVICE_LEAD: 0,
    ROLE_CS_AGENT: 0,
    ROLE_CS_ORDER_FOLLOWUP: 0,
    ROLE_CS_COMPLAINTS: 0,

    ROLE_OPERATIONS_MANAGER: 50000,
    ROLE_FACTORY_MANAGER: 50000,
    ROLE_FACTORY_VICE_MANAGER: 30000,
    ROLE_PROD_MANAGER: 40000,
    ROLE_PRODUCTION_SUPERVISOR: 20000,
    ROLE_FOAM_LINE_SUPERVISOR: 15000,
    ROLE_SPRING_LINE_SUPERVISOR: 15000,
    ROLE_UPHOLSTERY_SUPERVISOR: 15000,
    ROLE_SHIFT_LEAD: 5000,
    ROLE_PROD_TECHNICIAN: 0,
    ROLE_PROD_STAFF: 0,
    ROLE_PACKAGING_WORKER: 0,
    ROLE_DISPATCH_CONTROLLER: 0,
    ROLE_MAINTENANCE_MANAGER: 20000,
    ROLE_MECH_TECH: 0,
    ROLE_ELEC_TECH: 0,
    ROLE_LINE_MAINT_TECH: 0,
    ROLE_SPAREPARTS_CONTROLLER: 0,
    ROLE_QA_LAB_CHEMIST: 0,
    ROLE_QA_RAW_TESTER: 0,
    ROLE_QA_FINAL_TESTER: 0,
    ROLE_QA_SPEC_MATCHER: 0,
    ROLE_HSE_OFFICER: 0,
    ROLE_HSE_SUPERVISOR: 0,
    ROLE_HSE_EMERGENCY: 0,
    ROLE_RAW_STORE_KEEPER: 0,
    ROLE_SEMI_STORE_KEEPER: 0,
    ROLE_FG_STORE_KEEPER: 0,
    ROLE_LABOR_CONTROLLER: 0,
    ROLE_PORTER: 0,
    ROLE_TEA_BOY: 0,
    ROLE_CLEANER: 0,
    ROLE_SECURITY_GUARD: 0,

    ROLE_VIEWER: 0,
}

# ============================================================================
# Default Discount Percentages
# ============================================================================

DEFAULT_DISCOUNT_LIMITS = {
    ROLE_OWNER: None,
    ROLE_GM: 30,
    ROLE_SYS_ADMIN: 0,

    ROLE_BRANCHES_MANAGER: 10,
    ROLE_BRANCH_MANAGER: 5,
    ROLE_BRANCH_VICE_MANAGER: 5,
    ROLE_BRANCH_SUPERVISOR: 3,

    ROLE_FIN_MANAGER: 30,
    ROLE_SENIOR_ACCOUNTANT: 5,
    ROLE_ACCOUNTANT: 0,
    ROLE_COST_ACCOUNTANT: 0,
    ROLE_TREASURY_OFFICER: 0,
    ROLE_BRANCH_ACCOUNTANT: 0,
    ROLE_INTERNAL_AUDITOR: 0,

    ROLE_HR_MANAGER: 0,
    ROLE_HR_RECRUITER: 0,
    ROLE_HR_PAYROLL: 0,
    ROLE_HR_ATTENDANCE: 0,
    ROLE_HR_TRAINING: 0,
    ROLE_HR_GOV_RELATIONS: 0,
    ROLE_HR_STAFF: 0,

    ROLE_PROCUREMENT_MANAGER: 10,
    ROLE_PROCUREMENT_LEAD: 5,
    ROLE_PROCUREMENT_OFFICER: 0,
    ROLE_PO_OFFICER: 0,
    ROLE_SUPPLIER_FOLLOWUP: 0,

    ROLE_WAREHOUSE_MANAGER: 5,
    ROLE_STORE_SUPERVISOR: 3,
    ROLE_STORE_KEEPER: 0,
    ROLE_BRANCH_STORE_KEEPER: 0,
    ROLE_INVENTORY_CONTROLLER: 0,
    ROLE_WAREHOUSE_WORKER: 0,

    ROLE_IT_MANAGER: 0,
    ROLE_IT_DEVELOPER: 0,
    ROLE_IT_NETWORK: 0,
    ROLE_IT_SUPPORT: 0,

    ROLE_SALES_MARKETING_MANAGER: 25,
    ROLE_MARKETING_MANAGER: 10,
    ROLE_CAMPAIGN_TEAM: 0,
    ROLE_GRAPHIC_DESIGNER: 0,
    ROLE_CONTENT_CREATOR: 0,
    ROLE_SOCIAL_MEDIA_SPECIALIST: 0,
    ROLE_SALES_MANAGER: 20,
    ROLE_SALES_SUPERVISOR: 10,
    ROLE_SALES_REP_INTERNAL: 5,
    ROLE_SALES_REP_EXTERNAL: 5,
    ROLE_CASHIER: 0,
    ROLE_PRICING_OFFICER: 25,

    ROLE_QUALITY_MANAGER: 0,
    ROLE_QUALITY_INSPECTOR: 0,
    ROLE_CUSTOMER_CARE_LEAD: 0,
    ROLE_CUSTOMER_SERVICE_LEAD: 0,
    ROLE_CS_AGENT: 0,
    ROLE_CS_ORDER_FOLLOWUP: 0,
    ROLE_CS_COMPLAINTS: 0,

    ROLE_OPERATIONS_MANAGER: 0,
    ROLE_FACTORY_MANAGER: 0,
    ROLE_FACTORY_VICE_MANAGER: 0,
    ROLE_PROD_MANAGER: 0,
    ROLE_PRODUCTION_SUPERVISOR: 0,
    ROLE_FOAM_LINE_SUPERVISOR: 0,
    ROLE_SPRING_LINE_SUPERVISOR: 0,
    ROLE_UPHOLSTERY_SUPERVISOR: 0,
    ROLE_SHIFT_LEAD: 0,
    ROLE_PROD_TECHNICIAN: 0,
    ROLE_PROD_STAFF: 0,
    ROLE_PACKAGING_WORKER: 0,
    ROLE_DISPATCH_CONTROLLER: 0,
    ROLE_MAINTENANCE_MANAGER: 0,
    ROLE_MECH_TECH: 0,
    ROLE_ELEC_TECH: 0,
    ROLE_LINE_MAINT_TECH: 0,
    ROLE_SPAREPARTS_CONTROLLER: 0,
    ROLE_QA_LAB_CHEMIST: 0,
    ROLE_QA_RAW_TESTER: 0,
    ROLE_QA_FINAL_TESTER: 0,
    ROLE_QA_SPEC_MATCHER: 0,
    ROLE_HSE_OFFICER: 0,
    ROLE_HSE_SUPERVISOR: 0,
    ROLE_HSE_EMERGENCY: 0,
    ROLE_RAW_STORE_KEEPER: 0,
    ROLE_SEMI_STORE_KEEPER: 0,
    ROLE_FG_STORE_KEEPER: 0,
    ROLE_LABOR_CONTROLLER: 0,
    ROLE_PORTER: 0,
    ROLE_TEA_BOY: 0,
    ROLE_CLEANER: 0,
    ROLE_SECURITY_GUARD: 0,

    ROLE_VIEWER: 0,
}

# ============================================================================
# Approval Levels (for workflows)
# ============================================================================

APPROVAL_LEVELS = {
    ROLE_OWNER: 5,
    ROLE_GM: 5,
    ROLE_SYS_ADMIN: 2,

    ROLE_BRANCHES_MANAGER: 3,
    ROLE_BRANCH_MANAGER: 3,
    ROLE_BRANCH_VICE_MANAGER: 2,
    ROLE_BRANCH_SUPERVISOR: 2,

    ROLE_FIN_MANAGER: 4,
    ROLE_SENIOR_ACCOUNTANT: 3,
    ROLE_ACCOUNTANT: 2,
    ROLE_COST_ACCOUNTANT: 2,
    ROLE_TREASURY_OFFICER: 1,
    ROLE_BRANCH_ACCOUNTANT: 1,
    ROLE_INTERNAL_AUDITOR: 3,

    ROLE_HR_MANAGER: 3,
    ROLE_HR_RECRUITER: 1,
    ROLE_HR_PAYROLL: 2,
    ROLE_HR_ATTENDANCE: 1,
    ROLE_HR_TRAINING: 1,
    ROLE_HR_GOV_RELATIONS: 2,
    ROLE_HR_STAFF: 1,

    ROLE_PROCUREMENT_MANAGER: 3,
    ROLE_PROCUREMENT_LEAD: 2,
    ROLE_PROCUREMENT_OFFICER: 1,
    ROLE_PO_OFFICER: 1,
    ROLE_SUPPLIER_FOLLOWUP: 1,

    ROLE_WAREHOUSE_MANAGER: 3,
    ROLE_STORE_SUPERVISOR: 2,
    ROLE_STORE_KEEPER: 1,
    ROLE_BRANCH_STORE_KEEPER: 1,
    ROLE_INVENTORY_CONTROLLER: 1,
    ROLE_WAREHOUSE_WORKER: 1,

    ROLE_IT_MANAGER: 2,
    ROLE_IT_DEVELOPER: 1,
    ROLE_IT_NETWORK: 1,
    ROLE_IT_SUPPORT: 1,

    ROLE_SALES_MARKETING_MANAGER: 4,
    ROLE_MARKETING_MANAGER: 3,
    ROLE_CAMPAIGN_TEAM: 1,
    ROLE_GRAPHIC_DESIGNER: 1,
    ROLE_CONTENT_CREATOR: 1,
    ROLE_SOCIAL_MEDIA_SPECIALIST: 1,
    ROLE_SALES_MANAGER: 4,
    ROLE_SALES_SUPERVISOR: 3,
    ROLE_SALES_REP_INTERNAL: 1,
    ROLE_SALES_REP_EXTERNAL: 1,
    ROLE_CASHIER: 1,
    ROLE_PRICING_OFFICER: 3,

    ROLE_QUALITY_MANAGER: 3,
    ROLE_QUALITY_INSPECTOR: 2,
    ROLE_CUSTOMER_CARE_LEAD: 2,
    ROLE_CUSTOMER_SERVICE_LEAD: 2,
    ROLE_CS_AGENT: 1,
    ROLE_CS_ORDER_FOLLOWUP: 1,
    ROLE_CS_COMPLAINTS: 1,

    ROLE_OPERATIONS_MANAGER: 4,
    ROLE_FACTORY_MANAGER: 4,
    ROLE_FACTORY_VICE_MANAGER: 3,
    ROLE_PROD_MANAGER: 3,
    ROLE_PRODUCTION_SUPERVISOR: 2,
    ROLE_FOAM_LINE_SUPERVISOR: 2,
    ROLE_SPRING_LINE_SUPERVISOR: 2,
    ROLE_UPHOLSTERY_SUPERVISOR: 2,
    ROLE_SHIFT_LEAD: 1,
    ROLE_PROD_TECHNICIAN: 1,
    ROLE_PROD_STAFF: 1,
    ROLE_PACKAGING_WORKER: 1,
    ROLE_DISPATCH_CONTROLLER: 2,
    ROLE_MAINTENANCE_MANAGER: 3,
    ROLE_MECH_TECH: 1,
    ROLE_ELEC_TECH: 1,
    ROLE_LINE_MAINT_TECH: 1,
    ROLE_SPAREPARTS_CONTROLLER: 1,
    ROLE_QA_LAB_CHEMIST: 2,
    ROLE_QA_RAW_TESTER: 1,
    ROLE_QA_FINAL_TESTER: 1,
    ROLE_QA_SPEC_MATCHER: 1,
    ROLE_HSE_OFFICER: 2,
    ROLE_HSE_SUPERVISOR: 2,
    ROLE_HSE_EMERGENCY: 1,
    ROLE_RAW_STORE_KEEPER: 1,
    ROLE_SEMI_STORE_KEEPER: 1,
    ROLE_FG_STORE_KEEPER: 1,
    ROLE_LABOR_CONTROLLER: 1,
    ROLE_PORTER: 1,
    ROLE_TEA_BOY: 0,
    ROLE_CLEANER: 0,
    ROLE_SECURITY_GUARD: 1,

    ROLE_VIEWER: 0,
}

# ============================================================================
# Helper Functions
# ============================================================================

def get_role_display_name(role_code: str) -> str:
    """الحصول على الاسم العربي للدور"""
    return ROLE_DISPLAY_NAMES.get(role_code, role_code)


def get_role_description(role_code: str) -> str:
    """الحصول على وصف الدور"""
    return ROLE_DESCRIPTIONS.get(role_code, '')


def get_default_approval_limit(role_code: str) -> float | None:
    """الحصول على حد الموافقة الافتراضي للدور"""
    return DEFAULT_APPROVAL_LIMITS.get(role_code, 0)


def get_default_discount_limit(role_code: str) -> float | None:
    """الحصول على حد الخصم الافتراضي للدور"""
    return DEFAULT_DISCOUNT_LIMITS.get(role_code, 0)


def get_approval_level(role_code: str) -> int:
    """الحصول على مستوى الموافقة للدور"""
    return APPROVAL_LEVELS.get(role_code, 0)


def is_manager_role(role_code: str) -> bool:
    """فحص إذا كان الدور إداري (مدير)"""
    manager_roles = [
        ROLE_OWNER,
        ROLE_GM,
        ROLE_SYS_ADMIN,
        ROLE_BRANCHES_MANAGER,
        ROLE_BRANCH_MANAGER,
        ROLE_BRANCH_VICE_MANAGER,
        ROLE_BRANCH_SUPERVISOR,
        ROLE_FIN_MANAGER,
        ROLE_SENIOR_ACCOUNTANT,
        ROLE_HR_MANAGER,
        ROLE_PROCUREMENT_MANAGER,
        ROLE_PROCUREMENT_LEAD,
        ROLE_WAREHOUSE_MANAGER,
        ROLE_STORE_SUPERVISOR,
        ROLE_IT_MANAGER,
        ROLE_SALES_MARKETING_MANAGER,
        ROLE_MARKETING_MANAGER,
        ROLE_SALES_MANAGER,
        ROLE_SALES_SUPERVISOR,
        ROLE_QUALITY_MANAGER,
        ROLE_CUSTOMER_SERVICE_LEAD,
        ROLE_OPERATIONS_MANAGER,
        ROLE_FACTORY_MANAGER,
        ROLE_FACTORY_VICE_MANAGER,
        ROLE_PROD_MANAGER,
        ROLE_PRODUCTION_SUPERVISOR,
        ROLE_MAINTENANCE_MANAGER,
        ROLE_HSE_OFFICER,
    ]
    return role_code in manager_roles


def can_approve_by_default(role_code: str) -> bool:
    """فحص إذا كان الدور يستطيع الموافقة افتراضياً"""
    limit = get_default_approval_limit(role_code)
    return limit is None or limit > 0



