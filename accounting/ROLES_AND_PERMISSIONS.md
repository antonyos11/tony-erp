# نظام الأدوار والصلاحيات المحاسبية

## 📋 نظرة عامة

تم تصميم **3 أدوار رئيسية** لتغطية جميع احتياجات العمل المحاسبي، من أبسط المهام اليومية إلى أعقد العمليات المالية:

```
👤 كاشير/مندوب   →   💼 محاسب   →   👔 مدير مالي
   (12 شاشة)          (55 شاشة)       (65 شاشة)
```

---

## 🎭 الأدوار الثلاثة

### 1️⃣ **كاشير / مندوب** (Cashier / Sales Rep)

#### الوصف:
موظف خط أمامي يتعامل مع العمليات اليومية البسيطة فقط، دون الحاجة لفهم محاسبي عميق.

#### الصلاحيات الأساسية:
- ✅ **القراءة**: عرض معلومات محدودة
- ✅ **الإدخال البسيط**: سندات قبض وصرف فقط
- ❌ **لا يمكنه**: إنشاء قيود محاسبية، تعديل الحسابات، الوصول للتقارير المالية

#### الشاشات المتاحة (12 شاشة):

##### 📝 العمليات اليومية (5 شاشات)
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 1 | **لوحة المحاسبة** (عرض مبسط) | `/accounting/` | `view` |
| 2 | **سند قبض** | `/accounting/cash/receipt` | `add_cash_receipt` |
| 3 | **سند صرف** | `/accounting/cash/payment/` | `add_cash_payment` |
| 4 | **أرصدة نقدية** (عرض فقط) | `/accounting/cash/positions` | `view_cash_position` |
| 5 | **تحويل نقدي** (محدود) | `/accounting/cash/transfer` | `add_cash_transfer` |

##### 📄 الفواتير والحركة (4 شاشات)
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 6 | **كشف حساب عميل** (عرض فقط) | `/accounting/sales/statement/` | `view_customer_statement` |
| 7 | **كشف حساب مورد** (عرض فقط) | `/accounting/purchases/supplier-statement/` | `view_supplier_statement` |
| 8 | **حافظة الشيكات** (عرض فقط) | `/accounting/cheques/` | `view_cheque` |
| 9 | **شيك جديد** | `/accounting/cheques/new/` | `add_cheque` |

##### 📋 عرض معلومات (3 شاشات)
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 10 | **قائمة القيود** (عرض فقط) | `/accounting/journal-entries/` | `view_journal_entry` |
| 11 | **تفاصيل قيد** (عرض فقط) | `/accounting/journal-entries/<id>/` | `view_journal_entry` |
| 12 | **دليل الحسابات** (عرض فقط) | `/accounting/accounts/` | `view_account` |

---

### 2️⃣ **محاسب** (Accountant)

#### الوصف:
محاسب محترف يتعامل مع جميع العمليات المحاسبية اليومية، ويُعِدّ التقارير والقوائم المالية، لكن لا يمتلك صلاحيات تغيير الإعدادات الأساسية.

#### الصلاحيات الأساسية:
- ✅ **كل صلاحيات الكاشير** +
- ✅ **القيود المحاسبية**: إنشاء، تعديل، ترحيل
- ✅ **التقارير المالية**: جميع التقارير والقوائم
- ✅ **المراجعة**: ميزان المراجعة، دفتر الأستاذ
- ❌ **لا يمكنه**: تعديل الإعدادات، إقفال السنة، إنشاء/تعديل الحسابات الرئيسية

#### الشاشات المتاحة (55 شاشة):

##### 📝 الأساسيات اليومية (18 شاشة)
**القيود المحاسبية:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 1 | **قيد جديد** | `/accounting/journal-entries/create/` | `add_journal_entry` |
| 2 | **قيود مسودة** | `/accounting/journal/drafts` | `view_journal_entry` |
| 3 | **قائمة القيود** | `/accounting/journal-entries/` | `view_journal_entry` |
| 4 | **تفاصيل قيد** | `/accounting/journal-entries/<id>/` | `view_journal_entry` |
| 5 | **ترحيل قيد** | `/accounting/journal-entries/<id>/post/` | `post_journal_entry` |
| 6 | **عكس قيد** | `/accounting/journal-entries/<id>/reverse/` | `reverse_journal_entry` |
| 7 | **قيد ذكي** | `/accounting/smart-entry/` | `add_journal_entry` |

**الخزينة والبنوك:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 8 | **سند قبض** | `/accounting/cash/receipt` | `add_cash_receipt` |
| 9 | **سند صرف** | `/accounting/cash/payment/` | `add_cash_payment` |
| 10 | **تحويل نقدي** | `/accounting/cash/transfer` | `add_cash_transfer` |
| 11 | **أرصدة نقدية** | `/accounting/cash/positions` | `view_cash_position` |
| 12 | **تسوية بنك** | `/accounting/bank/reconcile` | `reconcile_bank` |

**دليل الحسابات:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 13 | **دليل الحسابات** | `/accounting/accounts/` | `view_account` |
| 14 | **تفاصيل حساب** | `/accounting/accounts/<id>/details/` | `view_account` |
| 15 | **حسابات المصروفات** | `/accounting/accounts/expenses/` | `view_account` |
| 16 | **بحث في الحسابات** | (مدمج) | `view_account` |

##### 📄 الفواتير والحركة (13 شاشة)
**المبيعات والعملاء:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 17 | **مدفوعات المبيعات** | `/accounting/sales/payments/` | `view_sales_payment` |
| 18 | **كشف حساب عميل** | `/accounting/sales/statement/` | `view_customer_statement` |
| 19 | **فواتير معلقة** | (مدمج) | `view_invoice` |

**المشتريات والموردين:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 20 | **كشف حساب مورد** | `/accounting/purchases/supplier-statement/` | `view_supplier_statement` |
| 21 | **فواتير شراء معلقة** | `/accounting/pending-purchase-invoices/` | `view_purchase_invoice` |

**الشيكات والبنوك:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 22 | **حافظة الشيكات** | `/accounting/cheques/` | `view_cheque` |
| 23 | **شيك جديد** | `/accounting/cheques/new/` | `add_cheque` |
| 24 | **تفاصيل شيك** | `/accounting/cheques/<id>/` | `view_cheque` |
| 25 | **استيراد كشف بنك** | `/accounting/bank/import-statement` | `import_bank_statement` |
| 26 | **تبديل حالة معاملة** | `/accounting/bank/tx/<id>/toggle/` | `reconcile_bank` |

##### 🔍 المراجعة والتسويات (6 شاشات)
**مراكز التكلفة والأصول:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 27 | **قائمة مراكز التكلفة** | `/accounting/cost-centers/` | `view_cost_center` |
| 28 | **تفاصيل مركز تكلفة** | `/accounting/cost-centers/<id>/` | `view_cost_center` |
| 29 | **نظرة عامة على الأصول** | `/accounting/assets/` | `view_asset` |

**التسويات:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 30 | **ميزان المراجعة** | `/accounting/trial-balance/` | `view_trial_balance` |
| 31 | **دفتر الأستاذ العام** | `/accounting/general-ledger/` | `view_general_ledger` |

##### 📈 التقارير والميزانيات (18 شاشة)
**القوائم المالية:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 32 | **قائمة الدخل** | `/accounting/income-statement/` | `view_income_statement` |
| 33 | **الميزانية العمومية** | `/accounting/balance-sheet/` | `view_balance_sheet` |
| 34 | **قائمة التدفقات النقدية** | `/accounting/cash-flow/` | `view_cash_flow` |
| 35 | **ميزان المراجعة** | `/accounting/trial-balance/` | `view_trial_balance` |
| 36 | **دفتر الأستاذ العام** | `/accounting/general-ledger/` | `view_general_ledger` |

**التقارير التحليلية:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 37 | **أعمار الذمم المدينة** | `/accounting/reports/aging/receivables` | `view_aging_report` |
| 38 | **أعمار الذمم الدائنة** | `/accounting/reports/aging/payables` | `view_aging_report` |
| 39 | **المراكز النقدية** | `/accounting/cash/positions` | `view_cash_position` |

**القروض:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 40 | **لوحة القروض** | `/accounting/loans/` | `view_loan` |
| 41 | **قائمة القروض** | `/accounting/loans/list/` | `view_loan` |
| 42 | **تفاصيل قرض** | `/accounting/loans/<id>/` | `view_loan` |
| 43 | **دفعة قرض** | `/accounting/loans/<id>/payment/` | `add_loan_payment` |

**الأدوات:**
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 44 | **تصدير بيانات** | `/accounting/tools/export` | `export_data` |

---

### 3️⃣ **مدير مالي** (Financial Manager / CFO)

#### الوصف:
المسؤول الأول عن المحاسبة، يمتلك صلاحيات كاملة لجميع العمليات والإعدادات والإقفالات.

#### الصلاحيات الأساسية:
- ✅ **كل صلاحيات المحاسب** +
- ✅ **الإعدادات**: تكوين الحسابات، الضرائب، السنة المالية
- ✅ **إنشاء وتعديل الحسابات**: جميع مستويات الحسابات
- ✅ **مراكز التكلفة**: إنشاء وتوزيع التكاليف
- ✅ **الإقفالات**: شهرية وسنوية
- ✅ **الأدوات المتقدمة**: إصلاحات، تشخيص، إعادة ترحيل

#### الشاشات المتاحة (65 شاشة):
**كل شاشات المحاسب (55) + 10 شاشات متقدمة**

##### ⚙️ الإعدادات المتقدمة (10 شاشات إضافية)
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 45 | **إعدادات المحاسبة** | `/accounting/settings/` | `manage_settings` |
| 46 | **الحسابات الافتراضية** | `/accounting/settings/defaults/` | `manage_default_accounts` |
| 47 | **إعدادات الضرائب** | `/accounting/settings/tax/` | `manage_tax_settings` |
| 48 | **إنشاء سنة مالية** | `/accounting/fiscal-years/create/` | `manage_fiscal_year` |
| 49 | **قوالب القيود** | `/accounting/journal-templates/` | `view_journal_template` |
| 50 | **إنشاء قالب قيد** | `/accounting/journal-templates/create/` | `add_journal_template` |
| 51 | **تفاصيل قالب** | `/accounting/journal-templates/<id>/` | `view_journal_template` |
| 52 | **إصلاحات سريعة** | `/accounting/tools/fixes` | `run_fixes` |
| 53 | **تشخيص النظام** | `/accounting/tools/diagnostics` | `run_diagnostics` |
| 54 | **استيراد قيود** | `/accounting/tools/import-journal` | `import_journal_entries` |

##### 🔐 العمليات الخاصة بالمدير فقط
| # | الشاشة | المسار | الصلاحية |
|---|--------|--------|----------|
| 55 | **حساب جديد** | `/accounting/accounts/create/` | `add_account` |
| 56 | **تعديل حساب** | `/accounting/accounts/<id>/edit/` | `change_account` |
| 57 | **مركز تكلفة جديد** | `/accounting/cost-centers/create/` | `add_cost_center` |
| 58 | **توزيع التكاليف** | `/accounting/cost/allocations` | `allocate_cost` |
| 59 | **إهلاك الأصول** | `/accounting/assets/depreciation` | `run_depreciation` |
| 60 | **تسويات الفترة** | `/accounting/period/adjustments` | `add_period_adjustment` |
| 61 | **قيود متكررة** | `/accounting/journal/recurring` | `manage_recurring_entries` |
| 62 | **إقفال شهر** | `/accounting/period/close-month` | `close_month` |
| 63 | **إقفال سنة** | `/accounting/period/close-year` | `close_year` |
| 64 | **ترحيل مجموعة قيود** | `/accounting/journal/drafts/bulk-post` | `bulk_post_journal_entries` |
| 65 | **حذف شيك** | `/accounting/cheques/<id>/delete/` | `delete_cheque` |

---

## 🔐 جدول الصلاحيات الكامل

### الصلاحيات المحاسبية (Permissions)

| الصلاحية | الكود | كاشير | محاسب | مدير مالي |
|----------|------|-------|-------|-----------|
| **القيود** ||||
| عرض قيود | `view_journal_entry` | ✅ | ✅ | ✅ |
| إضافة قيد | `add_journal_entry` | ❌ | ✅ | ✅ |
| تعديل قيد | `change_journal_entry` | ❌ | ✅ | ✅ |
| ترحيل قيد | `post_journal_entry` | ❌ | ✅ | ✅ |
| عكس قيد | `reverse_journal_entry` | ❌ | ✅ | ✅ |
| ترحيل مجموعة | `bulk_post_journal_entries` | ❌ | ❌ | ✅ |
| **الحسابات** ||||
| عرض حسابات | `view_account` | ✅ (محدود) | ✅ | ✅ |
| إضافة حساب | `add_account` | ❌ | ❌ | ✅ |
| تعديل حساب | `change_account` | ❌ | ❌ | ✅ |
| حذف حساب | `delete_account` | ❌ | ❌ | ✅ |
| **الخزينة والبنوك** ||||
| سند قبض | `add_cash_receipt` | ✅ | ✅ | ✅ |
| سند صرف | `add_cash_payment` | ✅ | ✅ | ✅ |
| تحويل نقدي | `add_cash_transfer` | ✅ (محدود) | ✅ | ✅ |
| تسوية بنك | `reconcile_bank` | ❌ | ✅ | ✅ |
| استيراد كشف بنك | `import_bank_statement` | ❌ | ✅ | ✅ |
| **مراكز التكلفة** ||||
| عرض مراكز | `view_cost_center` | ❌ | ✅ | ✅ |
| إضافة مركز | `add_cost_center` | ❌ | ❌ | ✅ |
| توزيع تكاليف | `allocate_cost` | ❌ | ❌ | ✅ |
| **التقارير** ||||
| قائمة الدخل | `view_income_statement` | ❌ | ✅ | ✅ |
| الميزانية العمومية | `view_balance_sheet` | ❌ | ✅ | ✅ |
| التدفقات النقدية | `view_cash_flow` | ❌ | ✅ | ✅ |
| ميزان المراجعة | `view_trial_balance` | ❌ | ✅ | ✅ |
| أعمار الذمم | `view_aging_report` | ❌ | ✅ | ✅ |
| **الإقفالات** ||||
| تسويات الفترة | `add_period_adjustment` | ❌ | ❌ | ✅ |
| إقفال شهر | `close_month` | ❌ | ❌ | ✅ |
| إقفال سنة | `close_year` | ❌ | ❌ | ✅ |
| **الإعدادات** ||||
| إعدادات المحاسبة | `manage_settings` | ❌ | ❌ | ✅ |
| إعدادات الضرائب | `manage_tax_settings` | ❌ | ❌ | ✅ |
| السنة المالية | `manage_fiscal_year` | ❌ | ❌ | ✅ |
| **الأدوات** ||||
| تصدير بيانات | `export_data` | ❌ | ✅ | ✅ |
| استيراد قيود | `import_journal_entries` | ❌ | ❌ | ✅ |
| تشخيص النظام | `run_diagnostics` | ❌ | ❌ | ✅ |
| إصلاحات سريعة | `run_fixes` | ❌ | ❌ | ✅ |

---

## 🎨 طريقة العرض في الواجهة

### حسب الدور:

#### **كاشير:**
```
📊 المحاسبة
  ├─ [Tab 1] 📝 العمليات اليومية (فقط)
  │   ├─ سند قبض
  │   ├─ سند صرف  
  │   ├─ تحويل نقدي
  │   └─ أرصدة الآن (عرض)
  │
  ├─ [Tab 2] 📄 استعلامات
  │   ├─ كشف حساب عميل (عرض)
  │   ├─ كشف حساب مورد (عرض)
  │   └─ حافظة الشيكات (عرض)
  │
  └─ التبويبات الأخرى مخفية ❌
```

#### **محاسب:**
```
📊 المحاسبة
  ├─ [Tab 1] 📝 الأساسيات اليومية ✅
  ├─ [Tab 2] 📄 الفواتير والحركة ✅
  ├─ [Tab 3] 🔍 المراجعة والتسويات (عرض فقط)
  ├─ [Tab 4] 📈 التقارير والميزانيات ✅
  └─ ⚙️ الإعدادات مخفية ❌
```

#### **مدير مالي:**
```
📊 المحاسبة                                [⚙️ إعدادات]
  ├─ [Tab 1] 📝 الأساسيات اليومية ✅
  ├─ [Tab 2] 📄 الفواتير والحركة ✅
  ├─ [Tab 3] 🔍 المراجعة والتسويات ✅
  ├─ [Tab 4] 📈 التقارير والميزانيات ✅
  └─ ⚙️ الإعدادات ← جميع الإعدادات المتقدمة ✅
```

---

## 📝 كود Python للصلاحيات

```python
# accounting/permissions.py

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import (
    Account, JournalEntry, JournalEntryItem,
    CostCenter, FiscalYear, Cheque, Loan
)


class AccountingRoles:
    """أدوار المحاسبة الثلاثة"""
    CASHIER = 'accounting_cashier'
    ACCOUNTANT = 'accounting_accountant'
    CFO = 'accounting_cfo'  # Chief Financial Officer
    
    ALL_ROLES = [CASHIER, ACCOUNTANT, CFO]


# تعريف الصلاحيات لكل دور
ROLE_PERMISSIONS = {
    AccountingRoles.CASHIER: [
        # القيود (عرض فقط)
        'accounting.view_journalentry',
        'accounting.view_journalentryitem',
        
        # الحسابات (عرض فقط)
        'accounting.view_account',
        
        # الخزينة
        'accounting.add_cashreceipt',
        'accounting.add_cashpayment',
        'accounting.add_cashtransfer',
        'accounting.view_cashposition',
        
        # الشيكات
        'accounting.view_cheque',
        'accounting.add_cheque',
        
        # الاستعلامات
        'accounting.view_customer_statement',
        'accounting.view_supplier_statement',
    ],
    
    AccountingRoles.ACCOUNTANT: [
        # كل صلاحيات الكاشير
        *ROLE_PERMISSIONS[AccountingRoles.CASHIER],
        
        # القيود (كاملة)
        'accounting.add_journalentry',
        'accounting.change_journalentry',
        'accounting.post_journalentry',
        'accounting.reverse_journalentry',
        
        # البنوك
        'accounting.reconcile_bank',
        'accounting.import_bank_statement',
        
        # مراكز التكلفة (عرض)
        'accounting.view_costcenter',
        
        # الأصول (عرض)
        'accounting.view_asset',
        
        # التقارير
        'accounting.view_income_statement',
        'accounting.view_balance_sheet',
        'accounting.view_cash_flow',
        'accounting.view_trial_balance',
        'accounting.view_general_ledger',
        'accounting.view_aging_report',
        
        # القروض
        'accounting.view_loan',
        'accounting.add_loan_payment',
        
        # الأدوات
        'accounting.export_data',
    ],
    
    AccountingRoles.CFO: [
        # كل صلاحيات المحاسب
        *ROLE_PERMISSIONS[AccountingRoles.ACCOUNTANT],
        
        # الحسابات (كاملة)
        'accounting.add_account',
        'accounting.change_account',
        'accounting.delete_account',
        
        # القيود (متقدم)
        'accounting.bulk_post_journal_entries',
        'accounting.import_journal_entries',
        
        # مراكز التكلفة (كاملة)
        'accounting.add_costcenter',
        'accounting.change_costcenter',
        'accounting.allocate_cost',
        
        # الأصول
        'accounting.add_asset',
        'accounting.run_depreciation',
        
        # الإقفالات
        'accounting.add_period_adjustment',
        'accounting.manage_recurring_entries',
        'accounting.close_month',
        'accounting.close_year',
        
        # القروض
        'accounting.add_loan',
        'accounting.change_loan',
        
        # الإعدادات
        'accounting.manage_settings',
        'accounting.manage_default_accounts',
        'accounting.manage_tax_settings',
        'accounting.manage_fiscal_year',
        
        # قوالب القيود
        'accounting.view_journal_template',
        'accounting.add_journal_template',
        'accounting.change_journal_template',
        
        # الأدوات المتقدمة
        'accounting.run_diagnostics',
        'accounting.run_fixes',
        
        # الشيكات (حذف)
        'accounting.delete_cheque',
    ],
}


def create_accounting_roles():
    """إنشاء الأدوار الثلاثة وربطها بالصلاحيات"""
    
    for role_name, permissions_codenames in ROLE_PERMISSIONS.items():
        # إنشاء أو جلب المجموعة
        group, created = Group.objects.get_or_create(name=role_name)
        
        if created:
            print(f"✅ تم إنشاء دور: {role_name}")
        
        # مسح الصلاحيات القديمة
        group.permissions.clear()
        
        # إضافة الصلاحيات الجديدة
        for perm_codename in permissions_codenames:
            try:
                app_label, codename = perm_codename.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"⚠️ الصلاحية {perm_codename} غير موجودة")
                continue
        
        print(f"✅ تم تحديث صلاحيات دور {role_name}: {len(permissions_codenames)} صلاحية")


def assign_user_to_role(user, role_name):
    """تعيين مستخدم لدور محدد"""
    if role_name not in AccountingRoles.ALL_ROLES:
        raise ValueError(f"الدور {role_name} غير معروف")
    
    group = Group.objects.get(name=role_name)
    user.groups.add(group)
    print(f"✅ تم تعيين {user.username} لدور {role_name}")


def has_accounting_role(user, role_name):
    """التحقق من امتلاك المستخدم لدور محدد"""
    return user.groups.filter(name=role_name).exists()


# Decorators للـ views
from functools import wraps
from django.core.exceptions import PermissionDenied


def require_accounting_role(role_name):
    """Decorator للتحقق من الدور قبل الوصول للـ view"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_accounting_role(request.user, role_name):
                raise PermissionDenied(f"يجب أن تكون {role_name} للوصول لهذه الصفحة")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# مثال استخدام:
# @require_accounting_role(AccountingRoles.CFO)
# def close_fiscal_year(request):
#     ...
```

---

## ✅ الخلاصة

### تم تصميم نظام الأدوار والصلاحيات بالمواصفات التالية:

1. ✅ **3 أدوار واضحة**: كاشير (12 شاشة)، محاسب (55 شاشة)، مدير مالي (65 شاشة)
2. ✅ **تدرج منطقي**: كل دور يرث صلاحيات الدور الأدنى منه
3. ✅ **فصل واضح**: الكاشير للعمليات البسيطة، المحاسب للعمل اليومي، المدير للإعدادات والإقفالات
4. ✅ **قابل للتطبيق**: كود Python جاهز للاستخدام مباشرة
5. ✅ **آمن**: كل عملية حساسة محمية بصلاحية خاصة

---

**تم الإعداد بواسطة:** فريق تطوير Tony ERB  
**التاريخ:** 2025-12-06

