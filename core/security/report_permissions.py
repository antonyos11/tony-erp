"""
Report Permissions & Configuration
نظام صلاحيات التقارير وتنظيمها حسب الأدوار
"""

from typing import List, Dict, Optional
from django.contrib.auth.models import User

from core.security.permissions_service import PermissionService
from core.security.role_definitions import (
    ROLE_OWNER,
    ROLE_FIN_MANAGER,
    ROLE_ACCOUNTANT,
    ROLE_INV_MANAGER,
    ROLE_STORE_KEEPER,
    ROLE_SALES_MANAGER,
    ROLE_SALES_STAFF,
    ROLE_PROD_MANAGER,
    ROLE_HR_STAFF,
    ROLE_VIEWER,
)


# ============================================================================
# Report Categories
# ============================================================================

class ReportCategory:
    """فئات التقارير"""
    FINANCIAL = 'financial'  # التقارير المالية
    SALES = 'sales'  # تقارير المبيعات
    INVENTORY = 'inventory'  # تقارير المخزون
    PURCHASES = 'purchases'  # تقارير المشتريات
    PRODUCTION = 'production'  # تقارير الإنتاج
    HR = 'hr'  # تقارير الموارد البشرية
    CRM = 'crm'  # تقارير علاقات العملاء
    OPERATIONAL = 'operational'  # تقارير تشغيلية


class ReportSensitivity:
    """مستوى حساسية التقرير"""
    PUBLIC = 'public'  # عام - الكل يراه
    RESTRICTED = 'restricted'  # محدود - لأدوار معينة
    CONFIDENTIAL = 'confidential'  # سري - للإدارة العليا فقط
    HIGHLY_CONFIDENTIAL = 'highly_confidential'  # سري للغاية - للمالك فقط


# ============================================================================
# Report Definitions
# ============================================================================

REPORTS_CATALOG = [
    # ========================================================================
    # التقارير المالية
    # ========================================================================
    {
        'id': 'trial_balance',
        'name': 'ميزان المراجعة',
        'category': ReportCategory.FINANCIAL,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'accounting:trial_balance',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT],
        'description': 'ميزان المراجعة لكل الحسابات',
    },
    {
        'id': 'income_statement',
        'name': 'قائمة الدخل',
        'category': ReportCategory.FINANCIAL,
        'sensitivity': ReportSensitivity.CONFIDENTIAL,
        'url': 'accounting:income_statement',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER],
        'description': 'قائمة الأرباح والخسائر',
        'shows_profit': True,
    },
    {
        'id': 'balance_sheet',
        'name': 'الميزانية العمومية',
        'category': ReportCategory.FINANCIAL,
        'sensitivity': ReportSensitivity.CONFIDENTIAL,
        'url': 'accounting:balance_sheet',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER],
        'description': 'الميزانية العمومية',
    },
    {
        'id': 'cash_flow',
        'name': 'التدفقات النقدية',
        'category': ReportCategory.FINANCIAL,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'accounting:cash_flow',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT],
        'description': 'تقرير التدفقات النقدية',
    },
    {
        'id': 'aged_receivables',
        'name': 'أعمار الذمم المدينة',
        'category': ReportCategory.FINANCIAL,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'accounting:aged_receivables',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_ACCOUNTANT, ROLE_SALES_MANAGER],
        'description': 'تقرير أعمار الذمم المدينة (العملاء)',
    },
    
    # ========================================================================
    # تقارير المبيعات
    # ========================================================================
    {
        'id': 'sales_summary',
        'name': 'ملخص المبيعات',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:sales_summary',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_SALES_MANAGER, ROLE_VIEWER],
        'description': 'ملخص المبيعات حسب الفترة',
    },
    {
        'id': 'sales_by_product',
        'name': 'المبيعات حسب الصنف',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:sales_by_product',
        'allowed_roles': [ROLE_OWNER, ROLE_SALES_MANAGER, ROLE_INV_MANAGER, ROLE_VIEWER],
        'description': 'تقرير المبيعات مقسمة حسب الأصناف',
    },
    {
        'id': 'sales_by_customer',
        'name': 'المبيعات حسب العميل',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:sales_by_customer',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_SALES_MANAGER],
        'description': 'تقرير المبيعات مقسمة حسب العملاء',
    },
    {
        'id': 'sales_by_salesperson',
        'name': 'المبيعات حسب المندوب',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:sales_by_salesperson',
        'allowed_roles': [ROLE_OWNER, ROLE_SALES_MANAGER],
        'description': 'تقرير أداء مندوبي المبيعات',
        'exclude_from_staff': True,  # المندوبون لا يرون أداء زملائهم
    },
    {
        'id': 'my_sales',
        'name': 'مبيعاتي',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.PUBLIC,
        'url': 'reports:my_sales',
        'allowed_roles': [ROLE_SALES_STAFF],
        'description': 'تقرير مبيعاتي الشخصية',
        'personal': True,
    },
    {
        'id': 'profit_by_invoice',
        'name': 'الأرباح حسب الفاتورة',
        'category': ReportCategory.SALES,
        'sensitivity': ReportSensitivity.HIGHLY_CONFIDENTIAL,
        'url': 'reports:profit_by_invoice',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER],
        'description': 'تقرير الأرباح التفصيلي لكل فاتورة',
        'shows_profit': True,
        'shows_cost': True,
    },
    
    # ========================================================================
    # تقارير المخزون
    # ========================================================================
    {
        'id': 'stock_status',
        'name': 'حالة المخزون',
        'category': ReportCategory.INVENTORY,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:stock_status',
        'allowed_roles': [ROLE_OWNER, ROLE_INV_MANAGER, ROLE_STORE_KEEPER, ROLE_VIEWER],
        'description': 'تقرير حالة المخزون الحالية',
    },
    {
        'id': 'stock_movements',
        'name': 'حركات المخزون',
        'category': ReportCategory.INVENTORY,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:stock_movements',
        'allowed_roles': [ROLE_OWNER, ROLE_INV_MANAGER, ROLE_STORE_KEEPER],
        'description': 'تقرير حركات المخزون',
    },
    {
        'id': 'low_stock_alert',
        'name': 'تنبيه النواقص',
        'category': ReportCategory.INVENTORY,
        'sensitivity': ReportSensitivity.PUBLIC,
        'url': 'reports:low_stock',
        'allowed_roles': [ROLE_OWNER, ROLE_INV_MANAGER, ROLE_STORE_KEEPER, ROLE_SALES_MANAGER],
        'description': 'الأصناف أقل من حد إعادة الطلب',
    },
    {
        'id': 'inventory_valuation',
        'name': 'تقييم المخزون',
        'category': ReportCategory.INVENTORY,
        'sensitivity': ReportSensitivity.CONFIDENTIAL,
        'url': 'reports:inventory_valuation',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_INV_MANAGER],
        'description': 'تقرير قيمة المخزون بالتكلفة',
        'shows_cost': True,
    },
    {
        'id': 'slow_moving_items',
        'name': 'الأصناف البطيئة',
        'category': ReportCategory.INVENTORY,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:slow_moving',
        'allowed_roles': [ROLE_OWNER, ROLE_INV_MANAGER, ROLE_SALES_MANAGER],
        'description': 'تقرير الأصناف البطيئة والراكدة',
    },
    
    # ========================================================================
    # تقارير المشتريات
    # ========================================================================
    {
        'id': 'purchase_summary',
        'name': 'ملخص المشتريات',
        'category': ReportCategory.PURCHASES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:purchase_summary',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_INV_MANAGER, ROLE_VIEWER],
        'description': 'ملخص المشتريات حسب الفترة',
    },
    {
        'id': 'purchase_by_supplier',
        'name': 'المشتريات حسب المورد',
        'category': ReportCategory.PURCHASES,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:purchase_by_supplier',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER, ROLE_INV_MANAGER],
        'description': 'تقرير المشتريات مقسمة حسب الموردين',
    },
    
    # ========================================================================
    # تقارير الإنتاج
    # ========================================================================
    {
        'id': 'production_summary',
        'name': 'ملخص الإنتاج',
        'category': ReportCategory.PRODUCTION,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:production_summary',
        'allowed_roles': [ROLE_OWNER, ROLE_PROD_MANAGER, ROLE_VIEWER],
        'description': 'ملخص أوامر الإنتاج',
    },
    {
        'id': 'production_efficiency',
        'name': 'كفاءة الإنتاج',
        'category': ReportCategory.PRODUCTION,
        'sensitivity': ReportSensitivity.CONFIDENTIAL,
        'url': 'reports:production_efficiency',
        'allowed_roles': [ROLE_OWNER, ROLE_PROD_MANAGER],
        'description': 'تقرير كفاءة الإنتاج والهدر',
    },
    
    # ========================================================================
    # تقارير الموارد البشرية
    # ========================================================================
    {
        'id': 'attendance_summary',
        'name': 'ملخص الحضور',
        'category': ReportCategory.HR,
        'sensitivity': ReportSensitivity.RESTRICTED,
        'url': 'reports:attendance',
        'allowed_roles': [ROLE_OWNER, ROLE_HR_STAFF],
        'description': 'ملخص حضور وغياب الموظفين',
    },
    {
        'id': 'payroll_summary',
        'name': 'ملخص الرواتب',
        'category': ReportCategory.HR,
        'sensitivity': ReportSensitivity.CONFIDENTIAL,
        'url': 'reports:payroll',
        'allowed_roles': [ROLE_OWNER, ROLE_FIN_MANAGER],
        'description': 'ملخص كشوف الرواتب',
    },
]


# ============================================================================
# Report Permission Service
# ============================================================================

class ReportPermissionService:
    """خدمة فحص صلاحيات التقارير"""
    
    @staticmethod
    def get_available_reports(user: User, category: Optional[str] = None) -> List[Dict]:
        """
        الحصول على التقارير المتاحة للمستخدم
        
        Args:
            user: المستخدم
            category: فلترة حسب الفئة (اختياري)
        
        Returns:
            قائمة التقارير المسموح بها
        """
        if not user or not user.is_authenticated:
            return []
        
        available_reports = []
        user_roles = PermissionService.get_user_roles(user)
        user_role_codes = [role.name for role in user_roles]
        
        for report in REPORTS_CATALOG:
            # فلترة حسب الفئة إذا طُلبت
            if category and report['category'] != category:
                continue
            
            # فحص إذا كان super admin
            if user.is_superuser:
                available_reports.append(report)
                continue
            
            # فحص الأدوار المسموح بها
            allowed_roles = report.get('allowed_roles', [])
            if any(role in user_role_codes for role in allowed_roles):
                # فحص إضافي: التقارير الشخصية أو المستثناة
                if report.get('personal'):
                    # التقارير الشخصية متاحة فقط لصاحبها
                    available_reports.append(report)
                elif report.get('exclude_from_staff') and ROLE_SALES_STAFF in user_role_codes:
                    # لا تعرض للموظفين العاديين
                    continue
                else:
                    available_reports.append(report)
        
        return available_reports
    
    @staticmethod
    def can_view_report(user: User, report_id: str) -> tuple[bool, str]:
        """
        فحص إذا كان المستخدم يستطيع عرض تقرير معين
        
        Returns:
            (يستطيع/لا يستطيع, رسالة)
        """
        if not user or not user.is_authenticated:
            return False, 'يجب تسجيل الدخول أولاً'
        
        if user.is_superuser:
            return True, 'مسموح'
        
        # البحث عن التقرير
        report = None
        for r in REPORTS_CATALOG:
            if r['id'] == report_id:
                report = r
                break
        
        if not report:
            return False, 'التقرير غير موجود'
        
        # فحص الأدوار
        user_roles = PermissionService.get_user_roles(user)
        user_role_codes = [role.name for role in user_roles]
        
        allowed_roles = report.get('allowed_roles', [])
        if not any(role in user_role_codes for role in allowed_roles):
            return False, 'ليس لديك الدور المطلوب لعرض هذا التقرير'
        
        return True, 'مسموح'
    
    @staticmethod
    def get_reports_by_category(user: User) -> Dict[str, List[Dict]]:
        """
        الحصول على التقارير مجموعة حسب الفئات
        
        Returns:
            dict بالفئات والتقارير المتاحة
        """
        reports_by_cat = {}
        
        all_reports = ReportPermissionService.get_available_reports(user)
        
        for report in all_reports:
            category = report['category']
            if category not in reports_by_cat:
                reports_by_cat[category] = []
            reports_by_cat[category].append(report)
        
        return reports_by_cat
    
    @staticmethod
    def get_category_label(category: str) -> str:
        """الحصول على التسمية العربية للفئة"""
        labels = {
            ReportCategory.FINANCIAL: 'التقارير المالية',
            ReportCategory.SALES: 'تقارير المبيعات',
            ReportCategory.INVENTORY: 'تقارير المخزون',
            ReportCategory.PURCHASES: 'تقارير المشتريات',
            ReportCategory.PRODUCTION: 'تقارير الإنتاج',
            ReportCategory.HR: 'تقارير الموارد البشرية',
            ReportCategory.CRM: 'تقارير علاقات العملاء',
            ReportCategory.OPERATIONAL: 'التقارير التشغيلية',
        }
        return labels.get(category, category)


