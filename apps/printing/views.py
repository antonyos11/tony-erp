"""
واجهات تطبيق الطباعة والباركود — RITA ERP
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, View, ListView

from apps.printing.models import PrintTemplate
from apps.printing.services.barcode_engine import (
    generate_barcode_html,
    generate_code128,
    generate_qr,
)
from apps.printing.services.invoice_printer import (
    render_invoice_html,
    render_receipt_html,
)


# ══════════════════════════════════════════════════════
# طباعة الفواتير
# ══════════════════════════════════════════════════════

class PrintInvoiceView(LoginRequiredMixin, View):
    """عرض طباعة فاتورة بيع — HTML أو نص للمتصفح."""

    def get(self, request, pk):
        from apps.sales.models import SalesInvoice
        invoice    = get_object_or_404(SalesInvoice, pk=pk)
        paper_size = request.GET.get('paper', 'a4')
        html       = render_invoice_html(invoice, paper_size=paper_size)
        return HttpResponse(html)


class PrintReceiptView(LoginRequiredMixin, View):
    """عرض طباعة إيصال قبض."""

    def get(self, request, pk):
        from apps.sales.models import SalesInvoice
        invoice    = get_object_or_404(SalesInvoice, pk=pk)
        paper_size = request.GET.get('paper', 'thermal_80')
        html       = render_receipt_html(invoice, paper_size=paper_size)
        return HttpResponse(html)


# ══════════════════════════════════════════════════════
# الباركود
# ══════════════════════════════════════════════════════

class GenerateBarcodeView(LoginRequiredMixin, View):
    """توليد باركود لمنتج واحد وإرجاعه كـ HTML أو JSON."""

    def get(self, request, product_pk=None):
        from apps.inventory.models import Product
        from datetime import date

        if product_pk:
            product         = get_object_or_404(Product, pk=product_pk)
            product_code    = product.code
            product_name    = product.name
        else:
            product_code = request.GET.get('code', 'PROD-001')
            product_name = request.GET.get('name', '')

        barcode_type = request.GET.get('type', 'code128')   # 'code128' أو 'qr'
        prod_order   = request.GET.get('order', '')

        html = generate_barcode_html(
            product_code    = product_code,
            product_name    = product_name,
            production_order= prod_order,
            barcode_type    = barcode_type,
        )

        if request.GET.get('format') == 'json':
            if barcode_type == 'qr':
                img_b64 = generate_qr(product_code, production_order=prod_order)
            else:
                img_b64 = generate_code128(product_code, production_order=prod_order)
            return JsonResponse({'barcode': img_b64, 'html': html})

        return HttpResponse(html)


class PrintBarcodeSheetView(LoginRequiredMixin, TemplateView):
    """طباعة صفحة تحتوي على مجموعة باركودات لمنتجات متعددة."""
    template_name = 'printing/barcode_sheet.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.inventory.models import Product
        from datetime import date

        # قبول قائمة PKs من الـ query string: ?products=1,2,3
        pks_param    = self.request.GET.get('products', '')
        barcode_type = self.request.GET.get('type', 'code128')
        prod_order   = self.request.GET.get('order', '')

        barcodes = []
        if pks_param:
            pks = [p.strip() for p in pks_param.split(',') if p.strip()]
            products = Product.objects.filter(pk__in=pks, is_active=True)
            for product in products:
                html = generate_barcode_html(
                    product_code    = product.code,
                    product_name    = product.name,
                    production_order= prod_order,
                    barcode_type    = barcode_type,
                )
                barcodes.append({'product': product, 'html': html})

        ctx['barcodes']     = barcodes
        ctx['barcode_type'] = barcode_type
        return ctx


# ══════════════════════════════════════════════════════
# قوالب الطباعة
# ══════════════════════════════════════════════════════

class PrintTemplateListView(LoginRequiredMixin, ListView):
    model               = PrintTemplate
    template_name       = 'printing/template_list.html'
    context_object_name = 'templates'
    paginate_by         = 20

    def get_queryset(self):
        qs = PrintTemplate.objects.filter(is_deleted=False)
        t  = self.request.GET.get('type')
        if t:
            qs = qs.filter(template_type=t)
        return qs

    def get_context_data(self, **kwargs):
        ctx                 = super().get_context_data(**kwargs)
        ctx['template_types'] = PrintTemplate.TEMPLATE_TYPES
        return ctx


# ══════════════════════════════════════════════════════
# طباعة ملصقات المنتجات (Labels)
# ══════════════════════════════════════════════════════

class PrintProductLabelsView(LoginRequiredMixin, TemplateView):
    """طباعة ملصقات أسعار/باركود لمجموعة منتجات"""
    template_name = 'printing/product_labels.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.inventory.models import Product

        pks_param    = self.request.GET.get('products', '')
        copies       = int(self.request.GET.get('copies', 1))
        barcode_type = self.request.GET.get('type', 'code128')
        show_price   = self.request.GET.get('show_price', '1') == '1'

        labels = []
        if pks_param:
            pks = [p.strip() for p in pks_param.split(',') if p.strip().isdigit()]
            products = Product.objects.filter(pk__in=pks, is_active=True)
            for product in products:
                barcode_html = generate_barcode_html(
                    product_code=product.code,
                    product_name=product.name,
                    barcode_type=barcode_type,
                )
                for _ in range(copies):
                    labels.append({
                        'product': product,
                        'barcode_html': barcode_html,
                        'show_price': show_price,
                    })

        ctx['labels'] = labels
        ctx['barcode_type'] = barcode_type
        ctx['copies'] = copies
        return ctx


class PrintProductLabelsSelectorView(LoginRequiredMixin, View):
    """صفحة اختيار منتجات لطباعة ملصقاتها"""
    template_name = 'printing/label_selector.html'

    def get(self, request):
        from apps.inventory.models import Product, Category
        products = Product.objects.filter(
            is_active=True, is_deleted=False
        ).select_related('category').order_by('code')
        categories = Category.objects.filter(is_deleted=False)
        return render(request, self.template_name, {
            'products': products,
            'categories': categories,
        })

    def post(self, request):
        from django.shortcuts import render as _render
        pks = request.POST.getlist('products')
        copies = request.POST.get('copies', '1')
        barcode_type = request.POST.get('type', 'code128')
        show_price = request.POST.get('show_price', '1')
        if not pks:
            from django.contrib import messages as msg
            msg.error(request, 'اختر منتجاً واحداً على الأقل')
            return redirect('printing:label_selector')
        pks_str = ','.join(pks)
        return redirect(
            f'/printing/labels/?products={pks_str}&copies={copies}&type={barcode_type}&show_price={show_price}'
        )
