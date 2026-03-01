"""
واجهات تطبيق الخزينة والبنوك — RITA ERP
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, View, TemplateView

from apps.treasury.models import BankAccount, CashBox, Check, MoneyTransfer
from apps.treasury.services.treasury_engine import TreasuryEngine
from apps.treasury.services.check_engine import CheckEngine
from apps.core.models import Branch


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['name', 'account_number', 'branch', 'account', 'is_active']
        widgets = {
            'name':           forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'branch':         forms.Select(attrs={'class': 'form-select'}),
            'account':        forms.Select(attrs={'class': 'form-select'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CashBoxForm(forms.ModelForm):
    class Meta:
        model = CashBox
        fields = ['name', 'branch', 'account', 'responsible']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'branch':      forms.Select(attrs={'class': 'form-select'}),
            'account':     forms.Select(attrs={'class': 'form-select'}),
            'responsible': forms.Select(attrs={'class': 'form-select'}),
        }


class CheckForm(forms.ModelForm):
    class Meta:
        model = Check
        fields = [
            'check_number', 'check_type', 'bank',
            'amount', 'issue_date', 'due_date', 'partner_name', 'notes',
        ]
        widgets = {
            'check_number': forms.TextInput(attrs={'class': 'form-control'}),
            'check_type':   forms.Select(attrs={'class': 'form-select'}),
            'bank':         forms.Select(attrs={'class': 'form-select'}),
            'amount':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'issue_date':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'partner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'notes':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MoneyTransferForm(forms.ModelForm):
    class Meta:
        model = MoneyTransfer
        fields = [
            'from_account_type', 'from_cash', 'from_bank',
            'to_account_type', 'to_cash', 'to_bank',
            'amount', 'date', 'notes',
        ]
        widgets = {
            'from_account_type': forms.Select(attrs={'class': 'form-select'}),
            'from_cash':         forms.Select(attrs={'class': 'form-select'}),
            'from_bank':         forms.Select(attrs={'class': 'form-select'}),
            'to_account_type':   forms.Select(attrs={'class': 'form-select'}),
            'to_cash':           forms.Select(attrs={'class': 'form-select'}),
            'to_bank':           forms.Select(attrs={'class': 'form-select'}),
            'amount':            forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date':              forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes':             forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ══════════════════════════════════════════════════════
# Bank Account Views
# ══════════════════════════════════════════════════════

class BankAccountListView(LoginRequiredMixin, ListView):
    model = BankAccount
    template_name = 'treasury/bank_account_list.html'
    context_object_name = 'bank_accounts'

    def get_queryset(self):
        return BankAccount.objects.filter(is_deleted=False).select_related('branch', 'account')


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'treasury/bank_account_form.html'
    success_url = reverse_lazy('treasury:bank_account_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم إضافة الحساب البنكي بنجاح')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# CashBox Views
# ══════════════════════════════════════════════════════

class CashBoxListView(LoginRequiredMixin, ListView):
    model = CashBox
    template_name = 'treasury/cashbox_list.html'
    context_object_name = 'cashboxes'

    def get_queryset(self):
        return CashBox.objects.filter(is_deleted=False).select_related('branch', 'account', 'responsible')


class CashBoxCreateView(LoginRequiredMixin, CreateView):
    model = CashBox
    form_class = CashBoxForm
    template_name = 'treasury/cashbox_form.html'
    success_url = reverse_lazy('treasury:cashbox_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم إضافة الخزنة بنجاح')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# Check Views
# ══════════════════════════════════════════════════════

class CheckListView(LoginRequiredMixin, ListView):
    model = Check
    template_name = 'treasury/check_list.html'
    context_object_name = 'checks'

    def get_queryset(self):
        qs = Check.objects.filter(is_deleted=False).select_related('bank')
        check_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        if check_type:
            qs = qs.filter(check_type=check_type)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['check_types'] = Check.CHECK_TYPES
        ctx['check_statuses'] = Check.CHECK_STATUSES
        return ctx


class CheckCreateView(LoginRequiredMixin, CreateView):
    model = Check
    form_class = CheckForm
    template_name = 'treasury/check_form.html'
    success_url = reverse_lazy('treasury:check_list')

    def form_valid(self, form):
        check = form.save(commit=False)
        check.created_by = self.request.user
        check.updated_by = self.request.user
        check.save()
        messages.success(self.request, f'تم إنشاء الشيك {check.check_number} بنجاح')
        return redirect(self.success_url)


class CheckActionView(LoginRequiredMixin, View):
    """إيداع / تحصيل / ارتجاع / إلغاء شيك"""

    def post(self, request, pk, action):
        check = get_object_or_404(Check, pk=pk, is_deleted=False)
        branch = getattr(request.user, 'branch', None)

        try:
            if action == 'deposit':
                CheckEngine.deposit_check(check, branch=branch, user=request.user)
                messages.success(request, f'تم إيداع الشيك {check.check_number}')
            elif action == 'clear':
                CheckEngine.clear_check(check, branch=branch, user=request.user)
                messages.success(request, f'تم تحصيل الشيك {check.check_number}')
            elif action == 'bounce':
                notes = request.POST.get('notes', '')
                CheckEngine.bounce_check(check, branch=branch, notes=notes, user=request.user)
                messages.warning(request, f'تم تسجيل ارتجاع الشيك {check.check_number}')
            elif action == 'cancel':
                CheckEngine.cancel_check(check, user=request.user)
                messages.warning(request, f'تم إلغاء الشيك {check.check_number}')
            else:
                messages.error(request, 'إجراء غير معروف')
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('treasury:check_list')


# ══════════════════════════════════════════════════════
# Money Transfer Views
# ══════════════════════════════════════════════════════

class MoneyTransferListView(LoginRequiredMixin, ListView):
    model = MoneyTransfer
    template_name = 'treasury/transfer_list.html'
    context_object_name = 'transfers'

    def get_queryset(self):
        return MoneyTransfer.objects.filter(is_deleted=False).select_related(
            'from_cash', 'from_bank', 'to_cash', 'to_bank',
        )


class MoneyTransferCreateView(LoginRequiredMixin, View):
    template_name = 'treasury/transfer_form.html'

    def _get_context(self):
        return {
            'bank_accounts': BankAccount.objects.filter(is_active=True, is_deleted=False),
            'cashboxes':     CashBox.objects.filter(is_deleted=False),
        }

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, self._get_context())

    def post(self, request):
        from django.shortcuts import render
        from_type = request.POST.get('from_account_type')
        to_type   = request.POST.get('to_account_type')
        amount    = request.POST.get('amount', 0)
        notes     = request.POST.get('notes', '')
        branch    = getattr(request.user, 'branch', None)

        try:
            # جلب مصدر التحويل
            if from_type == 'cash':
                from_obj = get_object_or_404(CashBox, pk=request.POST.get('from_cash'))
            else:
                from_obj = get_object_or_404(BankAccount, pk=request.POST.get('from_bank'))

            # جلب وجهة التحويل
            if to_type == 'cash':
                to_obj = get_object_or_404(CashBox, pk=request.POST.get('to_cash'))
            else:
                to_obj = get_object_or_404(BankAccount, pk=request.POST.get('to_bank'))

            TreasuryEngine.transfer(
                from_obj=from_obj, from_type=from_type,
                to_obj=to_obj,   to_type=to_type,
                amount=amount, notes=notes, branch=branch, user=request.user,
            )
            messages.success(request, f'تم التحويل بمبلغ {amount} بنجاح')
            return redirect('treasury:transfer_list')
        except (ValueError, Exception) as e:
            messages.error(request, str(e))
            return render(request, self.template_name, self._get_context())


# ══════════════════════════════════════════════════════
# Bank Reconciliation View
# ══════════════════════════════════════════════════════

class BankReconciliationView(LoginRequiredMixin, TemplateView):
    template_name = 'treasury/bank_reconciliation.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        bank_id = self.request.GET.get('bank_id')
        ctx['bank_accounts'] = BankAccount.objects.filter(is_active=True, is_deleted=False)

        if bank_id:
            bank = get_object_or_404(BankAccount, pk=bank_id)
            ctx['selected_bank'] = bank
            ctx['checks'] = Check.objects.filter(
                bank=bank, is_deleted=False,
            ).order_by('-due_date')
            ctx['transfers_in']  = MoneyTransfer.objects.filter(to_bank=bank,   is_deleted=False)
            ctx['transfers_out'] = MoneyTransfer.objects.filter(from_bank=bank, is_deleted=False)

        return ctx
