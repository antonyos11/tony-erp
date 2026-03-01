"""
واجهات التقارير — RITA ERP
Sprint 7 — 13 view + VAT report
"""
from datetime import date, timedelta
from decimal import Decimal

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from apps.reports.services.sales_reports import SalesReports
from apps.reports.services.inventory_reports import InventoryReports
from apps.reports.services.cost_reports import CostReports
from apps.reports.services.branch_reports import BranchReports
from apps.accounts.services.vat_engine import VATEngine


# ===== Helper Mixin =====

class ReportMixin(LoginRequiredMixin):
    """Mixin مشترك — يقرأ فلاتر التاريخ والفرع من GET"""

    def get_date_range(self):
        start = self.request.GET.get('start_date')
        end = self.request.GET.get('end_date')
        if start:
            start = date.fromisoformat(start)
        else:
            start = date.today().replace(day=1)
        if end:
            end = date.fromisoformat(end)
        else:
            end = date.today()
        return start, end

    def get_branch(self):
        branch_id = self.request.GET.get('branch')
        if branch_id:
            from apps.core.models import Branch
            try:
                return Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                pass
        return None

    def get_filter_context(self):
        start, end = self.get_date_range()
        from apps.core.models import Branch
        return {
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'branches': Branch.objects.filter(is_active=True),
            'selected_branch': self.request.GET.get('branch', ''),
        }


# ===== 1. ملخص المبيعات =====

class SalesSummaryView(ReportMixin, TemplateView):
    template_name = 'reports/sales_summary.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        branch = self.get_branch()
        salesperson_id = self.request.GET.get('salesperson')
        channel = self.request.GET.get('channel')

        salesperson = None
        if salesperson_id:
            from apps.core.models import User
            try:
                salesperson = User.objects.get(pk=salesperson_id)
            except Exception:
                pass

        ctx['report'] = SalesReports.sales_summary(start, end, branch, salesperson, channel)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'ملخص المبيعات'
        return ctx


# ===== 2. مبيعات حسب المنتج =====

class SalesByProductView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_product.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        branch = self.get_branch()
        ctx['products'] = SalesReports.sales_by_product(start, end, branch)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'مبيعات حسب المنتج'
        return ctx


# ===== 3. مبيعات حسب العميل =====

class SalesByCustomerView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_customer.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['customers'] = SalesReports.sales_by_customer(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'مبيعات حسب العميل'
        return ctx


# ===== 4. أداء البائعين =====

class SalesBySalespersonView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_salesperson.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['salespersons'] = SalesReports.sales_by_salesperson(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'أداء البائعين'
        return ctx


# ===== 5. ربحية المنتجات =====

class ProfitabilityView(ReportMixin, TemplateView):
    template_name = 'reports/profitability.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['products'] = SalesReports.profitability_report(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'ربحية المنتجات'
        return ctx


# ===== 6. حركة المخزون =====

class StockMovementView(ReportMixin, TemplateView):
    template_name = 'reports/stock_movement.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        warehouse = None
        wh_id = self.request.GET.get('warehouse')
        if wh_id:
            from apps.core.models import Warehouse
            try:
                warehouse = Warehouse.objects.get(pk=wh_id)
            except Warehouse.DoesNotExist:
                pass
        ctx['report'] = InventoryReports.stock_movement_report(start, end, warehouse)
        ctx.update(self.get_filter_context())
        from apps.core.models import Warehouse
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        ctx['selected_warehouse'] = self.request.GET.get('warehouse', '')
        ctx['title'] = 'حركة المخزون'
        return ctx


# ===== 7. المخزون الراكد =====

class DeadStockView(ReportMixin, TemplateView):
    template_name = 'reports/dead_stock.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        days = int(self.request.GET.get('days', 90))
        ctx['items'] = InventoryReports.dead_stock_report(days)
        ctx['days'] = days
        ctx['total_value'] = sum(i['value'] for i in ctx['items'])
        ctx['title'] = 'المخزون الراكد'
        return ctx


# ===== 8. تقرير إعادة الطلب =====

class ReorderView(ReportMixin, TemplateView):
    template_name = 'reports/reorder.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = InventoryReports.reorder_report()
        ctx['total_cost'] = sum(i['estimated_cost'] for i in ctx['items'])
        ctx['title'] = 'تقرير إعادة الطلب'
        return ctx


# ===== 9. تكلفة المنتج الفعلية =====

class ProductCostView(ReportMixin, TemplateView):
    template_name = 'reports/product_cost.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['products'] = CostReports.product_cost_report()
        ctx['title'] = 'تكلفة المنتج الفعلية'
        return ctx


# ===== 10. انحراف التكاليف =====

class CostVarianceView(ReportMixin, TemplateView):
    template_name = 'reports/cost_variance.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['orders'] = CostReports.cost_variance_report(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'انحراف التكاليف'
        return ctx


# ===== 11. تقييم الفروع =====

class BranchScorecardView(ReportMixin, TemplateView):
    template_name = 'reports/branch_scorecard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['branches'] = BranchReports.branch_scorecard(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'تقييم الفروع'
        return ctx


# ===== 12. أعمار الديون =====

class AgingView(ReportMixin, TemplateView):
    template_name = 'reports/aging.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        partner_type = self.request.GET.get('partner_type', 'customer')
        ctx['report'] = BranchReports.aging_report(partner_type)
        ctx['partner_type'] = partner_type
        ctx['title'] = 'أعمار الديون'
        return ctx


# ===== 13. الإقرار الضريبي =====

class VATReportView(ReportMixin, TemplateView):
    template_name = 'reports/vat_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['report'] = VATEngine.get_vat_summary(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'الإقرار الضريبي'
        return ctx
