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
from apps.core.mixins import apply_branch_filter, BranchCreateMixin


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
        qs = apply_branch_filter(qs, self.request)
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


# ══════════════════════════════════════════════════════
# تعديل واعتماد القيود (Sprint 20)
# ══════════════════════════════════════════════════════

from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.views import View


class JournalEditView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تعديل قيد في حالة مسودة"""
    permission_module = 'accounts'
    permission_action = 'edit'

    def get(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status != 'draft':
            messages.error(request, 'لا يمكن تعديل قيد إلا في حالة المسودة.')
            return redirect('accounts:journal_detail', pk=pk)
        lines = entry.lines.select_related('account').all()
        return render(request, 'accounts/journal_edit.html', {
            'title': f'تعديل قيد: {entry.entry_number}',
            'entry': entry,
            'lines': lines,
        })

    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status != 'draft':
            messages.error(request, 'لا يمكن تعديل قيد إلا في حالة المسودة.')
            return redirect('accounts:journal_detail', pk=pk)

        description = request.POST.get('description', entry.description)
        entry.description = description
        entry.save()
        messages.success(request, f'تم تحديث القيد {entry.entry_number}')
        return redirect('accounts:journal_detail', pk=pk)


class JournalCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إلغاء قيد محاسبي (تغيير الحالة لـ cancelled)"""
    permission_module = 'accounts'
    permission_action = 'approve'

    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status == 'posted':
            messages.error(request, 'لا يمكن إلغاء قيد مرحّل.')
            return redirect('accounts:journal_detail', pk=pk)
        entry.status = 'cancelled'
        entry.save()
        messages.success(request, f'تم إلغاء القيد {entry.entry_number}')
        return redirect('accounts:journal_list')


class JournalPostView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """ترحيل (اعتماد) قيد يدوي"""
    permission_module = 'accounts'
    permission_action = 'approve'

    def post(self, request, pk):
        entry = get_object_or_404(JournalEntry, pk=pk)
        if entry.status != 'draft':
            messages.error(request, 'لا يمكن ترحيل قيد إلا في حالة المسودة.')
            return redirect('accounts:journal_detail', pk=pk)

        # التحقق من التوازن
        from decimal import Decimal
        from django.db.models import Sum
        totals = entry.lines.aggregate(d=Sum('debit'), c=Sum('credit'))
        total_debit = totals['d'] or Decimal('0')
        total_credit = totals['c'] or Decimal('0')

        if abs(total_debit - total_credit) > Decimal('0.01'):
            messages.error(request, f'القيد غير متوازن: مدين={total_debit}, دائن={total_credit}')
            return redirect('accounts:journal_detail', pk=pk)

        entry.status = 'posted'
        entry.posted_by = request.user
        entry.posted_at = timezone.now()
        entry.save()
        messages.success(request, f'تم ترحيل القيد {entry.entry_number} بنجاح')
        return redirect('accounts:journal_detail', pk=pk)


# ══════════════════════════════════════════════════════
# Sprint 22B — مراكز التكلفة
# ══════════════════════════════════════════════════════

from apps.accounts.models import CostCenter


class CostCenterListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة مراكز التكلفة"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/cost_center_list.html'
    model = CostCenter
    context_object_name = 'cost_centers'
    ordering = ['code']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'مراكز التكلفة'
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 22B — WIP (إنتاج تحت التشغيل)
# ══════════════════════════════════════════════════════

from apps.accounts.models import WIPAccount
from apps.accounts.services.manufacturing_cost_engine import ManufacturingCostEngine
from django.views.generic import View
from django.shortcuts import get_object_or_404


class WIPSummaryView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """ملخص WIP — كل الأوامر المفتوحة + إجمالي القيمة"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/wip_summary.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        summary = ManufacturingCostEngine.get_wip_summary()
        ctx.update(summary)
        ctx['title'] = 'إنتاج تحت التشغيل (WIP)'
        return ctx


class ProductionCostDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """تفصيل تكلفة أمر إنتاج"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/production_cost_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.production.models import ProductionOrder
        order = get_object_or_404(ProductionOrder, pk=self.kwargs['pk'])
        report = ManufacturingCostEngine.get_production_cost_report(order)
        ctx.update(report)
        ctx['title'] = f'تكلفة أمر الإنتاج {order.order_number}'
        # بيانات Chart.js
        import json
        ctx['cost_chart_data'] = json.dumps({
            'labels': ['خامات', 'عمالة', 'تكاليف غير مباشرة'],
            'values': [
                float(report['material_cost']),
                float(report['labor_cost']),
                float(report['overhead_cost']),
            ],
        })
        return ctx


class UnitCostComparisonView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """مقارنة تكلفة الوحدة عبر الأوامر"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/unit_cost_comparison.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.inventory.models import Product
        import json
        product = get_object_or_404(Product, pk=self.kwargs['product_id'])
        comparison = ManufacturingCostEngine.get_unit_cost_comparison(product)
        ctx['product'] = product
        ctx['comparison'] = comparison
        ctx['title'] = f'تطور تكلفة الوحدة — {product.name}'
        ctx['chart_data'] = json.dumps({
            'labels': [str(r['order_number']) for r in comparison],
            'values': [float(r['unit_cost']) for r in comparison],
        })
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 22B — الميزانيات
# ══════════════════════════════════════════════════════

from apps.accounts.models import Budget, BudgetLine, FiscalYear
from apps.accounts.services.budget_engine import BudgetEngine
from django.views.generic import UpdateView
from django.contrib import messages
import json as _json


class BudgetListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """قائمة الميزانيات"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/budget_list.html'
    model = Budget
    context_object_name = 'budgets'
    ordering = ['-fiscal_year__start_date', 'name']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'الميزانيات'
        return ctx


class BudgetCreateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """إنشاء ميزانية"""
    permission_module = 'accounts'
    permission_action = 'create'
    template_name = 'accounts/budget_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إنشاء ميزانية جديدة'
        ctx['fiscal_years'] = FiscalYear.objects.filter(is_closed=False)
        ctx['accounts'] = Account.objects.filter(is_detail=True, is_active=True).order_by('code')
        ctx['branches'] = Branch.objects.filter(is_active=True)
        ctx['cost_centers'] = CostCenter.objects.filter(is_active=True)
        ctx['is_edit'] = False
        from apps.expenses.models import ExpenseCategory
        ctx['categories'] = ExpenseCategory.objects.filter(is_active=True)
        return ctx

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        fiscal_year_id = request.POST.get('fiscal_year')
        period_type = request.POST.get('period_type', 'monthly')
        branch_id = request.POST.get('branch')
        cost_center_id = request.POST.get('cost_center')
        notes = request.POST.get('notes', '')

        if not name or not fiscal_year_id:
            messages.error(request, 'يرجى تعبئة الاسم والسنة المالية.')
            return redirect('accounts:budget_create')

        try:
            fiscal_year = FiscalYear.objects.get(pk=fiscal_year_id)
        except FiscalYear.DoesNotExist:
            messages.error(request, 'السنة المالية غير موجودة.')
            return redirect('accounts:budget_create')

        budget = Budget.objects.create(
            name=name,
            fiscal_year=fiscal_year,
            period_type=period_type,
            branch_id=branch_id if branch_id else None,
            cost_center_id=cost_center_id if cost_center_id else None,
            notes=notes,
            created_by=request.user, updated_by=request.user,
        )
        messages.success(request, f'تم إنشاء الميزانية "{budget.name}" بنجاح.')
        return redirect('accounts:budget_detail', pk=budget.pk)


class BudgetDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """تفاصيل ميزانية"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/budget_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        budget = get_object_or_404(Budget, pk=self.kwargs['pk'])
        ctx['budget'] = budget
        ctx['lines'] = budget.lines.select_related('account', 'expense_category').order_by('account__code')
        ctx['title'] = f'ميزانية: {budget.name}'
        return ctx


class BudgetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """تعديل ميزانية (مسودة فقط)"""
    permission_module = 'accounts'
    permission_action = 'edit'
    template_name = 'accounts/budget_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        budget = get_object_or_404(Budget, pk=self.kwargs['pk'])
        if budget.status != 'draft':
            ctx['error'] = 'لا يمكن تعديل ميزانية معتمدة أو مغلقة.'
        ctx['budget'] = budget
        ctx['title'] = f'تعديل ميزانية: {budget.name}'
        ctx['fiscal_years'] = FiscalYear.objects.filter(is_closed=False)
        ctx['accounts'] = Account.objects.filter(is_detail=True, is_active=True).order_by('code')
        ctx['branches'] = Branch.objects.filter(is_active=True)
        ctx['cost_centers'] = CostCenter.objects.filter(is_active=True)
        ctx['is_edit'] = True
        from apps.expenses.models import ExpenseCategory
        ctx['categories'] = ExpenseCategory.objects.filter(is_active=True)
        return ctx

    def post(self, request, pk, *args, **kwargs):
        budget = get_object_or_404(Budget, pk=pk)
        if budget.status != 'draft':
            messages.error(request, 'لا يمكن تعديل ميزانية معتمدة.')
            return redirect('accounts:budget_detail', pk=pk)

        # تحديث بيانات الميزانية
        budget.name = request.POST.get('name', budget.name)
        budget.notes = request.POST.get('notes', budget.notes)
        budget.updated_by = request.user
        budget.save()
        messages.success(request, 'تم تحديث الميزانية بنجاح.')
        return redirect('accounts:budget_detail', pk=pk)


class BudgetApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """اعتماد الميزانية"""
    permission_module = 'accounts'
    permission_action = 'approve'

    def post(self, request, pk, *args, **kwargs):
        budget = get_object_or_404(Budget, pk=pk)
        if budget.status != 'draft':
            messages.error(request, 'يمكن اعتماد مسودات فقط.')
            return redirect('accounts:budget_detail', pk=pk)
        budget.status = 'approved'
        budget.approved_by = request.user
        budget.updated_by = request.user
        budget.save()
        messages.success(request, f'تم اعتماد الميزانية "{budget.name}" بنجاح.')
        return redirect('accounts:budget_detail', pk=pk)


class BudgetVsActualView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """تقرير Budget vs Actual"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/budget_vs_actual.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        budget = get_object_or_404(Budget, pk=self.kwargs['pk'])
        month_param = self.request.GET.get('month')
        month = int(month_param) if month_param else timezone.now().month
        report = BudgetEngine.get_budget_vs_actual(budget.pk, month)
        ctx.update(report)
        ctx['title'] = f'ميزانية مقابل فعلي — {budget.name}'
        ctx['months_range'] = range(1, 13)
        ctx['selected_month'] = month
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 22B — ربحية مراكز التكلفة
# ══════════════════════════════════════════════════════


class CostCenterProfitabilityView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """ربحية كل مركز تكلفة"""
    permission_module = 'accounts'
    permission_action = 'view'
    template_name = 'accounts/cost_center_profitability.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Sum
        from apps.accounts.models import JournalLine

        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        from datetime import date
        if start_date:
            from datetime import datetime
            start_date = date.fromisoformat(start_date)
        else:
            start_date = date.today().replace(day=1)
        if end_date:
            from datetime import datetime
            end_date = date.fromisoformat(end_date)
        else:
            end_date = date.today()

        cost_centers = CostCenter.objects.filter(is_active=True)
        data = []
        for cc in cost_centers:
            qs = JournalLine.objects.filter(
                cost_center=cc,
                entry__date__gte=start_date,
                entry__date__lte=end_date,
                entry__status='posted',
            )
            totals = qs.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
            total_debit = totals['total_debit'] or 0
            total_credit = totals['total_credit'] or 0
            data.append({
                'cost_center': cc,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'net': total_credit - total_debit,
            })

        data.sort(key=lambda x: x['net'], reverse=True)
        ctx['data'] = data
        ctx['start_date'] = start_date
        ctx['end_date'] = end_date
        ctx['title'] = 'ربحية مراكز التكلفة'
        return ctx
