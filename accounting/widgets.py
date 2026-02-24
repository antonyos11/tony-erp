"""
Widgets للميزات المتقدمة للمحاسبة
يمكن استدعاءها من أي صفحة رئيسية
"""
from django.db.models import Count, Q
from accounting.models import (
    BankReconciliation, 
    RecurringJournalEntry, 
    BudgetItem,
    Asset,
    PeriodClose,
    CustomReport,
    ReceivableAging
)


def get_advanced_features_stats(user):
    """
    الحصول على إحصائيات الميزات المتقدمة
    Returns:
        dict: إحصائيات الميزات المتقدمة
    """
    stats = {
        # التسويات البنكية
        'pending_reconciliations': BankReconciliation.objects.filter(status='pending').count(),
        'completed_reconciliations': BankReconciliation.objects.filter(status='completed').count(),
        
        # القيود المتكررة النشطة
        'active_recurring_entries': RecurringJournalEntry.objects.filter(is_active=True).count(),
        
        # الموازنات المتجاوزة
        'over_budget_items': 0,  # سيتم حسابها لاحقاً
        
        # الأصول الثابتة
        'total_assets': Asset.objects.count(),
        'depreciation_pending': 0,  # سيتم حسابها لاحقاً
        
        # الفترات المفتوحة
        'open_periods': PeriodClose.objects.filter(status='open').count(),
        
        # التقارير المخصصة للمستخدم
        'custom_reports': CustomReport.objects.filter(created_by=user).count() if user.is_authenticated else 0,
        
        # الذمم المتأخرة (أكثر من 90 يوم)
        'overdue_aging': 0,  # سيتم حسابها لاحقاً
        
        # إجمالي الميزات المتاحة
        'total_features': 15,
    }
    
    return stats


def get_quick_access_features():
    """
    الحصول على قائمة الميزات للوصول السريع
    Returns:
        list: قائمة الميزات المتقدمة
    """
    features = [
        {
            'name': 'لوحة CFO',
            'url': 'accounting:cfo_dashboard',
            'icon': 'bi-tachometer-alt',
            'color': 'primary',
            'badge': 'موصى به',
        },
        {
            'name': 'التحليل المالي',
            'url': 'accounting:financial_analysis_page',
            'icon': 'bi-chart-line',
            'color': 'info',
        },
        {
            'name': 'التسويات البنكية',
            'url': 'accounting:bank_reconciliation_list',
            'icon': 'bi-balance-scale',
            'color': 'success',
        },
        {
            'name': 'الموازنات',
            'url': 'accounting:budget_dashboard',
            'icon': 'bi-chart-bar',
            'color': 'purple',
        },
        {
            'name': 'إدارة الأصول',
            'url': 'accounting:assets_list_advanced',
            'icon': 'bi-boxes',
            'color': 'dark',
        },
        {
            'name': 'التقارير المخصصة',
            'url': 'accounting:custom_reports',
            'icon': 'bi-magic',
            'color': 'warning',
        },
    ]
    
    return features
