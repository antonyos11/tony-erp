"""
واجهات تطبيق المصروفات والسندات — RITA ERP
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView

from apps.core.models import Branch
from apps.accounts.models import Account
from apps.expenses.models import (
    Expense, ExpenseCategory, RecurringExpense,
    PaymentVoucher, ReceiptVoucher,
    PettyCash, PettyCashTransaction,
)
from apps.expenses.services.expense_engine import ExpenseEngine, VoucherEngine, PettyCashEngine
from apps.core.mixins import BranchFilterMixin, BranchCreateMixin

try:
    from apps.hr.models import Department, Employee
except ImportError:
    Department = None
    Employee = None

try:
    from apps.partners.models import Supplier
except ImportError:
    Supplier = None

try:
    from apps.sales.models import Customer, SalesInvoice
except ImportError:
    Customer = None
    SalesInvoice = None


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class ExpenseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True, children__isnull=True).order_by('name'),
        label='التصنيف', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    description = forms.CharField(
        label='الوصف', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    is_taxable = forms.BooleanField(
        required=False, label='خاضع للضريبة',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    payment_method = forms.ChoiceField(
        choices=Expense.PAYMENT_METHODS, label='طريقة الدفع',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    receipt_image = forms.ImageField(
        required=False, label='صورة الإيصال',
    )


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = ['name', 'category', 'branch', 'amount', 'frequency',
                  'start_date', 'end_date', 'next_due_date', 'auto_approve', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'auto_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PaymentVoucherForm(forms.Form):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    beneficiary_type = forms.ChoiceField(
        choices=[('supplier', 'مورد'), ('employee', 'موظف'), ('customer', 'عميل'), ('other', 'أخرى')],
        label='نوع المستفيد', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    beneficiary_name = forms.CharField(
        required=False, label='اسم المستفيد',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    amount_in_words = forms.CharField(
        required=False, label='المبلغ كتابةً',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    description = forms.CharField(
        label='البيان', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    payment_method = forms.ChoiceField(
        choices=[('cash', 'نقدي'), ('bank', 'تحويل بنكي'), ('check', 'شيك')],
        label='طريقة الدفع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    debit_account = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('code'),
        label='الحساب المدين', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    credit_account = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('code'),
        label='الحساب الدائن', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class ReceiptVoucherForm(forms.Form):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all().order_by('name'),
        label='الفرع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payer_type = forms.ChoiceField(
        choices=[('customer', 'عميل'), ('other', 'أخرى')],
        label='نوع الدافع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payer_name = forms.CharField(
        required=False, label='اسم الدافع',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    amount_in_words = forms.CharField(
        required=False, label='المبلغ كتابةً',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    description = forms.CharField(
        label='البيان', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    payment_method = forms.ChoiceField(
        choices=[('cash', 'نقدي'), ('bank', 'تحويل بنكي'), ('check', 'شيك')],
        label='طريقة الدفع', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    debit_account = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('code'),
        label='الحساب المدين', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    credit_account = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('code'),
        label='الحساب الدائن', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )


class PettyCashReplenishForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )


class PettyCashSpendForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=15, decimal_places=2, label='المبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    description = forms.CharField(
        label='البيان', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True).order_by('name'),
        required=False, label='التصنيف',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    receipt_image = forms.ImageField(required=False, label='صورة الإيصال')


# ══════════════════════════════════════════════════════
# 1. المصروفات
# ══════════════════════════════════════════════════════

class ExpenseListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'branch', 'approved_by')
        q = self.request.GET.get('q', '')
        category = self.request.GET.get('category', '')
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if q:
            qs = qs.filter(Q(expense_number__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(category_id=category)
        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        ctx['statuses'] = Expense.EXPENSE_STATUSES
        ctx['total_amount'] = self.get_queryset().aggregate(t=Sum('total'))['t'] or 0
        return ctx


class ExpenseCreateView(LoginRequiredMixin, View):
    template_name = 'expenses/expense_form.html'

    def get(self, request):
        form = ExpenseForm()
        return render(request, self.template_name, {'form': form, 'title': 'مصروف جديد'})

    def post(self, request):
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                expense = ExpenseEngine.create_expense(
                    category=form.cleaned_data['category'],
                    branch=form.cleaned_data['branch'],
                    description=form.cleaned_data['description'],
                    amount=form.cleaned_data['amount'],
                    is_taxable=form.cleaned_data.get('is_taxable', False),
                    payment_method=form.cleaned_data['payment_method'],
                    receipt_image=form.cleaned_data.get('receipt_image'),
                    user=request.user,
                )
                if form.cleaned_data.get('notes'):
                    expense.notes = form.cleaned_data['notes']
                    expense.save()
                messages.success(request, f'تم إنشاء المصروف {expense.expense_number} بنجاح')
                return redirect('expenses:expense_detail', pk=expense.pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'form': form, 'title': 'مصروف جديد'})


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.journal_entry:
            ctx['journal_lines'] = self.object.journal_entry.lines.select_related('account')
        return ctx


class ExpenseApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        try:
            ExpenseEngine.approve_and_pay_expense(expense, user=request.user)
            messages.success(request, f'تم اعتماد وصرف المصروف {expense.expense_number}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'خطأ أثناء الاعتماد: {e}')
        return redirect('expenses:expense_detail', pk=pk)


# ══════════════════════════════════════════════════════
# 2. المصروفات الدورية
# ══════════════════════════════════════════════════════

class RecurringExpenseListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = RecurringExpense
    template_name = 'expenses/recurring_list.html'
    context_object_name = 'recurring_expenses'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'branch')


class RecurringExpenseCreateView(LoginRequiredMixin, BranchCreateMixin, CreateView):
    model = RecurringExpense
    form_class = RecurringExpenseForm
    template_name = 'expenses/recurring_form.html'
    success_url = reverse_lazy('expenses:recurring_list')

    def get_success_url(self):
        messages.success(self.request, 'تم إنشاء المصروف الدوري بنجاح')
        return self.success_url


# ══════════════════════════════════════════════════════
# 3. سندات الصرف
# ══════════════════════════════════════════════════════

class PaymentVoucherListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = PaymentVoucher
    template_name = 'expenses/pv_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('branch', 'approved_by')
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(Q(voucher_number__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PaymentVoucher.VOUCHER_STATUSES
        return ctx


class PaymentVoucherCreateView(LoginRequiredMixin, View):
    template_name = 'expenses/pv_form.html'

    def get(self, request):
        form = PaymentVoucherForm()
        return render(request, self.template_name, {'form': form, 'title': 'سند صرف جديد'})

    def post(self, request):
        form = PaymentVoucherForm(request.POST)
        if form.is_valid():
            try:
                voucher = VoucherEngine.create_payment_voucher(
                    branch=form.cleaned_data['branch'],
                    beneficiary_type=form.cleaned_data['beneficiary_type'],
                    amount=form.cleaned_data['amount'],
                    description=form.cleaned_data['description'],
                    debit_account=form.cleaned_data['debit_account'],
                    credit_account=form.cleaned_data['credit_account'],
                    payment_method=form.cleaned_data['payment_method'],
                    beneficiary_name=form.cleaned_data.get('beneficiary_name', ''),
                    user=request.user,
                )
                if form.cleaned_data.get('amount_in_words'):
                    voucher.amount_in_words = form.cleaned_data['amount_in_words']
                if form.cleaned_data.get('notes'):
                    voucher.notes = form.cleaned_data['notes']
                voucher.save()
                messages.success(request, f'تم إنشاء سند الصرف {voucher.voucher_number} بنجاح')
                return redirect('expenses:pv_detail', pk=voucher.pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'form': form, 'title': 'سند صرف جديد'})


class PaymentVoucherDetailView(LoginRequiredMixin, DetailView):
    model = PaymentVoucher
    template_name = 'expenses/pv_detail.html'
    context_object_name = 'voucher'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.journal_entry:
            ctx['journal_lines'] = self.object.journal_entry.lines.select_related('account')
        return ctx


class PaymentVoucherApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        voucher = get_object_or_404(PaymentVoucher, pk=pk)
        try:
            VoucherEngine.approve_payment_voucher(voucher, user=request.user)
            messages.success(request, f'تم اعتماد سند الصرف {voucher.voucher_number}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'خطأ أثناء الاعتماد: {e}')
        return redirect('expenses:pv_detail', pk=pk)


class PaymentVoucherPrintView(LoginRequiredMixin, DetailView):
    model = PaymentVoucher
    template_name = 'expenses/pv_print.html'
    context_object_name = 'voucher'


# ══════════════════════════════════════════════════════
# 4. سندات القبض
# ══════════════════════════════════════════════════════

class ReceiptVoucherListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = ReceiptVoucher
    template_name = 'expenses/rv_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('branch', 'approved_by')
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(Q(voucher_number__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = ReceiptVoucher.VOUCHER_STATUSES
        return ctx


class ReceiptVoucherCreateView(LoginRequiredMixin, View):
    template_name = 'expenses/rv_form.html'

    def get(self, request):
        form = ReceiptVoucherForm()
        return render(request, self.template_name, {'form': form, 'title': 'سند قبض جديد'})

    def post(self, request):
        form = ReceiptVoucherForm(request.POST)
        if form.is_valid():
            try:
                voucher = VoucherEngine.create_receipt_voucher(
                    branch=form.cleaned_data['branch'],
                    payer_type=form.cleaned_data['payer_type'],
                    amount=form.cleaned_data['amount'],
                    description=form.cleaned_data['description'],
                    debit_account=form.cleaned_data['debit_account'],
                    credit_account=form.cleaned_data['credit_account'],
                    payment_method=form.cleaned_data['payment_method'],
                    payer_name=form.cleaned_data.get('payer_name', ''),
                    user=request.user,
                )
                if form.cleaned_data.get('amount_in_words'):
                    voucher.amount_in_words = form.cleaned_data['amount_in_words']
                if form.cleaned_data.get('notes'):
                    voucher.notes = form.cleaned_data['notes']
                voucher.save()
                messages.success(request, f'تم إنشاء سند القبض {voucher.voucher_number} بنجاح')
                return redirect('expenses:rv_detail', pk=voucher.pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'form': form, 'title': 'سند قبض جديد'})


class ReceiptVoucherDetailView(LoginRequiredMixin, DetailView):
    model = ReceiptVoucher
    template_name = 'expenses/rv_detail.html'
    context_object_name = 'voucher'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.journal_entry:
            ctx['journal_lines'] = self.object.journal_entry.lines.select_related('account')
        return ctx


class ReceiptVoucherApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        voucher = get_object_or_404(ReceiptVoucher, pk=pk)
        try:
            VoucherEngine.approve_receipt_voucher(voucher, user=request.user)
            messages.success(request, f'تم اعتماد سند القبض {voucher.voucher_number}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'خطأ أثناء الاعتماد: {e}')
        return redirect('expenses:rv_detail', pk=pk)


class ReceiptVoucherPrintView(LoginRequiredMixin, DetailView):
    model = ReceiptVoucher
    template_name = 'expenses/rv_print.html'
    context_object_name = 'voucher'


# ══════════════════════════════════════════════════════
# 5. العهد النثرية
# ══════════════════════════════════════════════════════

class PettyCashListView(LoginRequiredMixin, BranchFilterMixin, ListView):
    model = PettyCash
    template_name = 'expenses/petty_cash_list.html'
    context_object_name = 'petty_cashes'

    def get_queryset(self):
        return super().get_queryset().select_related('branch', 'custodian', 'account')


class PettyCashDetailView(LoginRequiredMixin, DetailView):
    model = PettyCash
    template_name = 'expenses/petty_cash_detail.html'
    context_object_name = 'petty_cash'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['transactions'] = self.object.transactions.select_related('category').order_by('-date')
        return ctx


class PettyCashReplenishView(LoginRequiredMixin, View):
    template_name = 'expenses/petty_cash_replenish.html'

    def get(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        form = PettyCashReplenishForm()
        return render(request, self.template_name, {'petty_cash': petty_cash, 'form': form})

    def post(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        form = PettyCashReplenishForm(request.POST)
        if form.is_valid():
            try:
                PettyCashEngine.replenish(
                    petty_cash=petty_cash,
                    amount=form.cleaned_data['amount'],
                    user=request.user,
                )
                messages.success(request, f'تم تعبئة العهدة بمبلغ {form.cleaned_data["amount"]}')
                return redirect('expenses:petty_cash_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'petty_cash': petty_cash, 'form': form})


class PettyCashSpendView(LoginRequiredMixin, View):
    template_name = 'expenses/petty_cash_spend.html'

    def get(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        form = PettyCashSpendForm()
        return render(request, self.template_name, {'petty_cash': petty_cash, 'form': form})

    def post(self, request, pk):
        petty_cash = get_object_or_404(PettyCash, pk=pk)
        form = PettyCashSpendForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                PettyCashEngine.spend(
                    petty_cash=petty_cash,
                    amount=form.cleaned_data['amount'],
                    description=form.cleaned_data['description'],
                    category=form.cleaned_data.get('category'),
                    receipt_image=form.cleaned_data.get('receipt_image'),
                    user=request.user,
                )
                messages.success(request, f'تم الصرف من العهدة بمبلغ {form.cleaned_data["amount"]}')
                return redirect('expenses:petty_cash_detail', pk=pk)
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'خطأ: {e}')
        return render(request, self.template_name, {'petty_cash': petty_cash, 'form': form})


# ══════════════════════════════════════════════════════
# 6. تقرير الميزانية vs الفعلي
# ══════════════════════════════════════════════════════

class ExpenseBudgetView(LoginRequiredMixin, TemplateView):
    template_name = 'expenses/budget_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))

        categories = ExpenseCategory.objects.filter(
            is_active=True, parent__isnull=False
        ).select_related('parent')

        report = []
        total_budget = Decimal('0')
        total_actual = Decimal('0')

        for cat in categories:
            actual = Expense.objects.filter(
                category=cat,
                date__year=year,
                date__month=month,
                status__in=['approved', 'paid'],
            ).aggregate(s=Sum('total'))['s'] or Decimal('0')

            budget = cat.budget_monthly
            variance = budget - actual
            pct = (actual / budget * 100) if budget > 0 else 0

            report.append({
                'category': cat,
                'budget': budget,
                'actual': actual,
                'variance': variance,
                'pct': round(pct, 1),
                'over_budget': actual > budget and budget > 0,
            })

            total_budget += budget
            total_actual += actual

        ctx.update({
            'report': report,
            'total_budget': total_budget,
            'total_actual': total_actual,
            'total_variance': total_budget - total_actual,
            'year': year,
            'month': month,
            'months': list(range(1, 13)),
            'years': list(range(today.year - 2, today.year + 2)),
        })
        return ctx


# ══════════════════════════════════════════════════════
# Sprint 22C — تصنيفات المصروفات CRUD
# ══════════════════════════════════════════════════════

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'parent', 'account', 'budget_monthly', 'is_active']
        widgets = {
            'name':           forms.TextInput(attrs={'class': 'form-control'}),
            'parent':         forms.Select(attrs={'class': 'form-select'}),
            'account':        forms.Select(attrs={'class': 'form-select'}),
            'budget_monthly': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    """قائمة تصنيفات المصروفات"""
    model = ExpenseCategory
    template_name = 'expenses/expense_category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return ExpenseCategory.objects.select_related('parent', 'account').order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تصنيفات المصروفات'
        ctx['root_categories'] = ExpenseCategory.objects.filter(
            parent__isnull=True
        ).prefetch_related('children').order_by('name')
        return ctx


class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    """إنشاء تصنيف مصروف جديد"""
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/expense_category_form.html'
    success_url = reverse_lazy('expenses:expense_category_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تصنيف مصروف جديد'
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        parent_id = self.request.GET.get('parent')
        if parent_id:
            initial['parent'] = parent_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'تم إنشاء تصنيف "{form.instance.name}"')
        return super().form_valid(form)


class ExpenseCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """تعديل تصنيف مصروف"""
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/expense_category_form.html'
    success_url = reverse_lazy('expenses:expense_category_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل: {self.object.name}'
        ctx['edit_mode'] = True
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'تم تحديث تصنيف "{form.instance.name}"')
        return super().form_valid(form)
