"""
واجهات تطبيق المشتريات — RITA ERP
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
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View

from apps.core.models import Branch, Warehouse
from apps.core.mixins import apply_branch_filter, BranchCreateMixin
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
        qs = apply_branch_filter(qs, self.request)
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


# ══════════════════════════════════════════════════════
# إضافة مورد سريع (AJAX)
# ══════════════════════════════════════════════════════

@login_required
@require_POST
def quick_add_supplier(request):
    """
    إضافة مورد سريع عبر AJAX
    يُستخدم في فورم أمر الشراء
    """
    data = json.loads(request.body)

    last = Supplier.objects.order_by('-code').first()
    if last and last.code.startswith('S'):
        try:
            new_num = int(last.code[1:]) + 1
        except ValueError:
            new_num = 1
    else:
        new_num = 1

    supplier = Supplier.objects.create(
        code=f'S{new_num:04d}',
        name=data.get('name', ''),
        supplier_type=data.get('supplier_type', 'local'),
        phone=data.get('phone', ''),
        phone2=data.get('phone2', ''),
        address=data.get('address', ''),
        country=data.get('country', 'مصر'),
        contact_person=data.get('contact_person', ''),
        is_active=True,
        created_by=request.user,
        updated_by=request.user,
    )

    return JsonResponse({
        'success': True,
        'supplier': {
            'id': supplier.id,
            'code': supplier.code,
            'name': supplier.name,
            'phone': supplier.phone,
        }
    })


# ══════════════════════════════════════════════════════
# Sprint 20 — Views إضافية للمشتريات
# ══════════════════════════════════════════════════════

class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """تعديل بيانات المورد"""
    permission_module = 'purchases'
    permission_action = 'edit'
    model = Supplier
    fields = ['name', 'code', 'phone', 'email', 'address', 'tax_number',
              'payment_terms', 'is_active']
    template_name = 'purchases/supplier_form.html'
    success_url = '/purchases/suppliers/'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            import django.forms as dforms
            if isinstance(field.widget, dforms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل مورد: {self.object.name}'
        ctx['edit_mode'] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم تحديث بيانات المورد "{form.instance.name}"')
        return super().form_valid(form)


class SupplierStatementView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """كشف حساب مورد"""
    permission_module = 'purchases'
    permission_action = 'view'

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        orders = PurchaseOrder.objects.filter(
            supplier=supplier
        ).order_by('order_date')

        from decimal import Decimal as D
        running_balance = D('0')
        statement = []
        for order in orders:
            total = getattr(order, 'total', D('0')) or D('0')
            paid = getattr(order, 'paid_amount', D('0')) or D('0')
            running_balance += total - paid
            statement.append({
                'date': order.order_date,
                'type': 'أمر شراء',
                'reference': order.order_number,
                'debit': D('0'),
                'credit': total,
                'balance': running_balance,
                'obj': order,
            })

        export = request.GET.get('export')
        if export == 'excel':
            import csv
            from django.http import HttpResponse
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="supplier_stmt_{supplier.code}.csv"'
            writer = csv.writer(response)
            writer.writerow(['التاريخ', 'النوع', 'المرجع', 'مدين', 'دائن', 'الرصيد'])
            for s in statement:
                writer.writerow([s['date'], s['type'], s['reference'], s['debit'], s['credit'], s['balance']])
            return response

        return render(request, 'purchases/supplier_statement.html', {
            'title': f'كشف حساب مورد: {supplier.name}',
            'supplier': supplier,
            'statement': statement,
            'final_balance': running_balance,
        })


class PurchaseOrderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعديل أمر شراء في حالة مسودة"""
    permission_module = 'purchases'
    permission_action = 'edit'

    def get(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status != 'draft':
            messages.error(request, 'لا يمكن تعديل أمر شراء مؤكد.')
            return redirect('purchases:order_detail', pk=pk)
        lines = order.lines.select_related('product').all()
        return render(request, 'purchases/order_update.html', {
            'title': f'تعديل أمر شراء: {order.order_number}',
            'order': order,
            'lines': lines,
        })

    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status != 'draft':
            messages.error(request, 'لا يمكن تعديل أمر شراء مؤكد.')
            return redirect('purchases:order_detail', pk=pk)
        order.notes = request.POST.get('notes', order.notes)
        order.save()
        messages.success(request, f'تم تحديث أمر الشراء {order.order_number}')
        return redirect('purchases:order_detail', pk=pk)


class PurchaseOrderCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إلغاء أمر شراء"""
    permission_module = 'purchases'
    permission_action = 'approve'

    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        if order.status in ('received', 'cancelled'):
            messages.error(request, 'لا يمكن إلغاء هذا الأمر.')
            return redirect('purchases:order_detail', pk=pk)
        order.status = 'cancelled'
        order.save()
        messages.success(request, f'تم إلغاء أمر الشراء {order.order_number}')
        return redirect('purchases:order_list')


class PurchaseOrderPrintView(LoginRequiredMixin, View):
    """طباعة أمر شراء"""
    def get(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        try:
            from apps.core.models import Company
            company = Company.objects.first()
        except Exception:
            company = None
        return render(request, 'purchases/order_print.html', {
            'order': order,
            'lines': order.lines.select_related('product').all(),
            'company': company,
        })
