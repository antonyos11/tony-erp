# هيكلة الأدوار المقترحة (RBAC) بحسب الهيكل الوظيفي

هذا المستند يربط الهيكل الوظيفي المطلوب بالأدوار والصلاحيات المقترحة في النظام.

## مستوى الإدارة العليا
- OWNER: صاحب الشركة / رئيس مجلس الإدارة
- GM: المدير العام (General Manager)
- SYS_ADMIN: مشرف النظام (دعم فني شامل)

## الإدارة المركزية (Head Office)
- BRANCHES_MANAGER: مدير إدارة الفروع
  - BRANCH_SUPERVISOR: مشرفي الفروع
  - BRANCH_MANAGER: مدراء الفروع
  - BRANCH_VICE_MANAGER (اختياري): نواب مدراء الفروع

- FIN_MANAGER: المدير المالي
  - FIN_REPORTING_MANAGER: مدير التقارير المالية (اختياري)
    - FIN_ANALYST: محلل تقارير مالية (اختياري)
  - SENIOR_ACCOUNTANT: كبير المحاسبين
    - ARAP_SUPERVISOR: مشرف حسابات عملاء/موردين
      - AR_ACCOUNTANT: محاسب حسابات عملاء
      - AP_ACCOUNTANT: محاسب حسابات موردين
    - ACCOUNTANT: محاسب عام
  - COST_ACCOUNTANT: محاسب تكاليف
  - TREASURY_OFFICER: أمين خزنة / كاشير مركزي
  - BRANCH_ACCOUNTANT: محاسب فروع / كاشير فروع

- HR_MANAGER: مدير الموارد البشرية
  - HR_RECRUITER: مسؤول توظيف
  - HR_PAYROLL: مسؤول رواتب Payroll
  - HR_ATTENDANCE: مسؤول حضور وانصراف
  - HR_GOV_RELATIONS: مسؤول علاقات حكومية (تأمينات/ضرائب)
  - HR_STAFF: موظف موارد بشرية عام

- PROCUREMENT_MANAGER: مدير المشتريات
  - PROCUREMENT_LEAD: مشتري رئيسي
  - PROCUREMENT_OFFICER: مشتري فرعي
  - PO_FOLLOWUP: مسؤول متابعة أوامر الشراء

- WAREHOUSE_MANAGER: مدير المخازن الرئيسي
  - STORE_SUPERVISOR: مشرف مخازن
    - STORE_KEEPER: أمين المخزن الرئيسي
    - BRANCH_STORE_KEEPER: أمين مخزن فرع
    - INVENTORY_CONTROLLER: مسؤول الجرد
    - WAREHOUSE_WORKER: عمال مخزن / شيالين

- IT_MANAGER: مدير IT
  - IT_DEVELOPER: مبرمج
  - IT_NETWORK: مسؤول شبكات
  - IT_SUPPORT: مسؤول صيانة أجهزة

## مستوى الإدارة العليا
- OWNER: صاحب الشركة / رئيس مجلس الإدارة
- GM: المدير العام (General Manager)
- SYS_ADMIN: مشرف النظام (دعم فني شامل)

## الإدارات المركزية (Head Office)
- BRANCHES_MANAGER: مدير إدارة الفروع
  - BRANCH_SUPERVISOR: مشرف فروع
  - BRANCH_MANAGER: مدير فرع
  - BRANCH_VICE_MANAGER: نائب مدير فرع (اختياري)

- FIN_MANAGER: المدير المالي
  - SENIOR_ACCOUNTANT: كبير محاسبين
    - ACCOUNTANT: محاسب عام
    - COST_ACCOUNTANT: محاسب تكاليف
    - TREASURY_OFFICER: محاسب خزنة / كاشير مركزي
    - BRANCH_ACCOUNTANT: محاسب فروع / كاشير فروع
  - INTERNAL_AUDITOR: مراجع داخلي

- HR_MANAGER: مدير HR
  - HR_RECRUITER: مسؤول توظيف
  - HR_PAYROLL: مسؤول رواتب
  - HR_ATTENDANCE: مسؤول حضور وانصراف
  - HR_TRAINING: مسؤول تدريب وتطوير
  - HR_GOV_RELATIONS: علاقات حكومية (تأمينات/ضرائب)
  - HR_STAFF: موظف HR عام

- PROCUREMENT_MANAGER: مدير مشتريات
  - PROCUREMENT_LEAD: مشتري رئيسي
  - PROCUREMENT_OFFICER: مشتري فرعي
  - PO_OFFICER: مسؤول أوامر شراء
  - SUPPLIER_FOLLOWUP: مسؤول متابعة الموردين

- WAREHOUSE_MANAGER: مدير المخازن الرئيسي
  - STORE_SUPERVISOR: مشرف مخازن
    - STORE_KEEPER: أمين المخزن الرئيسي
    - BRANCH_STORE_KEEPER: أمين مخزن فرع
    - INVENTORY_CONTROLLER: مسؤول الجرد
    - WAREHOUSE_WORKER: عمال مخزن / شيالين

- IT_MANAGER: مدير IT
  - IT_DEVELOPER: مبرمج
  - IT_NETWORK: مسؤول شبكات
  - IT_SUPPORT: فني صيانة أجهزة

- SALES_MARKETING_MANAGER: مدير التسويق والمبيعات
  - MARKETING_MANAGER: مدير التسويق
    - CAMPAIGN_TEAM: فريق الحملات الإعلانية
    - GRAPHIC_DESIGNER: مصمم جرافيك
    - CONTENT_CREATOR: صانع محتوى
    - SOCIAL_MEDIA_SPECIALIST: مسؤول سوشيال ميديا
  - SALES_MANAGER: مدير المبيعات
    - SALES_SUPERVISOR: مشرف مبيعات / فروع
      - SALES_REP_INTERNAL: مندوب مبيعات داخلي
      - SALES_REP_EXTERNAL: مندوب مبيعات خارجي
      - CASHIER: كاشير / نقطة بيع
    - PRICING_OFFICER: مسؤول تسعير/عروض

- QUALITY_MANAGER: مدير الجودة
  - QUALITY_INSPECTOR: مفتش جودة
  - CUSTOMER_CARE_LEAD: مسؤول خدمة العملاء وشكاوى الجودة

- CUSTOMER_SERVICE_LEAD: مسؤول خدمة العملاء (مركزي)
  - CS_AGENT: مسؤول خدمة عملاء
  - CS_ORDER_FOLLOWUP: مسؤول متابعة الأوردرات
  - CS_COMPLAINTS: مسؤول حل الشكاوى

- OPERATIONS_MANAGER: مدير التشغيل/الإنتاج (إجمالي)
  - FACTORY_MANAGER: مدير المصنع
  - FACTORY_VICE_MANAGER: نائب مدير المصنع (اختياري)

## هيكل المصنع (Factory)
- FACTORY_MANAGER / FACTORY_VICE_MANAGER
- PRODUCTION_MANAGER: مدير الإنتاج
  - PRODUCTION_SUPERVISOR: مشرفي الإنتاج
  - FOAM_LINE_SUPERVISOR: مشرف خط الإسفنج/الفوم
  - SPRING_LINE_SUPERVISOR: مشرف خط السوست
  - UPHOLSTERY_SUPERVISOR: مشرف خط التنجيد
  - SHIFT_LEAD: قائد وردية
    - PRODUCTION_TECHNICIAN: فنيين متخصصين
    - PRODUCTION_WORKER: عمال إنتاج
    - PACKAGING_WORKER: عمال تغليف وتعبئة
  - DISPATCH_CONTROLLER: مسؤول تسليمات المصنع

- MAINTENANCE_MANAGER: مدير الصيانة
  - MECH_TECH: فني ميكانيكا
  - ELEC_TECH: فني كهرباء
  - LINE_MAINT_TECH: فني صيانة خطوط
  - SPAREPARTS_CONTROLLER: مسؤول قطع غيار

- QA_LAB_CHEMIST: كيميائي المصنع
- QA_RAW_TESTER: اختبار المواد الخام
- QA_FINAL_TESTER: فحص المنتج النهائي
- QA_SPEC_MATCHER: مطابقة المواصفات

- HSE_OFFICER: مسؤول سلامة وصحة مهنية
  - HSE_SUPERVISOR: مشرف وقاية
  - HSE_EMERGENCY: مسؤول طوارئ

- مخازن المصنع: RAW_STORE_KEEPER (مواد خام) / SEMI_STORE_KEEPER (نصف مصنعة) / FG_STORE_KEEPER (منتج نهائي) / WAREHOUSE_WORKER

- الخدمات المساندة: LABOR_CONTROLLER (مراقب عمال) / PORTER (شيال) / TEA_BOY (بوفيه) / CLEANER (نظافة) / SECURITY_GUARD (أمن المصنع)

## هيكل الفروع (Branch-Level)
- BRANCH_MANAGER: مدير الفرع
- BRANCH_SUPERVISOR: مشرف الفرع
- CASHIER أو BRANCH_ACCOUNTANT: كاشير/محاسب الفرع
- SALES_REP_INTERNAL / SALES_REP_EXTERNAL: موظف مبيعات
- BRANCH_STORE_KEEPER: أمين مخزن الفرع
- WAREHOUSE_WORKER: عمال مخزن / شيالين
- CLEANER: عامل نظافة
- TEA_BOY: عامل بوفيه

## ربط الأدوار بالوحدات (اقتراح افتراضي)
- المحاسبة: FIN_MANAGER, SENIOR_ACCOUNTANT, ACCOUNTANT, COST_ACCOUNTANT, TREASURY_OFFICER, BRANCH_ACCOUNTANT, INTERNAL_AUDITOR
- المشتريات: PROCUREMENT_MANAGER, PROCUREMENT_LEAD, PROCUREMENT_OFFICER, PO_OFFICER, SUPPLIER_FOLLOWUP
- المخزون: WAREHOUSE_MANAGER, STORE_SUPERVISOR, STORE_KEEPER, BRANCH_STORE_KEEPER, INVENTORY_CONTROLLER, WAREHOUSE_WORKER
- المبيعات/التسويق: SALES_MARKETING_MANAGER, MARKETING_MANAGER, CAMPAIGN_TEAM, GRAPHIC_DESIGNER, CONTENT_CREATOR, SOCIAL_MEDIA_SPECIALIST, SALES_MANAGER, SALES_SUPERVISOR, SALES_REP_INTERNAL, SALES_REP_EXTERNAL, CASHIER, PRICING_OFFICER
- الإنتاج/المصنع: OPERATIONS_MANAGER, FACTORY_MANAGER, FACTORY_VICE_MANAGER, PRODUCTION_MANAGER, PRODUCTION_SUPERVISOR, FOAM_LINE_SUPERVISOR, SPRING_LINE_SUPERVISOR, UPHOLSTERY_SUPERVISOR, SHIFT_LEAD, PRODUCTION_TECHNICIAN, PRODUCTION_WORKER, PACKAGING_WORKER, DISPATCH_CONTROLLER, MAINTENANCE_MANAGER, MECH_TECH, ELEC_TECH, LINE_MAINT_TECH, SPAREPARTS_CONTROLLER
- الجودة/المعمل: QUALITY_MANAGER, QUALITY_INSPECTOR, CUSTOMER_CARE_LEAD, QA_LAB_CHEMIST, QA_RAW_TESTER, QA_FINAL_TESTER, QA_SPEC_MATCHER
- الموارد البشرية: HR_MANAGER, HR_RECRUITER, HR_PAYROLL, HR_ATTENDANCE, HR_TRAINING, HR_GOV_RELATIONS, HR_STAFF
- الفروع: BRANCHES_MANAGER, BRANCH_MANAGER, BRANCH_SUPERVISOR, BRANCH_VICE_MANAGER
- خدمة العملاء: CUSTOMER_SERVICE_LEAD, CS_AGENT, CS_ORDER_FOLLOWUP, CS_COMPLAINTS
- تقنية المعلومات: IT_MANAGER, IT_DEVELOPER, IT_NETWORK, IT_SUPPORT
- السلامة: HSE_OFFICER, HSE_SUPERVISOR, HSE_EMERGENCY
- الخدمات المساندة: TEA_BOY, CLEANER, PORTER, SECURITY_GUARD

## مستويات الصلاحيات (اقتراح مختصر)
- مستوى إدارة عليا: OWNER, GM → جميع الوحدات، كل العمليات.
- مستوى مدير إدارة: *_MANAGER → وحدته كاملة (view/add/change/approve/print/export) + تقارير.
- مستوى مشرف: *_SUPERVISOR → وحدته (view/add/change/approve محدود) ولا يغيّر إعدادات.
- مستوى تنفيذي: Officer/Accountant/Rep/Technician → (view/add/change) بدون approve/delete.
- مستوى عامل: Worker/Cleaner/Tea_Boy/Porter/Security → عمليات محدودة جداً أو لا صلاحيات تطبيقية.

## الخطوات التقنية المقترحة لتفعيلها
1) إضافة الأكواد أعلاه إلى `core/security/role_definitions.py` وإلى choices في `users.models.UserRole`.
2) إنشاء سجلات `UserRole` بالأسماء العربية المقترحة (migration أو data fixture).
3) ضبط صلاحيات الوحدات في `ModulePermission` و/أو `ResourcePermission` لكل دور (يمكن إنشاء قالب افتراضي).
4) تحديث خريطة الإدارة `MANAGER_SCOPES` (users/views.py) لربط كل مدير بالمشرفين والموظفين تحت إدارته، مع استخدام حقل `managed_by`.
5) (اختياري) ربط الفروع/المصانع: إضافة علاقة فرع/موقع لكل مستخدم فرعي لضبط الوصول بالفروع والمصنع.

## ملاحظات
- يمكن تقليل الأدوار إن أردت بساطة، أو الإبقاء على التفصيل الحالي بحسب الحاجة التشغيلية.
- الأدوار المقترحة لا تغيّر البيانات إلا بعد إنشاء سجلات `UserRole` وتوزيع الصلاحيات.
- يوصى بضبط حدود الموافقات والخصومات للأدوار المالية والمبيعات قبل الإطلاق.
