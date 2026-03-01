"""
واجهات تطبيق الضمان — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView, FormView,
)

from apps.warranty.models import WarrantyCard, WarrantyClaim


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class WarrantyActivateForm(forms.ModelForm):
    class Meta:
        model  = WarrantyCard
        fields = [
            'invoice', 'invoice_line', 'customer', 'product',
            'purchase_date', 'expiry_date',
            'customer_name', 'customer_phone', 'customer_address',
        ]
        widgets = {
            'invoice':          forms.Select(attrs={'class': 'form-select'}),
            'invoice_line':     forms.Select(attrs={'class': 'form-select'}),
            'customer':         forms.Select(attrs={'class': 'form-select'}),
            'product':          forms.Select(attrs={'class': 'form-select'}),
            'purchase_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'customer_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone':   forms.TextInput(attrs={'class': 'form-control'}),
            'customer_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class WarrantyClaimForm(forms.ModelForm):
    class Meta:
        model  = WarrantyClaim
        fields = ['warranty', 'claim_date', 'issue_description', 'resolution', 'status']
        widgets = {
            'warranty':          forms.Select(attrs={'class': 'form-select'}),
            'claim_date':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'resolution':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status':            forms.Select(attrs={'class': 'form-select'}),
        }


class WarrantySearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': 'ابحث برقم الضمان أو رقم الفاتورة أو اسم العميل',
        }),
        label='بحث',
    )


# ══════════════════════════════════════════════════════
# تفعيل الضمان
# ══════════════════════════════════════════════════════

class WarrantyActivateView(LoginRequiredMixin, CreateView):
    """تفعيل يدوي لبطاقة ضمان جديدة."""
    model         = WarrantyCard
    form_class    = WarrantyActivateForm
    template_name = 'warranty/activate_form.html'
    success_url   = reverse_lazy('warranty:warranty_search')

    def form_valid(self, form):
        obj                 = form.save(commit=False)
        obj.serial_number   = WarrantyCard.generate_serial()
        obj.activated_by    = self.request.user
        obj.activation_date = timezone.now()
        obj.created_by      = self.request.user
        obj.save()
        messages.success(self.request, f'تم تفعيل بطاقة الضمان: {obj.serial_number}')
        return redirect('warranty:warranty_detail', pk=obj.pk)


# ══════════════════════════════════════════════════════
# البحث
# ══════════════════════════════════════════════════════

class WarrantySearchView(LoginRequiredMixin, ListView):
    """بحث ببطاقات الضمان."""
    model               = WarrantyCard
    template_name       = 'warranty/search.html'
    context_object_name = 'warranties'
    paginate_by         = 20

    def get_queryset(self):
        qs = WarrantyCard.objects.filter(is_deleted=False).select_related(
            'invoice', 'customer', 'product',
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(serial_number__icontains=q) |
                Q(invoice__invoice_number__icontains=q) |
                Q(customer_name__icontains=q) |
                Q(customer_phone__icontains=q) |
                Q(product__name__icontains=q) |
                Q(product__code__icontains=q)
            )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        # تحديث الحالات المنتهية
        today = timezone.now().date()
        qs.filter(status='active', expiry_date__lt=today).update(status='expired')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form']     = WarrantySearchForm(self.request.GET or None)
        ctx['statuses'] = WarrantyCard.WARRANTY_STATUSES
        return ctx


# ══════════════════════════════════════════════════════
# تفاصيل الضمان
# ══════════════════════════════════════════════════════

class WarrantyDetailView(LoginRequiredMixin, DetailView):
    model               = WarrantyCard
    template_name       = 'warranty/detail.html'
    context_object_name = 'warranty'

    def get_context_data(self, **kwargs):
        ctx         = super().get_context_data(**kwargs)
        ctx['claims'] = self.object.claims.all().order_by('-claim_date')
        return ctx


# ══════════════════════════════════════════════════════
# مطالبات الضمان
# ══════════════════════════════════════════════════════

class WarrantyClaimCreateView(LoginRequiredMixin, CreateView):
    model         = WarrantyClaim
    form_class    = WarrantyClaimForm
    template_name = 'warranty/claim_form.html'

    def get_initial(self):
        initial = super().get_initial()
        warranty_pk = self.kwargs.get('warranty_pk') or self.request.GET.get('warranty')
        if warranty_pk:
            initial['warranty']   = warranty_pk
            initial['claim_date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'تم تسجيل مطالبة الضمان بنجاح.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('warranty:warranty_detail', kwargs={'pk': self.object.warranty.pk})
