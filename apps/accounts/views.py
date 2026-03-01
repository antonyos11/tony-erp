"""
واجهات تطبيق المحاسبة — RITA ERP
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, TemplateView,
)
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django import forms
from django.utils import timezone

from apps.accounts.models import (
    Account, JournalEntry, JournalLine, FiscalYear,
)
from apps.accounts.services.financial_reports import FinancialReports
from apps.authorization.decorators import PermissionRequiredMixin
from apps.core.models import Branch


# ══════════════════════════════════════════════════════
# دليل الحسابات
# ══════════════════════════════════════════════════════

class ChartOfAccountsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """عرض شجرة دليل الحسابات"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/chart_of_accounts.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # الحسابات الجذرية (بدون أب)
        ctx['root_accounts'] = Account.objects.filter(
            parent__isnull=True, is_active=True
        ).order_by('code')
        # كل الحسابات لعمل الشجرة في الـ template
        ctx['all_accounts'] = Account.objects.filter(
            is_active=True
        ).order_by('code').select_related('parent')
        ctx['title'] = 'دليل الحسابات'
        return ctx


# ══════════════════════════════════════════════════════
# فورم إضافة حساب
# ══════════════════════════════════════════════════════

class AccountForm(forms.ModelForm):
    """فورم إنشاء حساب"""

    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'nature', 'parent', 'is_detail']
        widgets = {
            'code':         forms.TextInput(attrs={'class': 'form-control'}),
            'name':         forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'nature':       forms.Select(attrs={'class': 'form-select'}),
            'parent':       forms.Select(attrs={'class': 'form-select'}),
            'is_detail':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'code':         'كود الحساب',
            'name':         'اسم الحساب',
            'account_type': 'نوع الحساب',
            'nature':       'طبيعة الحساب',
            'parent':       'الحساب الأب',
            'is_detail':    'حساب تفصيلي (يمكن القيد عليه)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Account.objects.filter(
            is_active=True
        ).order_by('code')
        self.fields['parent'].empty_label = '--- بدون أب (حساب جذري) ---'
        self.fields['parent'].required = False


class AccountCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """إضافة حساب جديد"""
    permission_module = 'accounts'
    permission_action = 'create'
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('accounts:chart_of_accounts')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إضافة حساب جديد'
        return ctx


# ══════════════════════════════════════════════════════
# قيود اليومية
# ══════════════════════════════════════════════════════

class JournalEntryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة القيود المحاسبية"""
    permission_module = 'accounts'
    permission_action = 'view'
    model = JournalEntry
    template_name = 'accounts/journal_list.html'
    context_object_name = 'entries'
    paginate_by = 20
    ordering = ['-date', '-entry_number']

    def get_queryset(self):
        qs = JournalEntry.objects.select_related('branch', 'fiscal_year').order_by('-date', '-entry_number')
        date_from = self.request.GET.get('date_from')
        date_to   = self.request.GET.get('date_to')
        source    = self.request.GET.get('source')
        status    = self.request.GET.get('status')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if source:
            qs = qs.filter(source=source)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title']          = 'القيود المحاسبية'
        ctx['source_choices'] = JournalEntry.SOURCE_CHOICES
        ctx['status_choices'] = JournalEntry.STATUS_CHOICES
        ctx['filter_params']  = self.request.GET.dict()
        return ctx


class JournalEntryDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """تفاصيل قيد محاسبي"""
    permission_module = 'accounts'
    permission_action = 'view'
    model = JournalEntry
    template_name = 'accounts/journal_detail.html'
    context_object_name = 'entry'

    def get_queryset(self):
        return JournalEntry.objects.select_related(
            'branch', 'fiscal_year', 'created_by'
        ).prefetch_related('lines__account', 'lines__cost_center')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'قيد رقم {self.object.entry_number}'
        return ctx


# ══════════════════════════════════════════════════════
# فورم القيد اليدوي
# ══════════════════════════════════════════════════════

class JournalEntryForm(forms.ModelForm):
    """فورم القيد اليدوي"""

    class Meta:
        model = JournalEntry
        fields = ['date', 'description', 'branch']
        widgets = {
            'date':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'branch':      forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'date':        'تاريخ القيد',
            'description': 'البيان',
            'branch':      'الفرع',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['branch'].empty_label = '--- اختر الفرع ---'
        self.fields['branch'].required = False
        self.fields['date'].initial = timezone.now().date()


class JournalEntryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """إنشاء قيد يدوي"""
    permission_module = 'accounts'
    permission_action = 'create'
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'accounts/journal_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'قيد يدوي جديد'
        ctx['detail_accounts'] = Account.objects.filter(
            is_detail=True, is_active=True
        ).order_by('code').values('id', 'code', 'name')
        return ctx

    def form_valid(self, form):
        from decimal import Decimal
        from apps.accounts.services.journal_engine import JournalEngine

        lines_data = []
        post = self.request.POST
        i = 0
        while f'account_id_{i}' in post:
            account_id = post.get(f'account_id_{i}', '').strip()
            debit_val  = post.get(f'debit_{i}', '0').strip() or '0'
            credit_val = post.get(f'credit_{i}', '0').strip() or '0'
            desc_val   = post.get(f'line_desc_{i}', '').strip()
            if account_id:
                try:
                    acc = Account.objects.get(pk=account_id)
                    lines_data.append({
                        'account_code': acc.code,
                        'debit':        Decimal(debit_val),
                        'credit':       Decimal(credit_val),
                        'description':  desc_val,
                    })
                except (Account.DoesNotExist, Exception):
                    pass
            i += 1

        if not lines_data:
            form.add_error(None, 'يجب إدخال سطور القيد')
            return self.form_invalid(form)

        try:
            entry = JournalEngine.create_entry(
                source='manual',
                description=form.cleaned_data['description'],
                branch=form.cleaned_data.get('branch'),
                lines_data=lines_data,
                user=self.request.user,
                auto_post=False,
            )
            return redirect('accounts:journal_detail', pk=entry.pk)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


# ══════════════════════════════════════════════════════
# التقارير المالية
# ══════════════════════════════════════════════════════

class TrialBalanceView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """ميزان المراجعة"""
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'accounts/trial_balance.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'ميزان المراجعة'
        start_date = self.request.GET.get('start_date')
        end_date   = self.request.GET.get('end_date')
        branch_id  = self.request.GET.get('branch')
        branch     = None
        if branch_id:
            try:
                branch = Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                pass
        if start_date or end_date:
            ctx['report'] = FinancialReports.trial_balance(
                start_date=start_date or None,
                end_date=end_date or None,
                branch=branch,
            )
        ctx['branches']   = Branch.objects.filter(is_active=True)
        ctx['start_date'] = start_date
        ctx['end_date']   = end_date
        ctx['branch_id']  = branch_id
        return ctx


class IncomeStatementView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """قائمة الدخل"""
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'accounts/income_statement.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'قائمة الدخل'
        start_date = self.request.GET.get('start_date')
        end_date   = self.request.GET.get('end_date')
        branch_id  = self.request.GET.get('branch')
        branch     = None
        if branch_id:
            try:
                branch = Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                pass
        if start_date and end_date:
            ctx['report'] = FinancialReports.income_statement(
                start_date=start_date,
                end_date=end_date,
                branch=branch,
            )
        ctx['branches']   = Branch.objects.filter(is_active=True)
        ctx['start_date'] = start_date
        ctx['end_date']   = end_date
        ctx['branch_id']  = branch_id
        return ctx


class BalanceSheetView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """المركز المالي"""
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'accounts/balance_sheet.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'قائمة المركز المالي'
        as_of_date = self.request.GET.get('date')
        branch_id  = self.request.GET.get('branch')
        branch     = None
        if branch_id:
            try:
                branch = Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                pass
        if as_of_date:
            ctx['report'] = FinancialReports.balance_sheet(date=as_of_date, branch=branch)
        ctx['branches']   = Branch.objects.filter(is_active=True)
        ctx['as_of_date'] = as_of_date
        ctx['branch_id']  = branch_id
        return ctx


class AccountStatementView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """كشف حساب تفصيلي"""
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'accounts/account_statement.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'كشف حساب'
        account_code = self.request.GET.get('account_code')
        start_date   = self.request.GET.get('start_date')
        end_date     = self.request.GET.get('end_date')
        if account_code:
            try:
                ctx['report'] = FinancialReports.account_statement(
                    account_code=account_code,
                    start_date=start_date or None,
                    end_date=end_date or None,
                )
            except Account.DoesNotExist:
                ctx['error'] = f'الحساب {account_code} غير موجود'
        ctx['detail_accounts'] = Account.objects.filter(
            is_detail=True, is_active=True
        ).order_by('code')
        ctx['account_code'] = account_code
        ctx['start_date']   = start_date
        ctx['end_date']     = end_date
        return ctx


# ══════════════════════════════════════════════════════
# السنوات المالية
# ══════════════════════════════════════════════════════

class FiscalYearForm(forms.ModelForm):
    """فورم السنة المالية"""

    class Meta:
        model = FiscalYear
        fields = ['name', 'start_date', 'end_date', 'is_active']
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name':       'اسم السنة المالية',
            'start_date': 'تاريخ البداية',
            'end_date':   'تاريخ النهاية',
            'is_active':  'نشطة',
        }


class FiscalYearListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة السنوات المالية"""
    permission_module = 'accounts'
    permission_action = 'view'
    model = FiscalYear
    template_name = 'accounts/fiscal_year_list.html'
    context_object_name = 'fiscal_years'
    ordering = ['-start_date']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'السنوات المالية'
        ctx['form']  = FiscalYearForm()
        return ctx

    def post(self, request, *args, **kwargs):
        """إنشاء سنة مالية جديدة"""
        form = FiscalYearForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:fiscal_year_list')
        qs = self.get_queryset()
        return self.render_to_response(self.get_context_data(
            object_list=qs,
            form=form,
        ))
