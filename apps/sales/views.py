"""
واجهات تطبيق المبيعات — RITA ERP
"""
from decimal import Decimal

from django import forms
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, View,
)

from apps.core.models import Branch, Warehouse
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesReturn, PriceList
from apps.inventory.models import Product
from apps.sales.services.sales_engine import SalesEngine
from apps.authorization.decorators import PermissionRequiredMixin
from apps.core.mixins import apply_branch_filter, BranchCreateMixin


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'code', 'name', 'customer_type', 'phone', 'phone2',
            'address', 'governorate', 'tax_number', 'credit_limit',
            'price_list', 'branch', 'account', 'is_active',
        ]
        widgets = {
            'code':         forms.TextInput(attrs={'class': 'form-control'}),
            'name':         forms.TextInput(attrs={'class': 'form-control'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'phone':        forms.TextInput(attrs={'class': 'form-control'}),
            'phone2':       forms.TextInput(attrs={'class': 'form-control'}),
            'address':      forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'governorate':  forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number':   forms.TextInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_list':   forms.Select(attrs={'class': 'form-select'}),
            'branch':       forms.Select(attrs={'class': 'form-select'}),
            'account':      forms.Select(attrs={'class': 'form-select'}),
            'is_active':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SalesInvoiceForm(forms.Form):
    """فورم إنشاء فاتورة بيع"""
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True).order_by('name'),
        label='العميل', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='المخزن', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payment_method = forms.ChoiceField(
        choices=SalesInvoice.PAYMENT_METHOD_CHOICES,
        label='طريقة الدفع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    sale_channel = forms.ChoiceField(
        choices=SalesInvoice.SALE_CHANNEL_CHOICES,
        label='قناة البيع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discount_percentage = forms.DecimalField(
        min_value=0, max_value=100, initial=0, required=False,
        label='خصم إجمالي %',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    is_taxable = forms.BooleanField(
        required=False, initial=True,
        label='خاضعة للضريبة',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    delivery_required = forms.BooleanField(
        required=False,
        label='يستلزم توصيل',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    delivery_address = forms.CharField(
        required=False, label='عنوان التوصيل',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    delivery_fee = forms.DecimalField(
        min_value=0, initial=0, required=False,
        label='رسوم التوصيل',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    notes = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class RecordPaymentForm(forms.Form):
    amount = forms.DecimalField(
        min_value=Decimal('0.01'),
        label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    payment_method = forms.ChoiceField(
        choices=SalesInvoice.PAYMENT_METHOD_CHOICES,
        label='طريقة الدفع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class SalesReturnForm(forms.Form):
    original_invoice = forms.ModelChoiceField(
        queryset=SalesInvoice.objects.filter(
            status__in=['confirmed', 'paid', 'partial_paid']
        ).order_by('-date'),
        label='الفاتورة الأصلية',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    reason = forms.CharField(
        label='سبب الإرجاع',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )


# ══════════════════════════════════════════════════════
# العملاء
# ══════════════════════════════════════════════════════

class CustomerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'sales'
    permission_action = 'view'
    model = Customer
    template_name = 'sales/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        qs = Customer.objects.all().order_by('code')
        q = self.request.GET.get('q', '').strip()
        customer_type = self.request.GET.get('customer_type', '')
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(phone__icontains=q))
        if customer_type:
            qs = qs.filter(customer_type=customer_type)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['customer_types'] = Customer.CUSTOMER_TYPE_CHOICES
        return ctx


class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_module = 'sales'
    permission_action = 'create'
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('sales:customer_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم إضافة العميل بنجاح')
        return super().form_valid(form)


class CustomerDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'sales'
    permission_action = 'view'
    model = Customer
    template_name = 'sales/customer_detail.html'
    context_object_name = 'customer'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = self.get_object()
        ctx['invoices'] = customer.invoices.order_by('-date')[:20]
        ctx['total_invoiced'] = customer.invoices.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        ctx['total_paid'] = customer.invoices.aggregate(
            paid=Sum('paid_amount')
        )['paid'] or Decimal('0')
        ctx['balance'] = ctx['total_invoiced'] - ctx['total_paid']
        return ctx


# ══════════════════════════════════════════════════════
# فواتير المبيعات
# ══════════════════════════════════════════════════════

class SalesInvoiceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'sales'
    permission_action = 'view'
    model = SalesInvoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = SalesInvoice.objects.select_related(
            'customer', 'branch', 'warehouse'
        ).order_by('-date')
        qs = apply_branch_filter(qs, self.request)
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '')
        customer_id = self.request.GET.get('customer', '')
        branch_id = self.request.GET.get('branch', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) | Q(customer__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = SalesInvoice.STATUS_CHOICES
        ctx['customers'] = Customer.objects.filter(is_active=True).order_by('name')
        ctx['branches'] = Branch.objects.all()
        qs = self.get_queryset()
        ctx['totals'] = qs.aggregate(
            total_amount=Sum('total'),
            total_paid=Sum('paid_amount'),
            total_remaining=Sum('remaining_amount'),
        )
        return ctx


class SalesInvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'sales'
    permission_action = 'create'
    template_name = 'sales/invoice_form.html'

    def get(self, request):
        form = SalesInvoiceForm()
        products = Product.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {'form': form, 'products': products})

    def post(self, request):
        form = SalesInvoiceForm(request.POST)
        products = Product.objects.filter(is_active=True).order_by('name')

        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'products': products})

        # استخراج بنود الفاتورة من POST
        items = []
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')
        discounts = request.POST.getlist('item_discount[]')

        for i, pid in enumerate(product_ids):
            if not pid:
                continue
            try:
                product = Product.objects.get(pk=pid)
                qty = Decimal(quantities[i] or '0')
                price = Decimal(unit_prices[i] or '0')
                disc = Decimal(discounts[i] if discounts and i < len(discounts) else '0')
                if qty > 0 and price > 0:
                    items.append({
                        'product': product,
                        'quantity': qty,
                        'unit_price': price,
                        'discount_percentage': disc,
                    })
            except (Product.DoesNotExist, ValueError, IndexError):
                pass

        if not items:
            messages.error(request, 'يجب إضافة منتج واحد على الأقل')
            return render(request, self.template_name, {'form': form, 'products': products})

        try:
            data = form.cleaned_data
            invoice = SalesEngine.create_invoice(
                customer=data['customer'],
                branch=data['branch'],
                warehouse=data['warehouse'],
                salesperson=request.user,
                items=items,
                payment_method=data['payment_method'],
                sale_channel=data['sale_channel'],
                discount_percentage=data.get('discount_percentage') or 0,
                is_taxable=data.get('is_taxable', True),
                delivery_required=data.get('delivery_required', False),
                delivery_address=data.get('delivery_address', ''),
                delivery_fee=data.get('delivery_fee') or 0,
                notes=data.get('notes', ''),
                user=request.user,
            )
            messages.success(request, f'تم إنشاء الفاتورة {invoice.invoice_number} بنجاح')
            return redirect('sales:invoice_detail', pk=invoice.pk)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء الفاتورة: {e}')
            return render(request, self.template_name, {'form': form, 'products': products})


class SalesInvoiceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'sales'
    permission_action = 'view'
    model = SalesInvoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = self.get_object()
        ctx['lines'] = invoice.lines.select_related('product').all()
        ctx['returns'] = invoice.returns.all()
        return ctx


class ConfirmInvoiceView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'sales'
    permission_action = 'approve'
    def post(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        try:
            SalesEngine.confirm_invoice(invoice, user=request.user)
            messages.success(request, f'تم تأكيد الفاتورة {invoice.invoice_number}')
            # ── إنشاء بطاقات الضمان تلقائياً لكل منتج يحتوي على ضمان ──
            self._create_warranty_cards(invoice, request.user)
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
        return redirect('sales:invoice_detail', pk=pk)

    def _create_warranty_cards(self, invoice, user):
        """إنشاء بطاقات الضمان تلقائياً بعد تأكيد الفاتورة."""
        try:
            from apps.warranty.models import WarrantyCard
            from datetime import timedelta
            from django.utils import timezone

            warranty_count = 0
            for line in invoice.lines.select_related('product').all():
                months = line.product.warranty_months
                if not months or months <= 0:
                    continue
                # إنشاء بطاقة ضمان لكل وحدة (أو بطاقة واحدة للسطر)
                if not WarrantyCard.objects.filter(invoice_line=line).exists():
                    expiry = invoice.date + timedelta(days=30 * months)
                    WarrantyCard.objects.create(
                        serial_number    = WarrantyCard.generate_serial(),
                        invoice          = invoice,
                        invoice_line     = line,
                        customer         = invoice.customer,
                        product          = line.product,
                        purchase_date    = invoice.date,
                        expiry_date      = expiry,
                        status           = 'active',
                        customer_name    = invoice.customer.name,
                        customer_phone   = invoice.customer.phone,
                        customer_address = invoice.customer.address,
                        activated_by     = user,
                        activation_date  = timezone.now(),
                        created_by       = user,
                        updated_by       = user,
                    )
                    warranty_count += 1

            if warranty_count:
                from django.contrib import messages as msg
                # استخدام الـ request من خلال thread-local غير ضروري—
                # الرسائل تُضاف من post() — نكتفي بعدم الرسالة هنا
                pass
        except Exception:
            pass  # لا نكسر تدفق التأكيد إذا فشل الضمان


class RecordPaymentView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'sales'
    permission_action = 'create'
    template_name = 'sales/payment_form.html'

    def get(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        form = RecordPaymentForm()
        return render(request, self.template_name, {'invoice': invoice, 'form': form})

    def post(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            try:
                SalesEngine.record_payment(
                    invoice=invoice,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    user=request.user,
                )
                messages.success(request, 'تم تسجيل الدفعة بنجاح')
                return redirect('sales:invoice_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'invoice': invoice, 'form': form})


# ══════════════════════════════════════════════════════
# المرتجعات
# ══════════════════════════════════════════════════════

class SalesReturnListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'sales'
    permission_action = 'view'
    model = SalesReturn
    template_name = 'sales/return_list.html'
    context_object_name = 'returns'
    paginate_by = 25

    def get_queryset(self):
        qs = SalesReturn.objects.select_related(
            'customer', 'original_invoice'
        ).order_by('-date')
        qs = apply_branch_filter(qs, self.request, 'original_invoice__branch')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(
                Q(return_number__icontains=q) | Q(customer__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = SalesReturn.STATUS_CHOICES
        return ctx


class SalesReturnCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'sales'
    permission_action = 'create'
    template_name = 'sales/return_form.html'

    def get(self, request):
        form = SalesReturnForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SalesReturnForm(request.POST)
        if form.is_valid():
            original_invoice = form.cleaned_data['original_invoice']
            reason = form.cleaned_data['reason']
            items = [
                {'product': line.product, 'quantity': line.quantity}
                for line in original_invoice.lines.all()
            ]
            try:
                ret = SalesEngine.create_return(
                    original_invoice=original_invoice,
                    items=items,
                    reason=reason,
                    user=request.user,
                )
                SalesEngine.approve_return(ret, user=request.user)
                messages.success(request, f'تم إنشاء المرتجع {ret.return_number} بنجاح')
                return redirect('sales:return_list')
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'form': form})


# ══════════════════════════════════════════════════════
# قوائم الأسعار
# ══════════════════════════════════════════════════════

class PriceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'sales'
    permission_action = 'view'
    model = PriceList
    template_name = 'sales/price_lists.html'
    context_object_name = 'price_lists'

    def get_queryset(self):
        return PriceList.objects.prefetch_related('items__product').order_by('name')


# ══════════════════════════════════════════════════════
# إضافة عميل سريع (AJAX)
# ══════════════════════════════════════════════════════

@login_required
@require_POST
def quick_add_customer(request):
    """
    إضافة عميل سريع عبر AJAX
    يُستخدم في فورم الفاتورة أو عرض السعر
    """
    data = json.loads(request.body)

    last = Customer.objects.order_by('-code').first()
    if last and last.code.startswith('C'):
        try:
            new_num = int(last.code[1:]) + 1
        except ValueError:
            new_num = 1
    else:
        new_num = 1

    customer = Customer.objects.create(
        code=f'C{new_num:04d}',
        name=data.get('name', ''),
        customer_type=data.get('customer_type', 'retail'),
        phone=data.get('phone', ''),
        phone2=data.get('phone2', ''),
        address=data.get('address', ''),
        governorate=data.get('governorate', ''),
        branch=request.current_branch,
        is_active=True,
        created_by=request.user,
        updated_by=request.user,
    )

    return JsonResponse({
        'success': True,
        'customer': {
            'id': customer.id,
            'code': customer.code,
            'name': customer.name,
            'phone': customer.phone,
        }
    })


# ══════════════════════════════════════════════════════
# Sprint 20 — Views إضافية للمبيعات
# ══════════════════════════════════════════════════════

from django.views import View
from django.shortcuts import render, get_object_or_404


class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """تعديل بيانات العميل"""
    permission_module = 'sales'
    permission_action = 'edit'
    model = Customer
    fields = ['name', 'code', 'phone', 'email', 'address', 'tax_number',
              'credit_limit', 'payment_terms', 'discount_percentage', 'is_active']
    template_name = 'sales/customer_form.html'
    success_url = '/sales/customers/'

    def get_form(self, form_class=None):
        from django import forms
        form = super().get_form(form_class)
        for field in form.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل عميل: {self.object.name}'
        ctx['edit_mode'] = True
        return ctx

    def form_valid(self, form):
        from django.contrib import messages
        messages.success(self.request, f'تم تحديث بيانات العميل "{form.instance.name}"')
        return super().form_valid(form)


class CustomerStatementView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """كشف حساب عميل"""
    permission_module = 'sales'
    permission_action = 'view'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        invoices = customer.invoices.order_by('date').select_related('branch')
        payments = getattr(customer, 'payments', customer.invoices.none())

        # رصيد تراكمي
        from decimal import Decimal
        running_balance = Decimal('0')
        statement = []
        for inv in invoices:
            running_balance += inv.total
            running_balance -= (inv.total - getattr(inv, 'remaining_amount', inv.total))
            statement.append({
                'date': inv.date,
                'type': 'فاتورة',
                'reference': inv.invoice_number,
                'debit': inv.total,
                'credit': Decimal('0'),
                'balance': running_balance,
                'obj': inv,
            })

        export = request.GET.get('export')
        if export == 'excel':
            return self._export_excel(customer, statement)

        return render(request, 'sales/customer_statement.html', {
            'title': f'كشف حساب: {customer.name}',
            'customer': customer,
            'statement': statement,
            'total_debit': sum(s['debit'] for s in statement),
            'total_credit': sum(s['credit'] for s in statement),
            'final_balance': running_balance,
        })

    def _export_excel(self, customer, statement):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="statement_{customer.code}.csv"'
        writer = csv.writer(response)
        writer.writerow(['التاريخ', 'النوع', 'المرجع', 'مدين', 'دائن', 'الرصيد'])
        for s in statement:
            writer.writerow([s['date'], s['type'], s['reference'], s['debit'], s['credit'], s['balance']])
        return response


class InvoiceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعديل فاتورة في حالة مسودة"""
    permission_module = 'sales'
    permission_action = 'edit'

    def get(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        if invoice.status != 'draft':
            from django.contrib import messages
            messages.error(request, 'لا يمكن تعديل فاتورة مؤكدة.')
            return redirect('sales:invoice_detail', pk=pk)
        return render(request, 'sales/invoice_update.html', {
            'title': f'تعديل فاتورة: {invoice.invoice_number}',
            'invoice': invoice,
            'lines': invoice.lines.select_related('product').all(),
        })

    def post(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        if invoice.status != 'draft':
            from django.contrib import messages
            messages.error(request, 'لا يمكن تعديل فاتورة مؤكدة.')
            return redirect('sales:invoice_detail', pk=pk)
        notes = request.POST.get('notes', invoice.notes)
        invoice.notes = notes
        invoice.save()
        from django.contrib import messages
        messages.success(request, f'تم تحديث الفاتورة {invoice.invoice_number}')
        return redirect('sales:invoice_detail', pk=pk)


class InvoiceCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إلغاء فاتورة مؤكدة"""
    permission_module = 'sales'
    permission_action = 'approve'

    def post(self, request, pk):
        from django.contrib import messages
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        if invoice.status not in ('confirmed', 'partial_paid'):
            messages.error(request, 'لا يمكن إلغاء هذه الفاتورة في حالتها الحالية.')
            return redirect('sales:invoice_detail', pk=pk)

        # إرجاع المخزون
        try:
            from apps.inventory.services.stock_engine import StockEngine
            for line in invoice.lines.select_related('product'):
                try:
                    warehouse = getattr(invoice, 'warehouse', None)
                    if warehouse and line.product:
                        StockEngine.receive_stock(
                            product=line.product,
                            warehouse=warehouse,
                            quantity=line.quantity,
                            unit_cost=line.cost_price,
                            source_type='invoice_cancel',
                            source_id=invoice.pk,
                            notes=f'إلغاء فاتورة {invoice.invoice_number}',
                            user=request.user,
                        )
                except Exception:
                    pass
        except Exception:
            pass

        invoice.status = 'cancelled'
        invoice.save()
        messages.success(request, f'تم إلغاء الفاتورة {invoice.invoice_number}')
        return redirect('sales:invoice_list')


class InvoicePrintView(LoginRequiredMixin, View):
    """طباعة فاتورة A4"""
    def get(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        try:
            from apps.core.models import Company
            company = Company.objects.first()
        except Exception:
            company = None
        return render(request, 'sales/invoice_print.html', {
            'invoice': invoice,
            'lines': invoice.lines.select_related('product').all(),
            'company': company,
        })


class InvoiceThermalView(LoginRequiredMixin, View):
    """طباعة فاتورة حرارية 80mm"""
    def get(self, request, pk):
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        try:
            from apps.core.models import Company
            company = Company.objects.first()
        except Exception:
            company = None
        return render(request, 'sales/invoice_thermal.html', {
            'invoice': invoice,
            'lines': invoice.lines.select_related('product').all(),
            'company': company,
        })


class PriceListCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إنشاء قائمة أسعار"""
    permission_module = 'sales'
    permission_action = 'create'

    def get(self, request):
        return render(request, 'sales/price_list_form.html', {
            'title': 'قائمة أسعار جديدة',
        })

    def post(self, request):
        from django.contrib import messages
        name = request.POST.get('name', '')
        if name and PriceList is not None:
            pl = PriceList.objects.create(
                name=name,
                description=request.POST.get('description', ''),
                is_active=True,
            )
            messages.success(request, f'تم إنشاء قائمة الأسعار "{pl.name}"')
            return redirect('sales:price_lists')
        messages.error(request, 'يرجى إدخال اسم قائمة الأسعار.')
        return redirect('sales:price_lists')


class PriceListDetailView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تفاصيل قائمة أسعار"""
    permission_module = 'sales'
    permission_action = 'view'

    def get(self, request, pk):
        if PriceList is None:
            from django.http import Http404
            raise Http404
        price_list = get_object_or_404(PriceList, pk=pk)
        return render(request, 'sales/price_list_detail.html', {
            'title': f'قائمة أسعار: {price_list.name}',
            'price_list': price_list,
        })


class PriceListUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعديل قائمة أسعار"""
    permission_module = 'sales'
    permission_action = 'edit'

    def get(self, request, pk):
        if PriceList is None:
            from django.http import Http404
            raise Http404
        price_list = get_object_or_404(PriceList, pk=pk)
        return render(request, 'sales/price_list_form.html', {
            'title': f'تعديل: {price_list.name}',
            'price_list': price_list,
            'edit_mode': True,
        })

    def post(self, request, pk):
        from django.contrib import messages
        if PriceList is None:
            from django.http import Http404
            raise Http404
        price_list = get_object_or_404(PriceList, pk=pk)
        price_list.name = request.POST.get('name', price_list.name)
        price_list.description = request.POST.get('description', price_list.description)
        price_list.save()
        messages.success(request, f'تم تحديث قائمة الأسعار "{price_list.name}"')
        return redirect('sales:price_lists')
