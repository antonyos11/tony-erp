"""
واجهات تطبيق الشركاء (الموردين) — RITA ERP
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
import csv

from apps.partners.models import Supplier
from apps.authorization.decorators import PermissionRequiredMixin


# ══════════════════════════════════════════════════════
# قائمة الموردين
# ══════════════════════════════════════════════════════

class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = Supplier
    template_name = 'partners/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 25

    def get_queryset(self):
        qs = Supplier.objects.filter(is_deleted=False).order_by('code')
        q = self.request.GET.get('q', '').strip()
        supplier_type = self.request.GET.get('type', '')
        is_active = self.request.GET.get('active', '')
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(name__icontains=q) |
                Q(phone__icontains=q) | Q(contact_person__icontains=q)
            )
        if supplier_type:
            qs = qs.filter(supplier_type=supplier_type)
        if is_active == '1':
            qs = qs.filter(is_active=True)
        elif is_active == '0':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['type_choices'] = Supplier.SUPPLIER_TYPE_CHOICES
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_type'] = self.request.GET.get('type', '')
        ctx['selected_active'] = self.request.GET.get('active', '')
        ctx['total_count'] = Supplier.objects.filter(is_deleted=False).count()
        ctx['active_count'] = Supplier.objects.filter(is_deleted=False, is_active=True).count()
        return ctx


# ══════════════════════════════════════════════════════
# تفاصيل المورد
# ══════════════════════════════════════════════════════

class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'purchases'
    permission_action = 'view'
    model = Supplier
    template_name = 'partners/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        supplier = self.object
        try:
            from apps.purchases.models import PurchaseOrder
            ctx['recent_orders'] = PurchaseOrder.objects.filter(
                supplier=supplier, is_deleted=False
            ).order_by('-date')[:10]
            ctx['total_purchases'] = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['received', 'confirmed'],
                is_deleted=False,
            ).aggregate(total=Sum('total'))['total'] or 0
            ctx['pending_orders'] = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['draft', 'confirmed'],
                is_deleted=False,
            ).count()
        except Exception:
            ctx['recent_orders'] = []
            ctx['total_purchases'] = 0
            ctx['pending_orders'] = 0
        return ctx


# ══════════════════════════════════════════════════════
# إنشاء مورد
# ══════════════════════════════════════════════════════

class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_module = 'purchases'
    permission_action = 'create'
    model = Supplier
    template_name = 'partners/supplier_form.html'
    fields = [
        'code', 'name', 'supplier_type', 'phone', 'phone2',
        'address', 'country', 'tax_number', 'is_taxable',
        'payment_terms', 'contact_person', 'bank_name', 'bank_account',
        'is_active',
    ]
    success_url = reverse_lazy('partners:supplier_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'تم إنشاء المورد {form.instance.name} بنجاح')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إضافة مورد جديد'
        ctx['btn_label'] = 'حفظ المورد'
        return ctx


# ══════════════════════════════════════════════════════
# تعديل مورد
# ══════════════════════════════════════════════════════

class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_module = 'purchases'
    permission_action = 'edit'
    model = Supplier
    template_name = 'partners/supplier_form.html'
    fields = [
        'name', 'supplier_type', 'phone', 'phone2',
        'address', 'country', 'tax_number', 'is_taxable',
        'payment_terms', 'contact_person', 'bank_name', 'bank_account',
        'is_active',
    ]

    def get_success_url(self):
        return reverse_lazy('partners:supplier_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        return form

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'تم تحديث بيانات المورد {self.object.name}')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل: {self.object.name}'
        ctx['btn_label'] = 'حفظ التغييرات'
        return ctx


# ══════════════════════════════════════════════════════
# تفعيل / تعطيل مورد
# ══════════════════════════════════════════════════════

class SupplierToggleActiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'purchases'
    permission_action = 'edit'

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk, is_deleted=False)
        supplier.is_active = not supplier.is_active
        supplier.updated_by = request.user
        supplier.save(update_fields=['is_active', 'updated_by'])
        status_label = 'نشط' if supplier.is_active else 'معطّل'
        messages.success(request, f'تم تغيير حالة المورد إلى: {status_label}')
        return redirect('partners:supplier_detail', pk=pk)


# ══════════════════════════════════════════════════════
# كشف حساب المورد
# ══════════════════════════════════════════════════════

class SupplierStatementView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'purchases'
    permission_action = 'view'
    template_name = 'partners/supplier_statement.html'

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk, is_deleted=False)
        date_from = request.GET.get('date_from', '')
        date_to   = request.GET.get('date_to', '')

        orders_qs = []
        total_orders = 0
        try:
            from apps.purchases.models import PurchaseOrder
            orders_qs = PurchaseOrder.objects.filter(
                supplier=supplier, is_deleted=False,
            ).order_by('date')
            if date_from:
                orders_qs = orders_qs.filter(date__gte=date_from)
            if date_to:
                orders_qs = orders_qs.filter(date__lte=date_to)
            total_orders = orders_qs.filter(
                status__in=['confirmed', 'received']
            ).aggregate(t=Sum('total'))['t'] or 0
        except Exception:
            pass

        if request.GET.get('export') == 'csv':
            return self._export_csv(supplier, orders_qs)

        return render(request, self.template_name, {
            'supplier': supplier,
            'orders': orders_qs,
            'total_orders': total_orders,
            'date_from': date_from,
            'date_to': date_to,
        })

    def _export_csv(self, supplier, orders):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="supplier_{supplier.code}_statement.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(['رقم الأمر', 'التاريخ', 'الحالة', 'الإجمالي'])
        for o in orders:
            writer.writerow([o.order_number, o.date, o.get_status_display(), o.total])
        return response


# ══════════════════════════════════════════════════════
# تصدير CSV لكل الموردين
# ══════════════════════════════════════════════════════

class SupplierExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_module = 'purchases'
    permission_action = 'view'

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'
        writer = csv.writer(response)
        writer.writerow(['الكود', 'الاسم', 'النوع', 'الهاتف', 'الدولة', 'شروط الدفع (أيام)', 'نشط'])
        for s in Supplier.objects.filter(is_deleted=False).order_by('code'):
            writer.writerow([
                s.code, s.name, s.get_supplier_type_display(),
                s.phone, s.country, s.payment_terms,
                'نعم' if s.is_active else 'لا',
            ])
        return response
