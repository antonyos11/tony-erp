"""
واجهات تطبيق المبيعات — RITA ERP
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, View,
)

from apps.core.models import Branch, Warehouse
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesReturn, PriceList
from apps.inventory.models import Product
from apps.sales.services.sales_engine import SalesEngine
from apps.authorization.decorators import PermissionRequiredMixin


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
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
        return redirect('sales:invoice_detail', pk=pk)


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
