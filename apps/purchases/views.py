"""
واجهات تطبيق المشتريات — RITA ERP
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, View

from apps.core.models import Branch, Warehouse
from apps.partners.models import Supplier
from apps.purchases.models import PurchaseOrder, PurchaseOrderLine
from apps.inventory.models import Product
from apps.purchases.services.purchase_engine import PurchaseEngine
from apps.authorization.decorators import PermissionRequiredMixin


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'code', 'name', 'supplier_type', 'phone', 'phone2',
            'address', 'country', 'tax_number', 'is_taxable',
            'payment_terms', 'account', 'contact_person',
            'bank_name', 'bank_account', 'is_active',
        ]
        widgets = {
            'code':          forms.TextInput(attrs={'class': 'form-control'}),
            'name':          forms.TextInput(attrs={'class': 'form-control'}),
            'supplier_type': forms.Select(attrs={'class': 'form-select'}),
            'phone':         forms.TextInput(attrs={'class': 'form-control'}),
            'phone2':        forms.TextInput(attrs={'class': 'form-control'}),
            'address':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'country':       forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number':    forms.TextInput(attrs={'class': 'form-control'}),
            'is_taxable':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_terms': forms.NumberInput(attrs={'class': 'form-control'}),
            'account':       forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account':  forms.TextInput(attrs={'class': 'form-control'}),
            'is_active':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseOrderForm(forms.Form):
    """فورم إنشاء أمر شراء"""
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True).order_by('name'),
        label='المورد', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='المخزن', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_taxable = forms.BooleanField(
        required=False, initial=True,
        label='شراء ضريبي',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    notes = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


# ══════════════════════════════════════════════════════
# الموردون
# ══════════════════════════════════════════════════════

class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = Supplier
    template_name = 'purchases/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 25

    def get_queryset(self):
        qs = Supplier.objects.all().order_by('code')
        q = self.request.GET.get('q', '').strip()
        supplier_type = self.request.GET.get('supplier_type', '')
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(name__icontains=q) | Q(phone__icontains=q)
            )
        if supplier_type:
            qs = qs.filter(supplier_type=supplier_type)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['supplier_types'] = Supplier.SUPPLIER_TYPE_CHOICES
        return ctx


class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_module = 'purchases'
    permission_action = 'create'
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'
    success_url = reverse_lazy('purchases:supplier_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم إضافة المورد بنجاح')
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = Supplier
    template_name = 'purchases/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supplier = self.get_object()
        ctx['orders'] = supplier.purchase_orders.order_by('-date')[:20]
        ctx['total_ordered'] = supplier.purchase_orders.aggregate(
            total=Sum('total')
        )['total'] or Decimal('0')
        ctx['total_paid'] = supplier.purchase_orders.aggregate(
            paid=Sum('paid_amount')
        )['paid'] or Decimal('0')
        ctx['balance'] = ctx['total_ordered'] - ctx['total_paid']
        return ctx


# ══════════════════════════════════════════════════════
# أوامر الشراء
# ══════════════════════════════════════════════════════

class PurchaseOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = PurchaseOrder
    template_name = 'purchases/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related(
            'supplier', 'branch', 'warehouse'
        ).order_by('-date')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '')
        supplier_id = self.request.GET.get('supplier', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) | Q(supplier__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = PurchaseOrder.ORDER_STATUSES
        ctx['suppliers'] = Supplier.objects.filter(is_active=True).order_by('name')
        qs = self.get_queryset()
        ctx['totals'] = qs.aggregate(
            total_amount=Sum('total'),
            total_paid=Sum('paid_amount'),
            total_remaining=Sum('remaining_amount'),
        )
        return ctx


class PurchaseOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'purchases'
    permission_action = 'create'
    template_name = 'purchases/order_form.html'

    def get(self, request):
        form = PurchaseOrderForm()
        products = Product.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {'form': form, 'products': products})

    def post(self, request):
        form = PurchaseOrderForm(request.POST)
        products = Product.objects.filter(is_active=True).order_by('name')

        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'products': products})

        # استخراج بنود أمر الشراء من POST
        items = []
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')

        for i, pid in enumerate(product_ids):
            if not pid:
                continue
            try:
                product = Product.objects.get(pk=pid)
                qty = Decimal(quantities[i] or '0')
                cost = Decimal(unit_costs[i] or '0')
                if qty > 0 and cost > 0:
                    items.append({
                        'product': product,
                        'quantity': qty,
                        'unit_cost': cost,
                    })
            except (Product.DoesNotExist, ValueError, IndexError):
                pass

        if not items:
            messages.error(request, 'يجب إضافة منتج واحد على الأقل')
            return render(request, self.template_name, {'form': form, 'products': products})

        try:
            data = form.cleaned_data
            order = PurchaseEngine.create_purchase_order(
                supplier=data['supplier'],
                branch=data['branch'],
                warehouse=data['warehouse'],
                items=items,
                is_taxable=data.get('is_taxable', True),
                notes=data.get('notes', ''),
                user=request.user,
            )
            messages.success(request, f'تم إنشاء أمر الشراء {order.order_number} بنجاح')
            return redirect('purchases:order_detail', pk=order.pk)
        except Exception as e:
            messages.error(request, f'خطأ في إنشاء أمر الشراء: {e}')
            return render(request, self.template_name, {'form': form, 'products': products})


class PurchaseOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = PurchaseOrder
    template_name = 'purchases/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = self.get_object()
        ctx['lines'] = order.lines.select_related('product').all()
        return ctx


class ReceivePurchaseView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'purchases'
    permission_action = 'approve'
    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            PurchaseEngine.receive_purchase(order, user=request.user)
            messages.success(request, f'تم استلام أمر الشراء {order.order_number} بنجاح')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')
        return redirect('purchases:order_detail', pk=pk)
