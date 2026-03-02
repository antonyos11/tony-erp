"""
واجهات تطبيق الأقساط — RITA ERP
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, View, CreateView

from apps.installments.models import InstallmentPlan, Installment
from apps.installments.services.installment_engine import InstallmentEngine
from apps.sales.models import Customer, SalesInvoice


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class InstallmentPlanForm(forms.Form):
    """فورم إنشاء خطة أقساط"""
    invoice = forms.ModelChoiceField(
        queryset=SalesInvoice.objects.filter(is_deleted=False).order_by('-date'),
        label='الفاتورة',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    down_payment = forms.DecimalField(
        label='المقدم', min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    number_of_installments = forms.IntegerField(
        label='عدد الأقساط', min_value=1, max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    interest_rate = forms.DecimalField(
        label='نسبة الفائدة %', min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    start_date = forms.DateField(
        label='تاريخ أول قسط',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )


class PayInstallmentForm(forms.Form):
    """فورم دفع قسط"""
    paid_amount = forms.DecimalField(
        label='المبلغ المدفوع', min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    payment_date = forms.DateField(
        label='تاريخ الدفع',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
    )


# ══════════════════════════════════════════════════════
# Plan Views
# ══════════════════════════════════════════════════════

class InstallmentPlanListView(LoginRequiredMixin, ListView):
    model = InstallmentPlan
    template_name = 'installments/plan_list.html'
    context_object_name = 'plans'

    def get_queryset(self):
        qs = InstallmentPlan.objects.filter(is_deleted=False).select_related(
            'invoice', 'customer',
        )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        customer_id = self.request.GET.get('customer')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = InstallmentPlan.STATUS_CHOICES
        ctx['customers'] = Customer.objects.filter(is_deleted=False).order_by('name')
        return ctx


class InstallmentPlanCreateView(LoginRequiredMixin, View):
    template_name = 'installments/plan_form.html'

    def get(self, request):
        return render(request, self.template_name, {'form': InstallmentPlanForm()})

    def post(self, request):
        form = InstallmentPlanForm(request.POST)
        if form.is_valid():
            invoice = form.cleaned_data['invoice']
            try:
                plan = InstallmentEngine.create_plan(
                    invoice=invoice,
                    customer=invoice.customer,
                    total_amount=invoice.total_amount,
                    down_payment=form.cleaned_data['down_payment'],
                    number_of_installments=form.cleaned_data['number_of_installments'],
                    interest_rate=form.cleaned_data['interest_rate'],
                    start_date=form.cleaned_data['start_date'],
                    user=request.user,
                )
                messages.success(request, f'تم إنشاء خطة أقساط بـ {plan.number_of_installments} قسط')
                return redirect('installments:plan_detail', pk=plan.pk)
            except Exception as e:
                messages.error(request, str(e))

        return render(request, self.template_name, {'form': form})


class InstallmentPlanDetailView(LoginRequiredMixin, DetailView):
    model = InstallmentPlan
    template_name = 'installments/plan_detail.html'
    context_object_name = 'plan'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schedule'] = InstallmentEngine.get_schedule(self.object)
        ctx['pay_form'] = PayInstallmentForm()
        return ctx


# ══════════════════════════════════════════════════════
# Installment Payment View
# ══════════════════════════════════════════════════════

class PayInstallmentView(LoginRequiredMixin, View):
    """تسجيل دفعة قسط"""

    def post(self, request, pk):
        installment = get_object_or_404(Installment, pk=pk, is_deleted=False)
        form = PayInstallmentForm(request.POST)
        if form.is_valid():
            try:
                InstallmentEngine.pay_installment(
                    installment=installment,
                    paid_amount=form.cleaned_data['paid_amount'],
                    payment_date=form.cleaned_data.get('payment_date'),
                    user=request.user,
                )
                messages.success(request, f'تم تسجيل دفعة القسط #{installment.installment_number}')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'بيانات غير صحيحة')

        return redirect('installments:plan_detail', pk=installment.plan_id)


# ══════════════════════════════════════════════════════
# Overdue View
# ══════════════════════════════════════════════════════

class OverdueInstallmentsView(LoginRequiredMixin, ListView):
    template_name = 'installments/overdue_list.html'
    context_object_name = 'installments'

    def get_queryset(self):
        return Installment.objects.filter(
            status__in=('overdue', 'pending'),
            is_deleted=False,
        ).select_related('plan', 'plan__customer').order_by('due_date')


# ══════════════════════════════════════════════════════
# تصدير جدول الأقساط CSV
# ══════════════════════════════════════════════════════

class InstallmentPlanExportView(LoginRequiredMixin, View):
    """تصدير جدول سداد خطة أقساط إلى CSV"""

    def get(self, request, pk):
        from django.http import HttpResponse
        import csv

        plan = get_object_or_404(InstallmentPlan, pk=pk, is_deleted=False)
        schedule = InstallmentEngine.get_schedule(plan)

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="installment_plan_{plan.pk}.csv"'
        writer = csv.writer(response)
        writer.writerow(['رقم القسط', 'تاريخ الاستحقاق', 'المبلغ', 'المدفوع', 'المتبقي', 'الحالة'])
        for inst in schedule:
            writer.writerow([
                inst.installment_number,
                inst.due_date,
                inst.amount,
                inst.paid_amount,
                inst.remaining,
                inst.get_status_display(),
            ])
        return response


# ══════════════════════════════════════════════════════
# إلغاء خطة أقساط
# ══════════════════════════════════════════════════════

class CancelInstallmentPlanView(LoginRequiredMixin, View):
    """إلغاء خطة أقساط (defaulted)"""

    def post(self, request, pk):
        plan = get_object_or_404(InstallmentPlan, pk=pk, is_deleted=False)
        if plan.status == 'active':
            plan.status = 'defaulted'
            plan.updated_by = request.user
            plan.save(update_fields=['status', 'updated_by'])
            messages.warning(request, f'تم تصنيف الخطة كمتعثرة')
        else:
            messages.error(request, 'لا يمكن تغيير حالة هذه الخطة')
        return redirect('installments:plan_detail', pk=pk)
