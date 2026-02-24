"""
نظام الصلاحيات والأدوار المحاسبية
=====================================

هذا الملف يحدد 3 أدوار رئيسية:
1. كاشير/مندوب (Cashier) - 12 شاشة
2. محاسب (Accountant) - 55 شاشة  
3. مدير مالي (CFO) - 65 شاشة
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps


class AccountingRoles:
    """أدوار المحاسبة الثلاثة"""
    CASHIER = 'accounting_cashier'
    ACCOUNTANT = 'accounting_accountant'
    CFO = 'accounting_cfo'  # Chief Financial Officer
    
    ALL_ROLES = [CASHIER, ACCOUNTANT, CFO]
    
    ROLE_LABELS = {
        CASHIER: 'كاشير / مندوب',
        ACCOUNTANT: 'محاسب',
        CFO: 'مدير مالي',
    }


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
        # كل صلاحيات الكاشير (سيتم إضافتها تلقائياً)
        
        # القيود (كاملة)
        'accounting.add_journalentry',
        'accounting.change_journalentry',
        'accounting.delete_journalentry',
        'accounting.post_journalentry',
        'accounting.reverse_journalentry',
        
        # البنوك
        'accounting.reconcile_bank',
        'accounting.import_bank_statement',
        'accounting.view_banktransaction',
        'accounting.change_banktransaction',
        
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
        'accounting.add_loanpayment',
        
        # الأدوات
        'accounting.export_data',
        
        # الشيكات
        'accounting.change_cheque',
    ],
    
    AccountingRoles.CFO: [
        # كل صلاحيات المحاسب (سيتم إضافتها تلقائياً)
        
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
        'accounting.delete_costcenter',
        'accounting.allocate_cost',
        
        # الأصول
        'accounting.add_asset',
        'accounting.change_asset',
        'accounting.run_depreciation',
        
        # الإقفالات
        'accounting.add_period_adjustment',
        'accounting.manage_recurring_entries',
        'accounting.close_month',
        'accounting.close_year',
        
        # القروض
        'accounting.add_loan',
        'accounting.change_loan',
        'accounting.delete_loan',
        
        # الإعدادات
        'accounting.manage_settings',
        'accounting.manage_default_accounts',
        'accounting.manage_tax_settings',
        'accounting.manage_fiscal_year',
        
        # قوالب القيود
        'accounting.view_journal_template',
        'accounting.add_journal_template',
        'accounting.change_journal_template',
        'accounting.delete_journal_template',
        
        # الأدوات المتقدمة
        'accounting.run_diagnostics',
        'accounting.run_fixes',
        
        # الشيكات (حذف)
        'accounting.delete_cheque',
        
        # السنوات المالية
        'accounting.add_fiscalyear',
        'accounting.change_fiscalyear',
        'accounting.delete_fiscalyear',
    ],
}


def get_role_permissions_with_inheritance(role_name):
    """
    الحصول على صلاحيات الدور مع الوراثة
    المحاسب يرث صلاحيات الكاشير
    المدير المالي يرث صلاحيات المحاسب (وبالتالي الكاشير)
    """
    permissions = set()
    
    if role_name == AccountingRoles.CASHIER:
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.CASHIER])
    
    elif role_name == AccountingRoles.ACCOUNTANT:
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.CASHIER])
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.ACCOUNTANT])
    
    elif role_name == AccountingRoles.CFO:
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.CASHIER])
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.ACCOUNTANT])
        permissions.update(ROLE_PERMISSIONS[AccountingRoles.CFO])
    
    return list(permissions)


def create_accounting_roles():
    """إنشاء الأدوار الثلاثة وربطها بالصلاحيات"""
    
    results = {
        'created': [],
        'updated': [],
        'errors': []
    }
    
    for role_name in AccountingRoles.ALL_ROLES:
        try:
            # إنشاء أو جلب المجموعة
            group, created = Group.objects.get_or_create(name=role_name)
            
            if created:
                results['created'].append(role_name)
                print(f"✅ تم إنشاء دور: {AccountingRoles.ROLE_LABELS[role_name]}")
            else:
                results['updated'].append(role_name)
                print(f"🔄 تحديث دور: {AccountingRoles.ROLE_LABELS[role_name]}")
            
            # مسح الصلاحيات القديمة
            group.permissions.clear()
            
            # الحصول على الصلاحيات مع الوراثة
            permissions_codenames = get_role_permissions_with_inheritance(role_name)
            
            # إضافة الصلاحيات الجديدة
            added_count = 0
            for perm_codename in permissions_codenames:
                try:
                    app_label, codename = perm_codename.split('.')
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(permission)
                    added_count += 1
                except Permission.DoesNotExist:
                    print(f"⚠️ الصلاحية {perm_codename} غير موجودة (سيتم تخطيها)")
                    continue
                except Exception as e:
                    print(f"❌ خطأ في إضافة الصلاحية {perm_codename}: {str(e)}")
                    continue
            
            print(f"✅ تم إضافة {added_count} صلاحية لدور {AccountingRoles.ROLE_LABELS[role_name]}")
            
        except Exception as e:
            error_msg = f"خطأ في إنشاء دور {role_name}: {str(e)}"
            results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    return results


def assign_user_to_role(user, role_name):
    """تعيين مستخدم لدور محدد"""
    if role_name not in AccountingRoles.ALL_ROLES:
        raise ValueError(f"الدور {role_name} غير معروف. الأدوار المتاحة: {AccountingRoles.ALL_ROLES}")
    
    try:
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        print(f"✅ تم تعيين {user.username} لدور {AccountingRoles.ROLE_LABELS[role_name]}")
        return True
    except Group.DoesNotExist:
        print(f"❌ الدور {role_name} غير موجود. قم بإنشائه أولاً باستخدام create_accounting_roles()")
        return False


def remove_user_from_role(user, role_name):
    """إزالة مستخدم من دور محدد"""
    if role_name not in AccountingRoles.ALL_ROLES:
        raise ValueError(f"الدور {role_name} غير معروف")
    
    try:
        group = Group.objects.get(name=role_name)
        user.groups.remove(group)
        print(f"✅ تم إزالة {user.username} من دور {AccountingRoles.ROLE_LABELS[role_name]}")
        return True
    except Group.DoesNotExist:
        print(f"❌ الدور {role_name} غير موجود")
        return False


def has_accounting_role(user, role_name):
    """التحقق من امتلاك المستخدم لدور محدد"""
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=role_name).exists()


def get_user_accounting_role(user):
    """الحصول على دور المستخدم المحاسبي (الأعلى إذا كان لديه أكثر من دور)"""
    if not user.is_authenticated:
        return None
    
    # ترتيب الأدوار من الأعلى للأدنى
    for role in [AccountingRoles.CFO, AccountingRoles.ACCOUNTANT, AccountingRoles.CASHIER]:
        if has_accounting_role(user, role):
            return role
    
    return None


# Decorators للـ views
def require_accounting_role(role_name):
    """
    Decorator للتحقق من الدور قبل الوصول للـ view
    
    الاستخدام:
    @require_accounting_role(AccountingRoles.CFO)
    def close_fiscal_year(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("يجب تسجيل الدخول أولاً")
            
            if not has_accounting_role(request.user, role_name):
                role_label = AccountingRoles.ROLE_LABELS.get(role_name, role_name)
                raise PermissionDenied(f"يجب أن تكون {role_label} للوصول لهذه الصفحة")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_accounting_permission(*permissions):
    """
    Decorator للتحقق من صلاحية محددة
    
    الاستخدام:
    @require_accounting_permission('accounting.add_journalentry')
    def create_journal_entry(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("يجب تسجيل الدخول أولاً")
            
            for perm in permissions:
                if not request.user.has_perm(perm):
                    raise PermissionDenied(f"ليس لديك صلاحية {perm}")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def can_user_access_accounting_screen(user, screen_id):
    """
    التحقق من إمكانية وصول المستخدم لشاشة محددة
    بناءً على دوره المحاسبي
    """
    if not user.is_authenticated:
        return False
    
    # المدير المالي يصل لكل شيء
    if has_accounting_role(user, AccountingRoles.CFO):
        return True
    
    # تحديد الشاشات المتاحة لكل دور
    CASHIER_SCREENS = [
        'accounting_dashboard', 'cash_receipt', 'cash_payment', 'cash_transfer',
        'cash_positions', 'customer_statement', 'supplier_statement', 
        'cheque_list', 'cheque_create', 'journal_entries_list', 'journal_entry_detail',
        'chart_of_accounts'
    ]
    
    ACCOUNTANT_SCREENS = CASHIER_SCREENS + [
        'journal_entry_create', 'journal_drafts', 'post_journal_entry',
        'reverse_journal_entry', 'bank_reconcile', 'bank_statement_import',
        'cost_centers_list', 'cost_center_detail', 'assets_overview',
        'trial_balance', 'general_ledger', 'income_statement', 'balance_sheet',
        'cash_flow_statement', 'aging_receivables', 'aging_payables',
        'loans_list', 'loan_detail', 'loan_payment', 'export_data'
    ]
    
    if has_accounting_role(user, AccountingRoles.ACCOUNTANT):
        return screen_id in ACCOUNTANT_SCREENS
    
    if has_accounting_role(user, AccountingRoles.CASHIER):
        return screen_id in CASHIER_SCREENS
    
    return False


# Context processor لإضافة معلومات الدور للـ templates
def accounting_role_context(request):
    """
    Context processor لإضافة معلومات دور المستخدم المحاسبي
    يتم إضافته في settings.py ضمن TEMPLATES -> context_processors
    """
    if not request.user.is_authenticated:
        return {}
    
    user_role = get_user_accounting_role(request.user)
    
    return {
        'user_accounting_role': user_role,
        'user_accounting_role_label': AccountingRoles.ROLE_LABELS.get(user_role, ''),
        'is_accounting_cashier': has_accounting_role(request.user, AccountingRoles.CASHIER),
        'is_accounting_accountant': has_accounting_role(request.user, AccountingRoles.ACCOUNTANT),
        'is_accounting_cfo': has_accounting_role(request.user, AccountingRoles.CFO),
    }

