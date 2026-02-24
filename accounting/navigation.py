from __future__ import annotations
"""هيكل التنقل (Navigation) لوحدة المحاسبة.

يعتمد على مبدأ: أقسام (Sections) تحتوي عناصر (Items).
يتم تصفية العناصر حسب صلاحيات المستخدم.

يمكن لاحقاً نقل هذا الملف لمكان مركزي (مثلاً core/navigation) لو أردنا دمج الوحدات الأخرى.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Iterable, Callable
from django.utils.functional import cached_property
from django.http import HttpRequest
from django.contrib.auth.models import AbstractUser
from typing import Any, Protocol

class _HasPerms(Protocol):
    def has_perm(self, perm: str) -> bool: ...
    @property
    def is_authenticated(self) -> bool: ...
from django.db.models import Count

from .models import JournalEntry

# ---------------------------------------------------------------------------
# نماذج البيانات
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class NavItem:
    key: str
    label: str
    route: str
    permissions: List[str] = field(default_factory=list)
    icon: Optional[str] = None  # اسم أيقونة (يمكن التوحيد مع مكتبة front-end)
    shortcut: Optional[str] = None  # اختصار لوحة مفاتيح
    badge: Optional[str] = None  # اسم دالة أو context variable لحساب الرقم (ex: "count_drafts")
    new_tab: bool = False

    def is_allowed(self, user: _HasPerms) -> bool:
        return all(user.has_perm(p) for p in self.permissions)

@dataclass(slots=True)
class NavSection:
    key: str
    label: str
    items: List[NavItem]
    icon: Optional[str] = None
    description: Optional[str] = None  # وصف القسم (يظهر كـ tooltip أو subtitle)
    collapsed: bool = False  # هل القسم مطوي افتراضياً

    def visible_items(self, user: _HasPerms) -> List[NavItem]:
        return [i for i in self.items if i.is_allowed(user)]

# ---------------------------------------------------------------------------
# تعريف القائمة الأساسية (يمكن تعديلها لاحقاً)
# NOTE: استخدم صلاحيات افتراضية تقريبية؛ حدثها لتطابق نموذج الصلاحيات عندك.
# ---------------------------------------------------------------------------
BASE_NAVIGATION: List[NavSection] = [
    # 📊 لوحة المحاسبة
    NavSection(
        key="dashboard",
        label="لوحة المحاسبة",
        icon="speedometer2",
        description="نظرة عامة على الوضع المالي",
        items=[
            NavItem(key="accounting_home", label="لوحة المحاسبة", route="/accounting/", permissions=["accounting.view_account"], icon="house-door"),
        ],
    ),
    
    # 💰 العمليات النقدية (الأكثر استخداماً)
    NavSection(
        key="cash_operations",
        label="العمليات النقدية",
        icon="cash-coin",
        description="المقبوضات والمدفوعات اليومية",
        items=[
            NavItem(key="cash_receipt", label="سند قبض", route="/accounting/cash/receipt", permissions=["accounting.add_cashreceipt"], icon="arrow-down-circle", shortcut="Ctrl+Shift+R"),
            NavItem(key="cash_payment", label="سند صرف", route="/accounting/cash/payment", permissions=["accounting.add_cashpayment"], icon="arrow-up-circle", shortcut="Ctrl+Shift+P"),
            NavItem(key="cash_positions", label="الأرصدة النقدية", route="/accounting/cash/positions", permissions=["accounting.view_cashposition"], icon="wallet2"),
            NavItem(key="cash_transfer", label="تحويل نقدي", route="/accounting/cash/transfer", permissions=["accounting.add_cashtransfer"], icon="arrow-left-right"),
        ],
    ),
    
    # 📝 القيود المحاسبية
    NavSection(
        key="journal_entries",
        label="القيود المحاسبية",
        icon="journal-text",
        description="سجل القيود والقوالب",
        items=[
            NavItem(key="journal_entry_new", label="قيد جديد", route="/accounting/journal-entries/create/", permissions=["accounting.add_journalentry"], icon="plus-circle", shortcut="Ctrl+Shift+J"),
            NavItem(key="general_journal", label="سجل القيود", route="/accounting/journal-entries/", permissions=["accounting.view_journalentry"], icon="journal-bookmark"),
            NavItem(key="journal_drafts", label="قيود غير مرحّلة", route="/accounting/journal/drafts", permissions=["accounting.view_journalentry"], icon="exclamation-triangle", badge="draft_journal_count"),
            NavItem(key="journal_templates", label="قوالب القيود", route="/accounting/journal-templates/", permissions=["accounting.view_journalentry"], icon="file-earmark-template"),
            NavItem(key="smart_entry", label="قيد ذكي", route="/accounting/smart-entry/", permissions=["accounting.add_journalentry"], icon="lightning"),
        ],
    ),
    
    # 🏦 البنوك والشيكات
    NavSection(
        key="banking",
        label="البنوك والشيكات",
        icon="bank2",
        description="التسويات البنكية وحافظة الشيكات",
        items=[
            NavItem(key="bank_reconcile", label="تسوية بنكية", route="/accounting/bank/reconcile", permissions=["accounting.reconcile_bank"], icon="check2-circle"),
            NavItem(key="cheques", label="حافظة الشيكات", route="/accounting/cheques/", permissions=["accounting.view_account"], icon="file-earmark-check", badge="unreconciled_cheques_count"),
            NavItem(key="bank_import", label="استيراد كشف بنكي", route="/accounting/bank/import-statement", permissions=["accounting.reconcile_bank"], icon="upload"),
        ],
    ),
    
    # 💳 القروض والالتزامات المالية
    NavSection(
        key="loans_obligations",
        label="القروض",
        icon="credit-card",
        description="إدارة القروض والأقساط",
        items=[
            NavItem(key="loans_dashboard", label="لوحة القروض", route="/accounting/loans/", permissions=["accounting.view_account"], icon="speedometer", badge="active_loans_count"),
            NavItem(key="loan_list", label="سجل القروض", route="/accounting/loans/list/", permissions=["accounting.view_account"], icon="list-ul"),
            NavItem(key="loan_create", label="قرض جديد", route="/accounting/loans/create/", permissions=["accounting.add_account"], icon="plus-circle-fill"),
        ],
    ),
    
    # 📚 دليل الحسابات
    NavSection(
        key="chart_of_accounts",
        label="دليل الحسابات",
        icon="diagram-3",
        description="الحسابات والأرصدة",
        items=[
            NavItem(key="chart_of_accounts", label="دليل الحسابات", route="/accounting/accounts/", permissions=["accounting.view_account"], icon="tree"),
            NavItem(key="account_new", label="حساب جديد", route="/accounting/accounts/create/", permissions=["accounting.add_account"], icon="plus-square"),
            NavItem(key="account_statement", label="كشف حساب", route="/accounting/accounts/statement", permissions=["accounting.view_account"], icon="file-earmark-text"),
            NavItem(key="expense_accounts", label="حسابات المصروفات", route="/accounting/accounts/expenses/", permissions=["accounting.view_account"], icon="receipt"),
        ],
    ),
    
    # 🏢 الموردون والعملاء
    NavSection(
        key="suppliers_customers",
        label="الموردون والعملاء",
        icon="people",
        description="كشوف الحسابات والمدفوعات",
        items=[
            NavItem(key="customer_statement", label="كشف حساب عميل", route="/accounting/sales/statement/", permissions=["accounting.view_account"], icon="person-lines-fill"),
            NavItem(key="supplier_statement", label="كشف حساب مورد", route="/accounting/purchases/supplier-statement/1/", permissions=["accounting.view_account"], icon="file-person"),
            NavItem(key="pending_purchases", label="فواتير شراء معلقة", route="/accounting/pending-purchase-invoices/", permissions=["accounting.view_account"], icon="hourglass-split", badge="pending_purchases_count"),
            NavItem(key="sales_payments", label="مدفوعات العملاء", route="/accounting/sales/payments/", permissions=["accounting.view_account"], icon="cash-stack"),
        ],
    ),
    
    # 🏭 مراكز التكلفة والتكاليف
    NavSection(
        key="cost_management",
        label="التكاليف",
        icon="calculator",
        description="تكاليف المنتجات ومراكز التكلفة",
        items=[
            NavItem(key="cost_centers", label="مراكز التكلفة", route="/accounting/cost-centers/", permissions=["accounting.view_costcenter"], icon="building"),
            NavItem(key="product_costing", label="تكاليف المنتجات", route="/accounting/costing/", permissions=["accounting.view_account"], icon="boxes"),
            NavItem(key="costing_analysis", label="تحليل التكاليف", route="/accounting/costing/analysis/", permissions=["accounting.view_account"], icon="graph-up"),
            NavItem(key="cost_allocations", label="تخصيص التكاليف", route="/accounting/cost/allocations", permissions=["accounting.view_costcenter"], icon="distribute-vertical"),
        ],
    ),
    
    # 📈 القوائم المالية (الأساسية)
    NavSection(
        key="financial_statements",
        label="القوائم المالية",
        icon="file-earmark-bar-graph",
        description="القوائم المالية الرئيسية",
        items=[
            NavItem(key="trial_balance", label="ميزان المراجعة", route="/accounting/trial-balance/", permissions=["reports.view_trial_balance"], icon="balance-scale"),
            NavItem(key="income_statement", label="قائمة الدخل", route="/accounting/income-statement/", permissions=["reports.view_income_statement"], icon="graph-up-arrow"),
            NavItem(key="balance_sheet", label="الميزانية العمومية", route="/accounting/balance-sheet/", permissions=["reports.view_balance_sheet"], icon="clipboard-data"),
            NavItem(key="cash_flow", label="قائمة التدفقات النقدية", route="/accounting/cash-flow/", permissions=["reports.view_cash_flow"], icon="water"),
        ],
    ),
    
    # 📊 التقارير التفصيلية
    NavSection(
        key="detailed_reports",
        label="التقارير التفصيلية",
        icon="clipboard-check",
        description="تقارير محاسبية متقدمة",
        collapsed=True,  # مطوي افتراضياً لأنه أقل استخداماً
        items=[
            NavItem(key="general_ledger", label="دفتر الأستاذ العام", route="/accounting/ledger", permissions=["accounting.view_ledger"], icon="book"),
            NavItem(key="aging_receivables", label="أعمار الذمم المدينة", route="/accounting/reports/aging/receivables", permissions=["reports.view_aging"], icon="clock-history"),
            NavItem(key="aging_payables", label="أعمار الذمم الدائنة", route="/accounting/reports/aging/payables", permissions=["reports.view_aging"], icon="clock"),
            NavItem(key="budget_vs_actual", label="الموازنة vs الفعلي", route="/accounting/reports/budget-vs-actual/", permissions=["reports.view_aging"], icon="bar-chart"),
            NavItem(key="product_profitability", label="ربحية المنتجات", route="/accounting/reports/product-profitability/", permissions=["reports.view_aging"], icon="pie-chart-fill"),
            NavItem(key="customer_profitability", label="ربحية العملاء", route="/accounting/reports/customer-profitability/", permissions=["reports.view_aging"], icon="person-check"),
            NavItem(key="tax_report", label="التقارير الضريبية", route="/accounting/reports/tax", permissions=["reports.view_aging"], icon="file-earmark-ruled"),
        ],
    ),
    
    # 🔧 الإعدادات (الأقل استخداماً)
    NavSection(
        key="settings",
        label="الإعدادات",
        icon="gear",
        description="إعدادات النظام المحاسبي",
        collapsed=True,  # مطوي افتراضياً
        items=[
            NavItem(key="fiscal_year", label="السنة المالية", route="/accounting/settings/fiscal-year", permissions=["accounting.manage_fiscal"], icon="calendar-range"),
            NavItem(key="account_setup", label="تكوين الحسابات", route="/accounting/settings/", permissions=["accounting.manage_accounts"], icon="sliders"),
            NavItem(key="tax_settings", label="إعدادات الضرائب", route="/accounting/settings/tax", permissions=["accounting.manage_tax"], icon="percent"),
            NavItem(key="period_close", label="إقفالات الفترات", route="/accounting/period/close-year", permissions=["accounting.manage_fiscal"], icon="lock"),
            NavItem(key="recurring_entries", label="قيود متكررة", route="/accounting/journal/recurring", permissions=["accounting.add_journalentry"], icon="arrow-repeat"),
        ],
    ),
    
    # 🛠️ الأدوات
    NavSection(
        key="tools",
        label="الأدوات",
        icon="tools",
        description="أدوات التصدير والاستيراد",
        collapsed=True,  # مطوي افتراضياً
        items=[
            NavItem(key="export_tools", label="تصدير البيانات", route="/accounting/tools/export", permissions=["accounting.view_account"], icon="download"),
            NavItem(key="import_journal", label="استيراد قيود", route="/accounting/tools/import-journal", permissions=["accounting.add_journalentry"], icon="upload"),
            NavItem(key="diagnostics", label="التشخيص", route="/accounting/tools/diagnostics", permissions=["accounting.view_account"], icon="bug"),
        ],
    ),
]

# ---------------------------------------------------------------------------
# وظائف مساعدة
# ---------------------------------------------------------------------------

def _resolve_badge(value: str, request: HttpRequest) -> Optional[int | str]:
    """محاولة إيجاد قيمة الشارة.
    حالياً: تبحث في request.context أو خصائص مضافة (يمكن توسعتها لاحقاً).
    """
    # يمكن لاحقاً دعم Callable في settings أو إشارة Signal
    try:
        return getattr(request, value, None) or request.META.get(value.upper())
    except Exception:
        return None

# ---------------------------------------------------------------------------
# الواجهة الخارجية
# ---------------------------------------------------------------------------

def get_navigation(user: _HasPerms) -> List[NavSection]:
    """إرجاع قائمة الأقسام بعد تصفية الصلاحيات."""
    allowed_sections: List[NavSection] = []
    for section in BASE_NAVIGATION:
        items = section.visible_items(user)
        if items:
            allowed_sections.append(
                NavSection(
                    key=section.key,
                    label=section.label,
                    icon=section.icon,
                    items=items,
                    description=section.description,
                    collapsed=section.collapsed
                )
            )
    return allowed_sections

# Context Processor ----------------------------------------------------------

def navigation_context(request: HttpRequest) -> dict:
    if not request.user.is_authenticated:  # لا حاجة لإظهار شيء للزائر
        return {}
    nav = get_navigation(request.user)

    # حساب الشارات (Badges) للعناصر المهمة
    draft_journal_count = 0
    pending_purchases_count = 0
    active_loans_count = 0
    unreconciled_cheques_count = 0
    
    try:
        # قيود غير مرحلة
        draft_journal_count = JournalEntry.objects.filter(is_posted=False).count()
    except Exception:
        pass
    
    try:
        # فواتير شراء معلقة (من وحدة المشتريات إن وجدت)
        from purchases.models import PurchaseInvoice
        pending_purchases_count = PurchaseInvoice.objects.filter(
            status__in=['draft', 'pending']
        ).count()
    except (ImportError, Exception):
        pass
    
    try:
        # القروض النشطة
        from accounting.models import Loan
        active_loans_count = Loan.objects.filter(status='active').count()
    except Exception:
        pass
    
    try:
        # الشيكات غير المسوّاة
        from accounting.models import Cheque
        unreconciled_cheques_count = Cheque.objects.filter(
            status__in=['pending', 'under_collection']
        ).count()
    except Exception:
        pass

    return {
        "accounting_navigation": nav,
        "draft_journal_count": draft_journal_count,
        "pending_purchases_count": pending_purchases_count,
        "active_loans_count": active_loans_count,
        "unreconciled_cheques_count": unreconciled_cheques_count,
        # ملاحظة: يمكن إضافة المزيد من الشارات حسب الحاجة
    }

__all__ = [
    "NavItem",
    "NavSection",
    "get_navigation",
    "navigation_context",
]
