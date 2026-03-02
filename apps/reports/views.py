"""
واجهات التقارير — RITA ERP
Sprint 7+16 — 13 view + VAT report + تصدير Excel/PDF
"""
from datetime import date, timedelta
import json
from decimal import Decimal

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from apps.reports.services.sales_reports import SalesReports
from apps.reports.services.inventory_reports import InventoryReports
from apps.reports.services.cost_reports import CostReports
from apps.reports.services.branch_reports import BranchReports
from apps.reports.services.export_engine import ExcelExporter, PDFExporter
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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            branch = self.get_branch()
            report = SalesReports.sales_summary(start, end, branch)
            headers = ['البند', 'القيمة (ج.م)']
            data = [
                ['إجمالي المبيعات', float(report['total_sales'])],
                ['الخصومات', float(report['discount'])],
                ['الضريبة', float(report['tax'])],
                ['المحصّل', float(report['total_paid'])],
                ['المتبقي', float(report['total_remaining'])],
                ['التكلفة', float(report['total_cost'])],
                ['الربح الإجمالي', float(report['gross_profit'])],
                ['هامش الربح %', float(report['profit_margin'])],
                ['عدد الفواتير', report['invoice_count']],
            ]
            if export == 'excel':
                return ExcelExporter.export('ملخص المبيعات', headers, data, f'sales_summary_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/sales_summary_pdf.html',
                    {'report': report, 'start_date': start, 'end_date': end, 'branch': branch},
                    f'sales_summary_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

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
        trend = SalesReports.daily_sales_trend(30)
        ctx['chart_labels'] = json.dumps([d['label'] for d in trend])
        ctx['chart_sales'] = json.dumps([float(d['total_sales'] or 0) for d in trend])
        top_prods = SalesReports.top_products(30, 10, branch)
        ctx['top_products'] = top_prods
        ctx['top_products_labels'] = json.dumps([p['product__name'] for p in top_prods])
        ctx['top_products_revenue'] = json.dumps([float(p['total_revenue'] or 0) for p in top_prods])
        ctx['top_products_profit'] = json.dumps([float(p['total_profit']  or 0) for p in top_prods])
        return ctx


# ===== 2. مبيعات حسب المنتج =====

class SalesByProductView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_product.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            branch = self.get_branch()
            products = SalesReports.sales_by_product(start, end, branch)
            headers = ['الكود', 'المنتج', 'الكمية', 'الإيراد', 'التكلفة', 'الربح', 'الهامش %']
            data = [
                [
                    p['product__code'], p['product__name'],
                    float(p['total_qty'] or 0), float(p['total_revenue'] or 0),
                    float(p['total_cost'] or 0), float(p['total_profit'] or 0),
                    float(p['profit_margin'] or 0),
                ]
                for p in products
            ]
            if export == 'excel':
                return ExcelExporter.export('مبيعات حسب المنتج', headers, data, f'sales_by_product_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'مبيعات حسب المنتج', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'sales_by_product_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        branch = self.get_branch()
        products = SalesReports.sales_by_product(start, end, branch)
        ctx['products'] = products
        ctx.update(self.get_filter_context())
        ctx['title'] = 'مبيعات حسب المنتج'
        top10 = products[:10]
        ctx['chart_labels'] = json.dumps([p['product__name'] for p in top10])
        ctx['chart_revenue'] = json.dumps([float(p['total_revenue'] or 0) for p in top10])
        ctx['chart_profit'] = json.dumps([float(p['total_profit'] or 0) for p in top10])
        return ctx


# ===== 3. مبيعات حسب العميل =====

class SalesByCustomerView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_customer.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            customers = SalesReports.sales_by_customer(start, end)
            headers = ['الكود', 'العميل', 'عدد الفواتير', 'إجمالي المبيعات', 'المحصّل', 'المتبقي']
            data = [
                [
                    c['customer__code'], c['customer__name'],
                    c['invoice_count'],
                    float(c['total_sales'] or 0), float(c['total_paid'] or 0), float(c['total_remaining'] or 0),
                ]
                for c in customers
            ]
            if export == 'excel':
                return ExcelExporter.export('مبيعات حسب العميل', headers, data, f'sales_by_customer_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'مبيعات حسب العميل', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'sales_by_customer_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        customers = SalesReports.sales_by_customer(start, end)
        ctx['customers'] = customers
        ctx.update(self.get_filter_context())
        ctx['title'] = 'مبيعات حسب العميل'
        top5 = customers[:5]
        ctx['chart_labels'] = json.dumps([c['customer__name'] for c in top5])
        ctx['chart_sales'] = json.dumps([float(c['total_sales'] or 0) for c in top5])
        return ctx


# ===== 4. أداء البائعين =====

class SalesBySalespersonView(ReportMixin, TemplateView):
    template_name = 'reports/sales_by_salesperson.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            salespersons = SalesReports.sales_by_salesperson(start, end)
            headers = ['البائع', 'عدد الفواتير', 'إجمالي المبيعات', 'الخصومات', 'الربح']
            data = [
                [sp['salesperson'], sp['invoice_count'],
                 float(sp['total_sales'] or 0), float(sp['total_discount'] or 0), float(sp['total_profit'] or 0)]
                for sp in salespersons
            ]
            if export == 'excel':
                return ExcelExporter.export('أداء البائعين', headers, data, f'salespersons_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'أداء البائعين', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'salespersons_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        salespersons = SalesReports.sales_by_salesperson(start, end)
        ctx['salespersons'] = salespersons
        ctx.update(self.get_filter_context())
        ctx['title'] = 'أداء البائعين'
        ctx['chart_labels'] = json.dumps([sp['salesperson'] for sp in salespersons])
        ctx['chart_sales'] = json.dumps([float(sp['total_sales'] or 0) for sp in salespersons])
        return ctx


# ===== 5. ربحية المنتجات =====

class ProfitabilityView(ReportMixin, TemplateView):
    template_name = 'reports/profitability.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            products = SalesReports.profitability_report(start, end)
            headers = ['المنتج', 'الكمية', 'الإيراد', 'التكلفة', 'الربح', 'الهامش %', 'الحالة']
            data = [
                [p['product__name'], float(p['total_qty'] or 0), float(p['total_revenue'] or 0),
                 float(p['total_cost'] or 0), float(p['total_profit'] or 0),
                 float(p['profit_margin'] or 0), p['status']]
                for p in products
            ]
            if export == 'excel':
                return ExcelExporter.export('ربحية المنتجات', headers, data, f'profitability_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'ربحية المنتجات', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'profitability_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            warehouse = None
            wh_id = request.GET.get('warehouse')
            if wh_id:
                from apps.core.models import Warehouse
                try:
                    warehouse = Warehouse.objects.get(pk=wh_id)
                except Warehouse.DoesNotExist:
                    pass
            report = InventoryReports.stock_movement_report(start, end, warehouse)
            headers = ['المنتج', 'رصيد أول الفترة', 'وارد', 'صادر', 'رصيد آخر الفترة']
            data = [
                [item.get('product_name', item.get('product__name', '')), float(item.get('opening', 0) or 0), float(item.get('in', 0) or 0),
                 float(item.get('out', 0) or 0), float(item.get('closing', 0) or 0)]
                for item in report
            ]
            if export == 'excel':
                return ExcelExporter.export('حركة المخزون', headers, data, f'stock_movement_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'حركة المخزون', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'stock_movement_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            days = int(request.GET.get('days', 90))
            items = InventoryReports.dead_stock_report(days)
            headers = ['المنتج', 'الكمية', 'التكلفة', 'القيمة الإجمالية', 'آخر حركة']
            data = [
                [i.get('product_name', ''), float(i.get('qty', 0) or 0), float(i.get('cost', 0) or 0),
                 float(i['value'] or 0), str(i.get('last_move', ''))]
                for i in items
            ]
            if export == 'excel':
                return ExcelExporter.export(f'المخزون الراكد ({days} يوم)', headers, data, f'dead_stock_{days}d.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': f'المخزون الراكد ({days} يوم)', 'headers': headers, 'data': data},
                    f'dead_stock_{days}d.pdf',
                )
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            items = InventoryReports.reorder_report()
            headers = ['المنتج', 'الرصيد الحالي', 'حد إعادة الطلب', 'النقص', 'التكلفة التقديرية']
            data = [
                [i.get('product_name', ''), float(i.get('current_stock', 0) or 0), float(i.get('reorder_level', 0) or 0),
                 float(i.get('deficit', 0) or 0), float(i.get('estimated_cost', 0) or 0)]
                for i in items
            ]
            if export == 'excel':
                return ExcelExporter.export('تقرير إعادة الطلب', headers, data, 'reorder_report.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'تقرير إعادة الطلب', 'headers': headers, 'data': data},
                    'reorder_report.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = InventoryReports.reorder_report()
        ctx['total_cost'] = sum(i['estimated_cost'] for i in ctx['items'])
        ctx['title'] = 'تقرير إعادة الطلب'
        return ctx


# ===== 9. تكلفة المنتج الفعلية =====

class ProductCostView(ReportMixin, TemplateView):
    template_name = 'reports/product_cost.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            products = CostReports.product_cost_report()
            headers = ['الكود', 'المنتج', 'تكلفة المواد', 'تكلفة العمالة', 'تكاليف إضافية', 'التكلفة الكلية', 'سعر البيع', 'الهامش %']
            data = [
                [p.get('code', ''), p.get('name', ''), float(p.get('material_cost', 0) or 0),
                 float(p.get('labor_cost', 0) or 0), float(p.get('overhead_cost', 0) or 0),
                 float(p.get('total_cost', 0) or 0), float(p.get('selling_price', 0) or 0),
                 float(p.get('margin', 0) or 0)]
                for p in products
            ]
            if export == 'excel':
                return ExcelExporter.export('تكلفة المنتجات', headers, data, 'product_cost.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'تكلفة المنتجات', 'headers': headers, 'data': data},
                    'product_cost.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['products'] = CostReports.product_cost_report()
        ctx['title'] = 'تكلفة المنتج الفعلية'
        return ctx


# ===== 10. انحراف التكاليف =====

class CostVarianceView(ReportMixin, TemplateView):
    template_name = 'reports/cost_variance.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            orders = CostReports.cost_variance_report(start, end)
            headers = ['أمر الإنتاج', 'تكلفة مخططة', 'تكلفة فعلية', 'الانحراف', 'الانحراف %']
            data = [
                [o.get('order_number', ''), float(o.get('planned_cost', 0) or 0),
                 float(o.get('actual_cost', 0) or 0), float(o.get('variance', 0) or 0),
                 float(o.get('variance_pct', 0) or 0)]
                for o in orders
            ]
            if export == 'excel':
                return ExcelExporter.export('انحراف التكاليف', headers, data, f'cost_variance_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'انحراف التكاليف', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'cost_variance_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            branches = BranchReports.branch_scorecard(start, end)
            headers = ['الفرع', 'المبيعات', 'التحصيل', 'الربح', 'الهامش %', 'عدد الفواتير']
            data = [
                [b.get('name', ''), float(b.get('total_sales', 0) or 0), float(b.get('total_paid', 0) or 0),
                 float(b.get('gross_profit', 0) or 0), float(b.get('profit_margin', 0) or 0),
                 b.get('invoice_count', 0)]
                for b in branches
            ]
            if export == 'excel':
                return ExcelExporter.export('تقييم الفروع', headers, data, f'branches_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'تقييم الفروع', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'branches_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        branches = BranchReports.branch_scorecard(start, end)
        ctx['branches'] = branches
        ctx.update(self.get_filter_context())
        ctx['title'] = 'تقييم الفروع'
        ctx['chart_labels'] = json.dumps([b.get('name', '') for b in branches])
        ctx['chart_sales'] = json.dumps([float(b.get('total_sales', 0) or 0) for b in branches])
        ctx['chart_profit'] = json.dumps([float(b.get('gross_profit', 0) or 0) for b in branches])
        return ctx


# ===== 12. أعمار الديون =====

class AgingView(ReportMixin, TemplateView):
    template_name = 'reports/aging.html'

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            partner_type = request.GET.get('partner_type', 'customer')
            report = BranchReports.aging_report(partner_type)
            headers = ['الاسم', '0-30 يوم', '31-60 يوم', '61-90 يوم', '+90 يوم', 'الإجمالي']
            data = [
                [r.get('name', ''), float(r.get('bucket_0_30', 0) or 0), float(r.get('bucket_31_60', 0) or 0),
                 float(r.get('bucket_61_90', 0) or 0), float(r.get('bucket_90_plus', 0) or 0),
                 float(r.get('total', 0) or 0)]
                for r in report
            ]
            if export == 'excel':
                return ExcelExporter.export(f'أعمار الديون', headers, data, f'aging_{partner_type}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'أعمار الديون', 'headers': headers, 'data': data},
                    f'aging_{partner_type}.pdf',
                )
        return super().get(request, *args, **kwargs)

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

    def get(self, request, *args, **kwargs):
        export = request.GET.get('export')
        if export:
            start, end = self.get_date_range()
            report = VATEngine.get_vat_summary(start, end)
            headers = ['البند', 'القيمة (ج.م)']
            data = [
                ['الضريبة على المبيعات', float(report.get('output_vat', 0) or 0)],
                ['الضريبة على المشتريات', float(report.get('input_vat', 0) or 0)],
                ['صافي ضريبة مستحقة', float(report.get('net_vat', 0) or 0)],
            ]
            if export == 'excel':
                return ExcelExporter.export('الإقرار الضريبي', headers, data, f'vat_report_{start}_{end}.xlsx')
            elif export == 'pdf':
                return PDFExporter.export(
                    'reports/pdf/generic_table_pdf.html',
                    {'title': 'الإقرار الضريبي', 'headers': headers, 'data': data, 'start_date': start, 'end_date': end},
                    f'vat_report_{start}_{end}.pdf',
                )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        ctx['report'] = VATEngine.get_vat_summary(start, end)
        ctx.update(self.get_filter_context())
        ctx['title'] = 'الإقرار الضريبي'
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 20 — تقارير إضافية
# ══════════════════════════════════════════════════════

class DailySalesView(ReportMixin, TemplateView):
    """تقرير المبيعات اليومية"""
    template_name = 'reports/daily_sales.html'
    title = 'المبيعات اليومية'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.sales.models import SalesInvoice
        from django.db.models import Sum, Count

        date_str = self.request.GET.get('date', str(date.today()))
        try:
            from datetime import datetime
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            selected_date = date.today()

        invoices = SalesInvoice.objects.filter(
            date__date=selected_date,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
        ).select_related('customer', 'branch')

        ctx['selected_date'] = selected_date
        ctx['invoices'] = invoices
        ctx['totals'] = invoices.aggregate(
            total=Sum('total'),
            count=Count('id'),
        )
        return ctx


class CustomerBalanceView(ReportMixin, TemplateView):
    """تقرير أرصدة العملاء"""
    template_name = 'reports/customer_balance.html'
    title = 'أرصدة العملاء'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.sales.models import Customer, SalesInvoice
        from django.db.models import Sum

        customers_data = []
        for customer in Customer.objects.filter(is_active=True):
            total_invoiced = SalesInvoice.objects.filter(
                customer=customer,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            ).aggregate(t=Sum('total'))['t'] or Decimal('0')
            outstanding = SalesInvoice.objects.filter(
                customer=customer,
                status__in=['confirmed', 'partial_paid'],
            ).aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
            if outstanding > 0:
                customers_data.append({
                    'customer': customer,
                    'total_invoiced': total_invoiced,
                    'outstanding': outstanding,
                })

        ctx['customers'] = sorted(customers_data, key=lambda x: x['outstanding'], reverse=True)
        ctx['total_outstanding'] = sum(c['outstanding'] for c in customers_data)
        return ctx


class SupplierBalanceView(ReportMixin, TemplateView):
    """تقرير أرصدة الموردين"""
    template_name = 'reports/supplier_balance.html'
    title = 'أرصدة الموردين'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from apps.partners.models import Supplier
            from apps.purchases.models import PurchaseOrder
            from django.db.models import Sum

            suppliers_data = []
            for supplier in Supplier.objects.filter(is_active=True):
                orders = PurchaseOrder.objects.filter(
                    supplier=supplier,
                    status__in=['confirmed', 'partial', 'received'],
                )
                total = orders.aggregate(t=Sum('total'))['t'] or Decimal('0')
                paid = orders.aggregate(t=Sum('paid_amount'))['t'] or Decimal('0')
                outstanding = total - paid
                if outstanding > 0:
                    suppliers_data.append({
                        'supplier': supplier,
                        'total': total,
                        'paid': paid,
                        'outstanding': outstanding,
                    })

            ctx['suppliers'] = sorted(suppliers_data, key=lambda x: x['outstanding'], reverse=True)
            ctx['total_outstanding'] = sum(s['outstanding'] for s in suppliers_data)
        except Exception:
            ctx['suppliers'] = []
            ctx['total_outstanding'] = Decimal('0')
        return ctx


class CashFlowView(ReportMixin, TemplateView):
    """تقرير التدفق النقدي"""
    template_name = 'reports/cash_flow.html'
    title = 'التدفق النقدي'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.sales.models import SalesInvoice
        from apps.expenses.models import Expense
        from django.db.models import Sum
        from datetime import datetime

        month_start = date.today().replace(day=1)

        inflows = SalesInvoice.objects.filter(
            date__gte=month_start,
            status__in=['paid', 'partial_paid'],
        ).aggregate(t=Sum('paid_amount'))['t'] or Decimal('0')

        outflows = Decimal('0')
        try:
            outflows = Expense.objects.filter(
                date__gte=month_start,
                status='paid',
            ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        except Exception:
            pass

        ctx['inflows'] = inflows
        ctx['outflows'] = outflows
        ctx['net_flow'] = inflows - outflows
        ctx['month_start'] = month_start
        return ctx


class ExpenseSummaryView(ReportMixin, TemplateView):
    """ملخص المصروفات"""
    template_name = 'reports/expense_summary.html'
    title = 'ملخص المصروفات'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from apps.expenses.models import Expense, ExpenseCategory
            from django.db.models import Sum, Count

            month_start = date.today().replace(day=1)
            expenses = Expense.objects.filter(date__gte=month_start)

            ctx['total_expenses'] = expenses.aggregate(t=Sum('amount'))['t'] or Decimal('0')
            ctx['by_category'] = expenses.values(
                'category__name'
            ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
            ctx['expenses'] = expenses.select_related('category').order_by('-date')[:50]
        except Exception as e:
            ctx['total_expenses'] = Decimal('0')
            ctx['by_category'] = []
            ctx['expenses'] = []
        return ctx


class ProductionSummaryView(ReportMixin, TemplateView):
    """ملخص الإنتاج"""
    template_name = 'reports/production_summary.html'
    title = 'ملخص الإنتاج'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.production.models import ProductionOrder
        from django.db.models import Sum, Count

        month_start = date.today().replace(day=1)
        orders = ProductionOrder.objects.filter(created_at__date__gte=month_start)

        ctx['total_orders'] = orders.count()
        ctx['completed'] = orders.filter(status='completed').count()
        ctx['in_progress'] = orders.filter(status='in_progress').count()
        ctx['cancelled'] = orders.filter(status='cancelled').count()
        ctx['total_quantity'] = orders.filter(status='completed').aggregate(
            t=Sum('quantity_produced')
        )['t'] or Decimal('0')
        ctx['orders'] = orders.select_related('product', 'production_line').order_by('-created_at')[:20]
        return ctx


class HRSummaryView(ReportMixin, TemplateView):
    """ملخص الموارد البشرية"""
    template_name = 'reports/hr_summary.html'
    title = 'ملخص الموارد البشرية'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from apps.hr.models import Employee, Attendance, LeaveRequest
            from django.db.models import Sum, Count

            today = date.today()
            month_start = today.replace(day=1)

            ctx['total_employees'] = Employee.objects.filter(status='active').count()
            ctx['present_today'] = Attendance.objects.filter(
                date=today, status='present'
            ).count()
            ctx['absent_today'] = Attendance.objects.filter(
                date=today, status='absent'
            ).count()
            ctx['pending_leaves'] = LeaveRequest.objects.filter(
                status='pending'
            ).count()
        except Exception:
            ctx['total_employees'] = 0
            ctx['present_today'] = 0
            ctx['absent_today'] = 0
            ctx['pending_leaves'] = 0
        return ctx


class AttendanceReportView(ReportMixin, TemplateView):
    """تقرير الحضور الشهري"""
    template_name = 'reports/attendance_report.html'
    title = 'تقرير الحضور'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from apps.hr.models import Employee, Attendance
            import calendar

            # الشهر المحدد
            year = int(self.request.GET.get('year', date.today().year))
            month = int(self.request.GET.get('month', date.today().month))

            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            days_range = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

            employees = Employee.objects.filter(status='active').select_related('department')
            attendance_data = []

            for emp in employees:
                attendances = {
                    a.date: a.status
                    for a in Attendance.objects.filter(
                        employee=emp,
                        date__range=(first_day, last_day),
                    )
                }
                row = {
                    'employee': emp,
                    'days': [],
                    'present': 0, 'absent': 0, 'leave': 0,
                }
                for d in days_range:
                    status = attendances.get(d, '')
                    row['days'].append({'date': d, 'status': status})
                    if status == 'present':
                        row['present'] += 1
                    elif status == 'absent':
                        row['absent'] += 1
                    elif status in ('leave', 'official_leave'):
                        row['leave'] += 1
                attendance_data.append(row)

            ctx['attendance_data'] = attendance_data
            ctx['days_range'] = days_range
            ctx['year'] = year
            ctx['month'] = month
            ctx['month_name'] = first_day.strftime('%B %Y')
        except Exception as e:
            ctx['error'] = str(e)
        return ctx


# ══════════════════════════════════════════════════════════════════════
# Sprint 22B — تقارير متقدمة: أعمار الديون + الربحية متعددة الأبعاد
# ══════════════════════════════════════════════════════════════════════

from apps.reports.services.advanced_reports import AgingReport, ProfitabilityReport


class CustomerAgingView(ReportMixin, TemplateView):
    """تقرير أعمار ديون العملاء"""
    template_name = 'reports/customer_aging.html'
    title = 'أعمار ديون العملاء'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        as_of_date_str = self.request.GET.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            from datetime import date as _date
            try:
                as_of_date = _date.fromisoformat(as_of_date_str)
            except ValueError:
                pass
        report = AgingReport.customer_aging(as_of_date=as_of_date)
        ctx.update(report)
        ctx['title'] = self.title
        return ctx


class SupplierAgingView(ReportMixin, TemplateView):
    """تقرير أعمار ديون الموردين"""
    template_name = 'reports/supplier_aging.html'
    title = 'أعمار ديون الموردين'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        as_of_date_str = self.request.GET.get('as_of_date')
        as_of_date = None
        if as_of_date_str:
            from datetime import date as _date
            try:
                as_of_date = _date.fromisoformat(as_of_date_str)
            except ValueError:
                pass
        report = AgingReport.supplier_aging(as_of_date=as_of_date)
        ctx.update(report)
        ctx['title'] = self.title
        return ctx


class ProfitByProductView(ReportMixin, TemplateView):
    """ربحية حسب المنتج"""
    template_name = 'reports/profitability_by_dimension.html'
    title = 'الربحية حسب المنتج'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        report = ProfitabilityReport.by_product(start, end)
        ctx.update(report)
        ctx['title'] = self.title
        ctx.update(self.get_filter_context())
        return ctx


class ProfitByBranchView(ReportMixin, TemplateView):
    """ربحية حسب الفرع"""
    template_name = 'reports/profitability_by_dimension.html'
    title = 'الربحية حسب الفرع'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        report = ProfitabilityReport.by_branch(start, end)
        ctx.update(report)
        ctx['title'] = self.title
        ctx.update(self.get_filter_context())
        return ctx


class ProfitByCustomerView(ReportMixin, TemplateView):
    """ربحية حسب العميل"""
    template_name = 'reports/profitability_by_dimension.html'
    title = 'الربحية حسب العميل'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        report = ProfitabilityReport.by_customer(start, end)
        ctx.update(report)
        ctx['title'] = self.title
        ctx.update(self.get_filter_context())
        return ctx


class ProfitByChannelView(ReportMixin, TemplateView):
    """ربحية حسب قناة البيع"""
    template_name = 'reports/profitability_by_dimension.html'
    title = 'الربحية حسب قناة البيع'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_date_range()
        report = ProfitabilityReport.by_sales_channel(start, end)
        ctx.update(report)
        ctx['title'] = self.title
        ctx.update(self.get_filter_context())
        return ctx
