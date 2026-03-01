"""
واجهات تطبيق التوصيل — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, TemplateView,
)

from apps.delivery.models import DeliveryOrder, DeliveryZone


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class DeliveryOrderForm(forms.ModelForm):
    class Meta:
        model  = DeliveryOrder
        fields = [
            'invoice', 'zone', 'driver', 'delivery_address',
            'delivery_fee', 'delivery_date', 'notes',
        ]
        widgets = {
            'invoice':          forms.Select(attrs={'class': 'form-select'}),
            'zone':             forms.Select(attrs={'class': 'form-select'}),
            'driver':           forms.Select(attrs={'class': 'form-select'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_fee':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_date':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes':            forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class DeliveryStatusForm(forms.Form):
    STATUS_CHOICES = DeliveryOrder.DELIVERY_STATUSES
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='الحالة الجديدة',
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='ملاحظات',
    )


# ══════════════════════════════════════════════════════
# مناطق التوصيل
# ══════════════════════════════════════════════════════

class DeliveryZoneListView(LoginRequiredMixin, ListView):
    model               = DeliveryZone
    template_name       = 'delivery/zone_list.html'
    context_object_name = 'zones'
    paginate_by         = 20

    def get_queryset(self):
        qs = DeliveryZone.objects.filter(is_deleted=False)
        q  = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(governorate__icontains=q))
        return qs


# ══════════════════════════════════════════════════════
# أوامر التوصيل
# ══════════════════════════════════════════════════════

class DeliveryOrderListView(LoginRequiredMixin, ListView):
    model               = DeliveryOrder
    template_name       = 'delivery/order_list.html'
    context_object_name = 'orders'
    paginate_by         = 25

    def get_queryset(self):
        qs = DeliveryOrder.objects.filter(is_deleted=False).select_related(
            'invoice', 'zone', 'driver',
        )
        status = self.request.GET.get('status')
        q      = self.request.GET.get('q')
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(delivery_address__icontains=q) |
                Q(invoice__invoice_number__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx             = super().get_context_data(**kwargs)
        ctx['statuses'] = DeliveryOrder.DELIVERY_STATUSES
        return ctx


class DeliveryOrderCreateView(LoginRequiredMixin, CreateView):
    model         = DeliveryOrder
    form_class    = DeliveryOrderForm
    template_name = 'delivery/order_form.html'
    success_url   = reverse_lazy('delivery:order_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'تم إنشاء أمر التوصيل بنجاح.')
        return super().form_valid(form)


class DeliveryTrackingView(LoginRequiredMixin, UpdateView):
    """تحديث حالة التوصيل."""
    model         = DeliveryOrder
    template_name = 'delivery/order_tracking.html'
    success_url   = reverse_lazy('delivery:order_list')

    def get_form(self, form_class=None):
        if self.request.method == 'POST':
            return DeliveryStatusForm(self.request.POST)
        return DeliveryStatusForm(initial={'status': self.get_object().status})

    def form_valid(self, form):
        obj         = self.get_object()
        obj.status  = form.cleaned_data['status']
        if form.cleaned_data.get('notes'):
            obj.notes = (obj.notes + '\n' + form.cleaned_data['notes']).strip()
        obj.updated_by = self.request.user
        obj.save()
        messages.success(self.request, f'تم تحديث حالة التوصيل إلى: {obj.get_status_display()}')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx           = super().get_context_data(**kwargs)
        ctx['object'] = self.get_object()
        return ctx
