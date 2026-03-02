"""
Views التطبيق الأساسي — RITA ERP
"""
import json
from decimal import Decimal
from datetime import timedelta, date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, F, Count
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    TemplateView, ListView, CreateView, DetailView, UpdateView,
)

from apps.core.models import Branch, Warehouse, User, Company
from apps.core.mixins import BranchFilterMixin, BranchCreateMixin, AdminRequiredMixin


# ══════════════════════════════════════════════════════
# Switch Branch
# ══════════════════════════════════════════════════════

@login_required
def switch_branch(request):
    """تغيير الفرع النشط (للـ Admin ومن لديهم صلاحية)"""
    if not (request.user.is_superuser or request.user.is_staff
            or getattr(request, 'can_see_all_branches', False)):
        messages.error(request, 'ليس لديك صلاحية تغيير الفرع.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    branch_param = request.GET.get('branch', '')

    if branch_param == 'all':
        request.session.pop('active_branch_id', None)
        messages.success(request, 'تم التبديل إلى عرض كل الفروع.')
    else:
        try:
            branch_id = int(branch_param)
            branch = get_object_or_404(Branch, id=branch_id, is_active=True)
            request.session['active_branch_id'] = branch_id
            messages.success(request, f'تم التبديل إلى فرع: {branch.name}')
        except (ValueError, TypeError):
            messages.error(request, 'فرع غير صالح.')

    return redirect(request.META.get('HTTP_REFERER', '/'))


# ══════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════

class DashboardView(LoginRequiredMixin, TemplateView):
    """لوحة التحكم الرئيسية — بيانات مفلترة حسب الفرع"""
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'لوحة التحكم'

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # ---- lazy imports ----
        from apps.sales.models import SalesInvoice, SalesInvoiceLine, Customer
        from apps.inventory.models import StockLevel, Product
        from apps.inventory.services.valuation import InventoryValuation
        from apps.production.models import ProductionOrder
        from apps.accounts.models import Account, JournalLine

        # فلترة حسب الفرع الحالي
        branch = getattr(self.request, 'current_branch', None)

        invoice_filter = {}
        stock_filter = {}
        if branch:
            invoice_filter['branch'] = branch
            stock_filter['warehouse__branch'] = branch

        # ===== 1. بطاقات KPIs =====
        sales_today = SalesInvoice.objects.filter(
            date__gte=today_start,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            **invoice_filter,
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        sales_month = SalesInvoice.objects.filter(
            date__gte=month_start,
            status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            **invoice_filter,
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

        inv_prefix = {'invoice__' + k: v for k, v in invoice_filter.items()}

        profit_month = SalesInvoiceLine.objects.filter(
            invoice__date__gte=month_start,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            **inv_prefix,
        ).aggregate(total=Sum('profit'))['total'] or Decimal('0')

        cost_month = SalesInvoiceLine.objects.filter(
            invoice__date__gte=month_start,
            invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            **inv_prefix,
        ).aggregate(
            revenue=Sum('subtotal'),
            cost=Sum(F('cost_price') * F('quantity')),
        )
        revenue_val = cost_month['revenue'] or Decimal('0')
        profit_margin = (
            (profit_month / revenue_val * 100).quantize(Decimal('0.1'))
            if revenue_val > 0 else Decimal('0')
        )

        invoices_today = SalesInvoice.objects.filter(
            date__gte=today_start, **invoice_filter
        ).count()

        # رصيد الخزينة
        cash_balance = Decimal('0')
        cash_qs = Account.objects.filter(
            Q(code__startswith='1101') | Q(name__icontains='خزينة') | Q(name__icontains='صندوق'),
            is_detail=True, is_active=True,
        )
        for acc in cash_qs:
            totals = JournalLine.objects.filter(
                account=acc, entry__status='posted'
            ).aggregate(d=Sum('debit'), c=Sum('credit'))
            cash_balance += (totals['d'] or Decimal('0')) - (totals['c'] or Decimal('0'))

        # قيمة المخزون
        stock_value = InventoryValuation.get_total_inventory_value()

        # أوامر إنتاج
        prod_filter = {}
        if branch:
            prod_filter['warehouse_raw__branch'] = branch

        active_production = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress', 'quality_check'],
            **prod_filter,
        ).count()

        cust_prefix = {'invoices__' + k: v for k, v in invoice_filter.items()}
        active_customers = Customer.objects.filter(
            invoices__date__gte=now - timedelta(days=90),
            **cust_prefix,
        ).distinct().count()

        def kpi_color(value, green_threshold, yellow_threshold):
            if value >= green_threshold:
                return 'success'
            elif value >= yellow_threshold:
                return 'warning'
            return 'danger'

        context['stats'] = {
            'sales_today': sales_today,
            'sales_month': sales_month,
            'profit_month': profit_month,
            'profit_margin': profit_margin,
            'profit_margin_color': kpi_color(profit_margin, 25, 15),
            'invoices_today': invoices_today,
            'cash_balance': cash_balance,
            'stock_value': stock_value,
            'active_production': active_production,
            'active_customers': active_customers,
        }

        # ===== 2. رسم بياني — مبيعات آخر 7 أيام =====
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            day = (now - timedelta(days=i)).date()
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time(), tzinfo=now.tzinfo)
            day_end = day_start + timedelta(days=1)
            day_sales = SalesInvoice.objects.filter(
                date__gte=day_start, date__lt=day_end,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
                **invoice_filter,
            ).aggregate(total=Sum('total'))['total'] or 0
            chart_labels.append(day.strftime('%d/%m'))
            chart_data.append(float(day_sales))

        context['chart_labels'] = json.dumps(chart_labels)
        context['chart_data'] = json.dumps(chart_data)

        # ===== 3. أفضل 5 منتجات مبيعاً =====
        top_products = (
            SalesInvoiceLine.objects.filter(
                invoice__date__gte=month_start,
                invoice__status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
                **inv_prefix,
            )
            .values('product__code', 'product__name')
            .annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('subtotal'),
                total_profit=Sum('profit'),
            )
            .order_by('-total_revenue')[:5]
        )
        context['top_products'] = list(top_products)

        # ===== 4. تنبيهات =====
        alerts = []

        from apps.inventory.services.stock_engine import StockEngine
        low_stock = StockEngine.get_low_stock_products()
        if low_stock:
            alerts.append({
                'type': 'danger',
                'icon': 'exclamation-triangle-fill',
                'title': f'🔴 {len(low_stock)} منتج تحت حد إعادة الطلب',
                'items': [f"{p['product'].name} (متاح: {p['current_stock']})" for p in low_stock[:5]],
            })

        unpaid = SalesInvoice.objects.filter(
            status__in=['confirmed', 'partial_paid'],
            remaining_amount__gt=0,
            **invoice_filter,
        )
        unpaid_count = unpaid.count()
        unpaid_total = unpaid.aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
        if unpaid_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'cash-coin',
                'title': f'🟡 {unpaid_count} فاتورة غير مدفوعة ({unpaid_total:,.2f} ج.م)',
                'items': [],
            })

        overdue_prod = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress'],
            expected_date__lt=now.date(),
            **prod_filter,
        )
        overdue_count = overdue_prod.count()
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'clock-history',
                'title': f'🔴 {overdue_count} أمر إنتاج متأخر',
                'items': [f"{o.order_number} — {o.product.name}" for o in overdue_prod[:5]],
            })

        if not alerts:
            alerts.append({
                'type': 'success',
                'icon': 'check-circle-fill',
                'title': '🟢 لا توجد تنبيهات — كل شيء يعمل بسلاسة',
                'items': [],
            })

        context['alerts'] = alerts

        # ===== صلاحيات لوحة التحكم حسب دور المستخدم =====
        context['dashboard_perms'] = self._get_dashboard_permissions(self.request.user)
        return context

    def _get_dashboard_permissions(self, user):
        """تحديد ما يراه المستخدم في لوحة التحكم بناءً على دوره الوظيفي."""
        # المشرفون العامون يرون كل شيء
        if user.is_superuser or user.is_staff:
            return {
                'see_sales':       True,
                'see_purchases':   True,
                'see_inventory':   True,
                'see_accounting':  True,
                'see_production':  True,
                'see_hr':          True,
                'see_cost':        True,
                'see_profit':      True,
                'see_all_kpis':    True,
            }

        try:
            from apps.authorization.models import UserRole
            roles = UserRole.objects.filter(
                user=user, is_active=True
            ).select_related('role').values_list(
                'role__level',
                'role__can_see_cost',
                'role__can_see_profit',
            )

            levels       = {r[0] for r in roles}
            can_cost     = any(r[1] for r in roles)
            can_profit   = any(r[2] for r in roles)

            # مستويات المديرين والمحاسبين يرون أكثر
            is_manager   = bool(levels & {'admin', 'manager', 'supervisor'})
            is_sales     = bool(levels & {'admin', 'manager', 'supervisor', 'sales'})
            is_purchases = bool(levels & {'admin', 'manager', 'supervisor', 'purchases'})
            is_inventory = bool(levels & {'admin', 'manager', 'supervisor', 'warehouse'})
            is_accounts  = bool(levels & {'admin', 'manager', 'supervisor', 'accountant'})
            is_hr        = bool(levels & {'admin', 'manager', 'supervisor', 'hr'})
            is_production= bool(levels & {'admin', 'manager', 'supervisor', 'production'})

            return {
                'see_sales':      is_sales or is_manager,
                'see_purchases':  is_purchases or is_manager,
                'see_inventory':  is_inventory or is_manager,
                'see_accounting': is_accounts or is_manager,
                'see_production': is_production or is_manager,
                'see_hr':         is_hr or is_manager,
                'see_cost':       can_cost or is_manager,
                'see_profit':     can_profit or is_manager,
                'see_all_kpis':   is_manager,
            }
        except Exception:
            # fallback: إظهار أساسيات المبيعات فقط
            return {
                'see_sales':      True,
                'see_purchases':  False,
                'see_inventory':  False,
                'see_accounting': False,
                'see_production': False,
                'see_hr':         False,
                'see_cost':       False,
                'see_profit':     False,
                'see_all_kpis':   False,
            }


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'name', 'branch_type', 'governorate', 'area', 'address',
            'phone', 'manager', 'discount_rate', 'contract_start',
            'contract_end', 'contract_terms', 'has_warehouse', 'is_active',
        ]
        widgets = {
            'name':           forms.TextInput(attrs={'class': 'form-control'}),
            'branch_type':    forms.Select(attrs={'class': 'form-select'}),
            'governorate':    forms.TextInput(attrs={'class': 'form-control'}),
            'area':           forms.TextInput(attrs={'class': 'form-control'}),
            'address':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone':          forms.TextInput(attrs={'class': 'form-control'}),
            'manager':        forms.Select(attrs={'class': 'form-select'}),
            'discount_rate':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contract_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_end':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'has_warehouse':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'warehouse_type', 'branch', 'keeper', 'is_active']
        widgets = {
            'name':           forms.TextInput(attrs={'class': 'form-control'}),
            'warehouse_type': forms.Select(attrs={'class': 'form-select'}),
            'branch':         forms.Select(attrs={'class': 'form-select'}),
            'keeper':         forms.Select(attrs={'class': 'form-select'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='تأكيد كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'branch', 'phone', 'is_staff', 'is_active',
        ]
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'branch':     forms.Select(attrs={'class': 'form-select'}),
            'phone':      forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'كلمتا المرور غير متطابقتين.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


# ══════════════════════════════════════════════════════
# Branch Views
# ══════════════════════════════════════════════════════

class BranchListView(AdminRequiredMixin, ListView):
    model = Branch
    template_name = 'core/branch_list.html'
    context_object_name = 'branches'
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_type = self.request.GET.get('type')
        if branch_type:
            qs = qs.filter(branch_type=branch_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إدارة الفروع'
        ctx['branch_types'] = Branch.BRANCH_TYPE_CHOICES
        return ctx


class BranchCreateView(AdminRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = 'core/branch_form.html'
    success_url = reverse_lazy('core:branch_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إنشاء فرع جديد'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم إنشاء الفرع "{form.instance.name}" بنجاح.')
        return super().form_valid(form)


class BranchDetailView(AdminRequiredMixin, DetailView):
    model = Branch
    template_name = 'core/branch_detail.html'
    context_object_name = 'branch'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        branch = self.object
        ctx['title'] = f'فرع: {branch.name}'
        ctx['warehouses'] = branch.warehouses.filter(is_active=True)
        ctx['employees'] = branch.users.filter(is_active=True)

        today = timezone.now().date()

        try:
            from apps.sales.models import SalesInvoice
            ctx['sales_total'] = SalesInvoice.objects.filter(
                branch=branch,
                status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
            ).aggregate(t=Sum('total'))['t'] or Decimal('0')
            ctx['invoices_count'] = SalesInvoice.objects.filter(branch=branch).count()
        except Exception:
            ctx['sales_total'] = Decimal('0')
            ctx['invoices_count'] = 0

        try:
            from apps.inventory.models import StockLevel
            ctx['stock_value'] = StockLevel.objects.filter(
                warehouse__branch=branch
            ).aggregate(
                t=Sum(F('quantity') * F('product__cost_price'))
            )['t'] or Decimal('0')
        except Exception:
            ctx['stock_value'] = Decimal('0')

        if branch.contract_end:
            days_left = (branch.contract_end - today).days
            ctx['contract_days_left'] = days_left
            ctx['contract_warning'] = days_left <= 30
            ctx['contract_expired'] = days_left < 0

        return ctx


class BranchUpdateView(AdminRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = 'core/branch_form.html'
    success_url = reverse_lazy('core:branch_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل فرع: {self.object.name}'
        ctx['edit_mode'] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم تحديث الفرع "{form.instance.name}" بنجاح.')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# Warehouse Views
# ══════════════════════════════════════════════════════

class WarehouseListView(AdminRequiredMixin, ListView):
    model = Warehouse
    template_name = 'core/warehouse_list.html'
    context_object_name = 'warehouses'
    ordering = ['branch__name', 'name']

    def get_queryset(self):
        return super().get_queryset().select_related('branch', 'keeper')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إدارة المخازن'
        return ctx


class WarehouseCreateView(AdminRequiredMixin, CreateView):
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'core/warehouse_form.html'
    success_url = reverse_lazy('core:warehouse_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إنشاء مخزن جديد'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم إنشاء المخزن "{form.instance.name}" بنجاح.')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# User Views
# ══════════════════════════════════════════════════════

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    ordering = ['username']

    def get_queryset(self):
        qs = super().get_queryset().select_related('branch')
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إدارة المستخدمين'
        ctx['branches'] = Branch.objects.filter(is_active=True)
        return ctx


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إنشاء مستخدم جديد'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم إنشاء المستخدم "{form.instance.username}" بنجاح.')
        return super().form_valid(form)


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'core/user_detail.html'
    context_object_name = 'profile_user'

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.object
        ctx['title'] = f'مستخدم: {user.get_full_name() or user.username}'
        try:
            from apps.authorization.models import UserRole
            ctx['user_roles'] = UserRole.objects.filter(user=user).select_related('role')
        except Exception:
            ctx['user_roles'] = []
        return ctx


# ══════════════════════════════════════════════════════
# Franchise Management
# ══════════════════════════════════════════════════════

class FranchiseManagementView(AdminRequiredMixin, ListView):
    model = Branch
    template_name = 'core/franchise_management.html'
    context_object_name = 'franchises'

    def get_queryset(self):
        return Branch.objects.filter(
            branch_type__in=['franchise', 'distributor']
        ).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إدارة التوكيلات والموزعين'
        today = timezone.now().date()

        franchise_data = []
        for branch in ctx['franchises']:
            days_left = None
            contract_status = 'no_contract'
            if branch.contract_end:
                days_left = (branch.contract_end - today).days
                if days_left < 0:
                    contract_status = 'expired'
                elif days_left <= 30:
                    contract_status = 'expiring_soon'
                else:
                    contract_status = 'active'

            try:
                from apps.sales.models import SalesInvoice
                sales = SalesInvoice.objects.filter(
                    branch=branch,
                    status__in=['confirmed', 'paid', 'partial_paid', 'delivered'],
                ).aggregate(t=Sum('total'))['t'] or Decimal('0')
                balance = SalesInvoice.objects.filter(
                    branch=branch,
                    status__in=['confirmed', 'partial_paid'],
                ).aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
            except Exception:
                sales = Decimal('0')
                balance = Decimal('0')

            franchise_data.append({
                'branch': branch,
                'days_left': days_left,
                'contract_status': contract_status,
                'sales': sales,
                'balance': balance,
            })

        ctx['franchise_data'] = franchise_data
        ctx['expiring_soon_count'] = sum(
            1 for f in franchise_data if f['contract_status'] == 'expiring_soon'
        )
        ctx['expired_count'] = sum(
            1 for f in franchise_data if f['contract_status'] == 'expired'
        )
        return ctx


# ══════════════════════════════════════════════════════
# User Management — Enhanced (Sprint 20)
# ══════════════════════════════════════════════════════

from django.views import View
from django.shortcuts import render


class UserUpdateView(AdminRequiredMixin, UpdateView):
    """تعديل بيانات المستخدم"""
    model = User
    form_class = UserCreateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('core:user_list')

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'])

    def get_form_class(self):
        from django import forms

        class UserUpdateForm(forms.ModelForm):
            class Meta:
                model = User
                fields = [
                    'username', 'first_name', 'last_name', 'email',
                    'branch', 'phone', 'is_staff', 'is_active',
                ]
                widgets = {
                    'username':   forms.TextInput(attrs={'class': 'form-control'}),
                    'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                    'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
                    'email':      forms.EmailInput(attrs={'class': 'form-control'}),
                    'branch':     forms.Select(attrs={'class': 'form-select'}),
                    'phone':      forms.TextInput(attrs={'class': 'form-control'}),
                    'is_staff':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                    'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                }

        return UserUpdateForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل المستخدم: {self.object.username}'
        ctx['edit_mode'] = True
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'تم تحديث المستخدم "{form.instance.username}" بنجاح.')
        return super().form_valid(form)


class UserToggleActiveView(AdminRequiredMixin, View):
    """تعطيل/تفعيل مستخدم"""
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'لا يمكنك تعطيل حسابك!')
            return redirect('core:user_detail', pk=pk)
        user.is_active = not user.is_active
        user.save()
        status_text = 'تفعيل' if user.is_active else 'تعطيل'
        messages.success(request, f'تم {status_text} المستخدم {user.username}')
        return redirect('core:user_list')


class UserChangePasswordView(AdminRequiredMixin, View):
    """تغيير كلمة مرور مستخدم (بواسطة الأدمن)"""
    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        return render(request, 'core/user_change_password.html', {
            'target_user': target_user,
            'title': f'تغيير كلمة مرور: {target_user.username}',
        })

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if new_password != confirm_password:
            messages.error(request, 'كلمتا المرور غير متطابقتين!')
            return redirect('core:user_change_password', pk=pk)
        if len(new_password) < 8:
            messages.error(request, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل!')
            return redirect('core:user_change_password', pk=pk)
        target_user.set_password(new_password)
        target_user.save()
        messages.success(request, f'تم تغيير كلمة مرور {target_user.username}')
        return redirect('core:user_detail', pk=pk)


class MyProfileView(LoginRequiredMixin, View):
    """صفحة البروفايل الشخصي"""
    def get(self, request):
        context = {
            'title': 'حسابي',
            'profile_user': request.user,
            'employee': getattr(request.user, 'employee', None),
        }
        if hasattr(request.user, 'employee'):
            emp = request.user.employee
            try:
                context['leave_balance'] = emp.leave_balances.filter(
                    year=timezone.now().year
                ).first()
                context['recent_attendance'] = emp.attendances.order_by('-date')[:10]
            except Exception:
                pass
        return render(request, 'core/my_profile.html', context)


class MyChangePasswordView(LoginRequiredMixin, View):
    """المستخدم يغير كلمة مروره بنفسه"""
    def get(self, request):
        return render(request, 'core/my_change_password.html', {
            'title': 'تغيير كلمة المرور',
        })

    def post(self, request):
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(old_password):
            messages.error(request, 'كلمة المرور الحالية خاطئة!')
            return redirect('core:my_change_password')
        if new_password != confirm_password:
            messages.error(request, 'كلمتا المرور الجديدة غير متطابقتين!')
            return redirect('core:my_change_password')
        if len(new_password) < 8:
            messages.error(request, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل!')
            return redirect('core:my_change_password')

        request.user.set_password(new_password)
        request.user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        messages.success(request, 'تم تغيير كلمة المرور بنجاح')
        return redirect('core:my_profile')


# ══════════════════════════════════════════════════════
# Global Search (Sprint 20)
# ══════════════════════════════════════════════════════

class GlobalSearchView(LoginRequiredMixin, View):
    """بحث شامل في النظام"""
    def get(self, request):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return render(request, 'core/search_results.html', {
                'query': q,
                'title': 'نتائج البحث',
            })

        results = {}

        try:
            from apps.sales.models import Customer, SalesInvoice
            results['customers'] = Customer.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q) | Q(phone__icontains=q)
            )[:10]
            results['invoices'] = SalesInvoice.objects.filter(
                Q(invoice_number__icontains=q) | Q(customer__name__icontains=q)
            ).select_related('customer')[:10]
        except Exception:
            pass

        try:
            from apps.inventory.models import Product
            results['products'] = Product.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q) | Q(barcode__icontains=q)
            )[:10]
        except Exception:
            pass

        try:
            from apps.quotations.models import Quotation
            results['quotations'] = Quotation.objects.filter(
                Q(quotation_number__icontains=q) | Q(prospect_name__icontains=q)
            )[:10]
        except Exception:
            pass

        try:
            from apps.hr.models import Employee
            results['employees'] = Employee.objects.filter(
                Q(full_name_ar__icontains=q) | Q(employee_number__icontains=q)
            )[:10]
        except Exception:
            pass

        try:
            from apps.purchases.models import Supplier
            results['suppliers'] = Supplier.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q)
            )[:10]
        except Exception:
            pass

        try:
            from apps.crm.models import Lead
            results['leads'] = Lead.objects.filter(
                Q(name__icontains=q) | Q(phone__icontains=q)
            )[:10]
        except Exception:
            pass

        try:
            from apps.production.models import ProductionOrder
            results['production_orders'] = ProductionOrder.objects.filter(
                order_number__icontains=q
            )[:5]
        except Exception:
            pass

        total = sum(len(qs) for qs in results.values())

        return render(request, 'core/search_results.html', {
            'title': f'نتائج البحث: {q}',
            'query': q,
            'results': results,
            'total': total,
        })


# ══════════════════════════════════════════════════════
# Error Handlers (Sprint 20)
# ══════════════════════════════════════════════════════

def handler404(request, exception):
    """صفحة 404 مخصصة"""
    return render(request, '404.html', {'title': 'الصفحة غير موجودة'}, status=404)


def handler500(request):
    """صفحة 500 مخصصة"""
    return render(request, '500.html', {'title': 'خطأ في الخادم'}, status=500)


# ══════════════════════════════════════════════════════
# Sprint 22A Part 2 — إدارة المستخدمين بالتفويض الهرمي
# ══════════════════════════════════════════════════════

from apps.authorization.services.delegation_engine import DelegationEngine
from apps.authorization.services.permission_engine import PermissionEngine
from apps.authorization.models import SystemRole, UserRoleAssignment


# ─── تأكد من استيراد get_object_or_404 مرة أخرى (safe) ───
from django.shortcuts import render, redirect, get_object_or_404


class UserListView(LoginRequiredMixin, ListView):
    """
    قائمة المستخدمين — المدير يشوف فقط من يحق له إدارتهم
    """
    model = User
    template_name = 'core/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.select_related('branch').prefetch_related(
            'role_assignments__role'
        ).order_by('-date_joined')

        # فلترة حسب النطاق
        if not self.request.user.is_superuser:
            scope = PermissionEngine.get_user_scope(self.request.user)
            if scope.get('scope') != 'all' and scope.get('branch_ids'):
                qs = qs.filter(branch_id__in=scope['branch_ids'])

        # فلترة إضافية
        search = self.request.GET.get('search', '') or self.request.GET.get('q', '')
        role_filter = self.request.GET.get('role', '')
        status_filter = self.request.GET.get('status', '')

        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        if role_filter:
            qs = qs.filter(role_assignments__role_id=role_filter, role_assignments__is_active=True)
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'إدارة المستخدمين'
        context['roles'] = SystemRole.objects.filter(is_active=True)
        context['branches'] = Branch.objects.filter(is_active=True)
        context['can_add_user'] = (
            self.request.user.is_superuser or
            DelegationEngine.get_grantable_roles(self.request.user).exists()
        )
        return context


class DelegatedUserCreateView(LoginRequiredMixin, View):
    """
    إنشاء مستخدم جديد — حسب صلاحيات المدير

    السلوك:
    1. الفرع يُحدد تلقائياً (لو مدير فرع = فرعه)
    2. الأدوار تظهر فقط المسموحة
    3. النظام يمنع أي تجاوز
    4. كل شيء يُسجل في Audit Log
    """

    def get(self, request):
        # فحص: هل يقدر يضيف مستخدمين أصلاً؟
        grantable_roles = DelegationEngine.get_grantable_roles(request.user)
        if not grantable_roles.exists() and not request.user.is_superuser:
            messages.error(request, "ليس لديك صلاحية لإضافة مستخدمين")
            return redirect('core:user_list')

        grantable_branches = DelegationEngine.get_grantable_branches(request.user)
        grantable_warehouses = DelegationEngine.get_grantable_warehouses(request.user)
        grantable_lines = DelegationEngine.get_grantable_production_lines(request.user)

        # الموظفين غير المرتبطين بحساب
        try:
            from apps.hr.models import Employee
            unlinked_employees = Employee.objects.filter(
                is_active=True, user__isnull=True,
            )
            # لو مدير فرع — يرى موظفي فرعه فقط
            scope = PermissionEngine.get_user_scope(request.user)
            if scope.get('branch_ids') and scope.get('scope') != 'all':
                unlinked_employees = unlinked_employees.filter(
                    branch_id__in=scope['branch_ids']
                )
        except Exception:
            unlinked_employees = []
            scope = PermissionEngine.get_user_scope(request.user)

        context = {
            'title': 'إضافة مستخدم جديد',
            'grantable_roles': grantable_roles,
            'grantable_branches': grantable_branches,
            'grantable_warehouses': grantable_warehouses,
            'grantable_lines': grantable_lines,
            'unlinked_employees': unlinked_employees,
            'user_scope': scope,
            # لو مدير فرع = فرع واحد فقط → نثبّته
            'fixed_branch': grantable_branches.first() if grantable_branches.count() == 1 else None,
        }

        return render(request, 'core/user_create_delegated.html', context)

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # جمع البيانات
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role_id = request.POST.get('role')
        branch_id = request.POST.get('branch')
        warehouse_id = request.POST.get('warehouse')
        line_id = request.POST.get('production_line')
        employee_id = request.POST.get('employee')

        # ═══ التحقق ═══
        errors = []

        if not username:
            errors.append("اسم المستخدم مطلوب")
        elif User.objects.filter(username=username).exists():
            errors.append("اسم المستخدم موجود بالفعل")

        if not password or len(password) < 8:
            errors.append("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        if password != confirm_password:
            errors.append("كلمتا المرور غير متطابقتين")

        if not first_name:
            errors.append("الاسم الأول مطلوب")

        if not role_id:
            errors.append("يجب اختيار دور")

        # تحميل الكائنات
        role = None
        branch = None
        warehouse = None
        production_line = None

        if role_id:
            try:
                role = SystemRole.objects.get(pk=role_id)
            except SystemRole.DoesNotExist:
                errors.append("الدور غير موجود")

        if branch_id:
            from apps.core.models import Branch
            try:
                branch = Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                errors.append("الفرع غير موجود")

        if warehouse_id:
            from apps.core.models import Warehouse
            try:
                warehouse = Warehouse.objects.get(pk=warehouse_id)
            except Warehouse.DoesNotExist:
                errors.append("المخزن غير موجود")

        if line_id:
            try:
                from apps.production.models import ProductionLine
                production_line = ProductionLine.objects.get(pk=line_id)
            except Exception:
                errors.append("خط الإنتاج غير موجود")

        # ═══ التحقق من التفويض (الأهم!) ═══
        if role and not errors:
            is_valid, delegation_error = DelegationEngine.validate_assignment(
                granting_user=request.user,
                role=role,
                branch=branch,
                warehouse=warehouse,
                production_line=production_line,
            )
            if not is_valid:
                errors.append(delegation_error)

        # ═══ لو فيه أخطاء — ارجع ═══
        if errors:
            for err in errors:
                messages.error(request, err)
            return self.get(request)

        # ═══ إنشاء المستخدم ═══
        from django.db import transaction

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )

            # لو الـ User model فيه حقل branch — حدّثه
            if branch and hasattr(user, 'branch'):
                user.branch = branch
                user.save()

            # تعيين الدور
            UserRoleAssignment.objects.create(
                user=user,
                role=role,
                branch=branch,
                warehouse=warehouse,
                production_line=production_line,
                assigned_by=request.user,
            )

            # ربط بموظف (اختياري)
            if employee_id:
                try:
                    from apps.hr.models import Employee
                    emp = Employee.objects.get(pk=employee_id, user__isnull=True)
                    emp.user = user
                    emp.save()
                except Exception:
                    pass

            # ═══ Audit Log ═══
            try:
                from apps.authorization.services.audit import log_action
                log_action(
                    request.user, 'create', 'users', 'User', str(user.id),
                    f'أنشأ المستخدم {user.username} بدور {role.name}'
                    f'{" في فرع " + branch.name if branch else ""}'
                    f'{" في مخزن " + warehouse.name if warehouse else ""}'
                    f'{" في خط " + production_line.name if production_line else ""}'
                )
            except Exception:
                pass

        messages.success(request,
            f"تم إنشاء المستخدم '{user.get_full_name() or user.username}' "
            f"بدور '{role.name}'"
            f"{' في فرع ' + branch.name if branch else ''}"
        )

        return redirect('core:user_detail', pk=user.pk)


class DelegatedUserUpdateView(LoginRequiredMixin, View):
    """
    تعديل مستخدم — بنفس قواعد التفويض
    - المدير يعدّل فقط المستخدمين اللي هو عيّنهم أو تحت نطاقه
    - لا يمكنه رفع الدور لمستوى أعلى منه
    """
    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # فحص: هل يقدر يعدّل هذا المستخدم؟
        if not self._can_manage(request.user, target_user):
            messages.error(request, "ليس لديك صلاحية لتعديل هذا المستخدم")
            return redirect('core:user_list')

        current_assignment = UserRoleAssignment.objects.filter(
            user=target_user, is_active=True
        ).first()

        context = {
            'title': f'تعديل المستخدم: {target_user.get_full_name() or target_user.username}',
            'target_user': target_user,
            'current_assignment': current_assignment,
            'grantable_roles': DelegationEngine.get_grantable_roles(request.user),
            'grantable_branches': DelegationEngine.get_grantable_branches(request.user),
            'grantable_warehouses': DelegationEngine.get_grantable_warehouses(request.user),
            'grantable_lines': DelegationEngine.get_grantable_production_lines(request.user),
        }
        return render(request, 'core/user_update_delegated.html', context)

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        if not self._can_manage(request.user, target_user):
            messages.error(request, "ليس لديك صلاحية لتعديل هذا المستخدم")
            return redirect('core:user_list')

        # تحديث البيانات الشخصية
        target_user.first_name = request.POST.get('first_name', target_user.first_name)
        target_user.last_name = request.POST.get('last_name', target_user.last_name)
        target_user.email = request.POST.get('email', target_user.email)
        target_user.save()

        # تحديث الدور (لو تغيّر)
        new_role_id = request.POST.get('role')
        if new_role_id:
            new_role = get_object_or_404(SystemRole, pk=new_role_id)
            branch_id = request.POST.get('branch')
            warehouse_id = request.POST.get('warehouse')
            line_id = request.POST.get('production_line')

            from apps.core.models import Branch, Warehouse
            branch = Branch.objects.filter(pk=branch_id).first() if branch_id else None
            warehouse = Warehouse.objects.filter(pk=warehouse_id).first() if warehouse_id else None
            line = None
            if line_id:
                try:
                    from apps.production.models import ProductionLine
                    line = ProductionLine.objects.filter(pk=line_id).first()
                except Exception:
                    pass

            is_valid, error = DelegationEngine.validate_assignment(
                request.user, new_role, branch, warehouse, line
            )
            if not is_valid:
                messages.error(request, error)
                return redirect('core:user_update', pk=pk)

            # تعطيل التعيين القديم
            old_assignment = UserRoleAssignment.objects.filter(
                user=target_user, is_active=True
            ).first()
            UserRoleAssignment.objects.filter(user=target_user, is_active=True).update(is_active=False)

            UserRoleAssignment.objects.create(
                user=target_user,
                role=new_role,
                branch=branch,
                warehouse=warehouse,
                production_line=line,
                assigned_by=request.user,
            )

            try:
                from apps.authorization.services.audit import log_action
                old_role_name = old_assignment.role.name if old_assignment else 'بدون'
                log_action(
                    request.user, 'update', 'users', 'UserRole', str(target_user.id),
                    f'تغيير دور {target_user.username}: {old_role_name} → {new_role.name}'
                )
            except Exception:
                pass

        messages.success(request, f"تم تعديل بيانات '{target_user.username}'")
        return redirect('core:user_detail', pk=pk)

    def _can_manage(self, manager, target):
        """هل المدير يقدر يدير هذا المستخدم؟"""
        if manager.is_superuser:
            return True
        if manager == target:
            return False  # لا يعدّل نفسه من هنا

        # هل هو اللي عيّنه؟
        assigned_by_me = UserRoleAssignment.objects.filter(
            user=target, assigned_by=manager
        ).exists()
        if assigned_by_me:
            return True

        # هل المستخدم في نطاقه؟
        scope = PermissionEngine.get_user_scope(manager)
        if scope.get('scope') == 'all':
            target_role = UserRoleAssignment.objects.filter(
                user=target, is_active=True
            ).first()
            if target_role:
                return DelegationEngine.can_grant_role(manager, target_role.role)
            return True

        if scope.get('branch_ids'):
            target_branch = getattr(target, 'branch_id', None)
            if target_branch and target_branch in scope['branch_ids']:
                return True

        return False


class UserToggleActiveView(LoginRequiredMixin, View):
    """تعطيل أو تفعيل مستخدم"""
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # لا يعطّل نفسه
        if target_user == request.user:
            messages.error(request, "لا يمكنك تعطيل حسابك!")
            return redirect('core:user_list')

        # فحص التفويض
        update_view = DelegatedUserUpdateView()
        if not update_view._can_manage(request.user, target_user):
            messages.error(request, "ليس لديك صلاحية")
            return redirect('core:user_list')

        target_user.is_active = not target_user.is_active
        target_user.save()

        action = "تفعيل" if target_user.is_active else "تعطيل"

        try:
            from apps.authorization.services.audit import log_action
            log_action(request.user, 'update', 'users', 'User', str(target_user.id),
                       f'{action} المستخدم {target_user.username}')
        except Exception:
            pass

        messages.success(request, f"تم {action} المستخدم '{target_user.username}'")
        return redirect('core:user_list')


class AdminChangePasswordView(LoginRequiredMixin, View):
    """المدير يغيّر كلمة مرور مستخدم تحته"""
    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        return render(request, 'core/admin_change_password.html', {
            'target_user': target_user,
            'title': f'تغيير كلمة مرور: {target_user.username}',
        })

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # فحص التفويض
        update_view = DelegatedUserUpdateView()
        if not update_view._can_manage(request.user, target_user):
            messages.error(request, "ليس لديك صلاحية")
            return redirect('core:user_list')

        new_password = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if new_password != confirm:
            messages.error(request, "كلمتا المرور غير متطابقتين")
            return redirect('core:user_change_password', pk=pk)
        if len(new_password) < 8:
            messages.error(request, "كلمة المرور يجب أن تكون 8 أحرف على الأقل")
            return redirect('core:user_change_password', pk=pk)

        target_user.set_password(new_password)
        target_user.save()

        try:
            from apps.authorization.services.audit import log_action
            log_action(request.user, 'update', 'users', 'User', str(target_user.id),
                       f'تغيير كلمة مرور {target_user.username}')
        except Exception:
            pass

        messages.success(request, f"تم تغيير كلمة مرور '{target_user.username}'")
        return redirect('core:user_detail', pk=pk)


class DelegationReportView(LoginRequiredMixin, View):
    """
    تقرير: من أضاف من — متى — أي دور
    متاح للإدارة العليا والمراجع فقط
    """
    def get(self, request):
        if not request.user.is_superuser and not PermissionEngine.has_permission(
            request.user, 'authorization', 'audit_log'
        ):
            messages.error(request, "ليس لديك صلاحية")
            return redirect('core:dashboard')

        report = DelegationEngine.get_delegation_report()

        # فلترة اختيارية
        manager_filter = request.GET.get('manager')
        branch_filter = request.GET.get('branch')
        if manager_filter:
            report = report.filter(assigned_by_id=manager_filter)
        if branch_filter:
            report = report.filter(branch_id=branch_filter)

        return render(request, 'authorization/delegation_report.html', {
            'assignments': report,
            'title': 'تقرير التفويضات',
            'branches': Branch.objects.filter(is_active=True),
        })


# ══════════════════════════════════════════════════════
# Company Settings — إعدادات الشركة (Sprint 24)
# ══════════════════════════════════════════════════════

class CompanySettingsForm(forms.ModelForm):
    """فورم إعدادات الشركة — شامل كل التبويبات"""

    class Meta:
        model = Company
        exclude = ['setup_completed']
        widgets = {
            'name':              forms.TextInput(attrs={'class': 'form-control'}),
            'name_en':           forms.TextInput(attrs={'class': 'form-control'}),
            'legal_name':        forms.TextInput(attrs={'class': 'form-control'}),
            'code':              forms.TextInput(attrs={'class': 'form-control'}),
            # قانونية
            'tax_number':        forms.TextInput(attrs={'class': 'form-control'}),
            'commercial_register': forms.TextInput(attrs={'class': 'form-control'}),
            'industry_register': forms.TextInput(attrs={'class': 'form-control'}),
            # عنوان
            'address':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city':              forms.TextInput(attrs={'class': 'form-control'}),
            'governorate':       forms.TextInput(attrs={'class': 'form-control'}),
            'country':           forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code':       forms.TextInput(attrs={'class': 'form-control'}),
            # تواصل
            'phone':             forms.TextInput(attrs={'class': 'form-control'}),
            'phone2':            forms.TextInput(attrs={'class': 'form-control'}),
            'fax':               forms.TextInput(attrs={'class': 'form-control'}),
            'email':             forms.EmailInput(attrs={'class': 'form-control'}),
            'website':           forms.URLInput(attrs={'class': 'form-control'}),
            # مالية
            'default_currency':  forms.TextInput(attrs={'class': 'form-control'}),
            'vat_rate':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fiscal_year_start_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            # طباعة
            'invoice_header':    forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'invoice_footer':    forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'invoice_terms':     forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'quotation_terms':   forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'warranty_terms':    forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            # مخزون
            'default_valuation_method': forms.Select(attrs={'class': 'form-select'}),
            # أمان
            'session_timeout_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_login_attempts':      forms.NumberInput(attrs={'class': 'form-control'}),
            'password_min_length':     forms.NumberInput(attrs={'class': 'form-control'}),
            # نشط
            'is_active':         forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CompanySettingsView(LoginRequiredMixin, View):
    """
    إعدادات الشركة — فورم مقسم لـ 6 تبويبات:
    1. بيانات أساسية
    2. بيانات قانونية
    3. إعدادات مالية
    4. إعدادات الطباعة
    5. إعدادات المخزون
    6. إعدادات الأمان
    """
    template_name = 'core/company_settings.html'

    def _require_admin(self, request):
        return request.user.is_superuser or request.user.is_staff

    def get(self, request):
        if not self._require_admin(request):
            messages.error(request, 'هذه الصفحة للإدارة فقط.')
            return redirect('core:dashboard')
        company = Company.get_main()
        form = CompanySettingsForm(instance=company)
        active_tab = request.GET.get('tab', 'basic')
        return render(request, self.template_name, {
            'form': form,
            'company': company,
            'active_tab': active_tab,
            'title': 'إعدادات الشركة',
        })

    def post(self, request):
        if not self._require_admin(request):
            messages.error(request, 'هذه الصفحة للإدارة فقط.')
            return redirect('core:dashboard')
        company = Company.get_main()
        form = CompanySettingsForm(request.POST, request.FILES, instance=company)
        active_tab = request.POST.get('active_tab', 'basic')
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ إعدادات الشركة بنجاح ✔')
            return redirect(f"{request.path}?tab={active_tab}")
        return render(request, self.template_name, {
            'form': form,
            'company': company,
            'active_tab': active_tab,
            'title': 'إعدادات الشركة',
        })


# ══════════════════════════════════════════════════════
# Setup Wizard — معالج الإعداد الأولي (Sprint 24)
# ══════════════════════════════════════════════════════

class SetupWizardView(LoginRequiredMixin, View):
    """
    معالج الإعداد الأولي — يظهر لأول مرة فقط (setup_completed=False)

    الخطوات:
    1  — بيانات الشركة
    2  — الفروع والمخازن
    3  — الأقسام
    4  — المستخدمون والأدوار
    5  — السنة المالية
    6  — ✅ جاهز
    """
    template_name = 'core/setup_wizard.html'
    TOTAL_STEPS = 6

    def _require_superuser(self, request):
        if not request.user.is_superuser:
            messages.error(request, 'معالج الإعداد للمدير العام فقط.')
            return False
        return True

    def _get_step(self, request):
        try:
            step = int(request.GET.get('step', request.POST.get('step', 1)))
        except (ValueError, TypeError):
            step = 1
        return max(1, min(step, self.TOTAL_STEPS))

    def get(self, request):
        if not self._require_superuser(request):
            return redirect('core:dashboard')
        company = Company.get_main()
        # لو انتهى الإعداد، اعرض رسالة مع زر لإعادة الفتح
        if company.setup_completed and not request.GET.get('reopen'):
            return render(request, self.template_name, {
                'already_done': True,
                'company': company,
                'title': 'معالج الإعداد',
            })
        step = self._get_step(request)
        context = self._build_context(request, company, step)
        return render(request, self.template_name, context)

    def post(self, request):
        if not self._require_superuser(request):
            return redirect('core:dashboard')
        company = Company.get_main()
        step = self._get_step(request)
        action = request.POST.get('action', 'next')

        if action == 'prev':
            return redirect(f"{request.path}?step={max(1, step - 1)}&reopen=1")

        # معالجة كل خطوة
        if step == 1:
            self._process_step1(request, company)
        elif step == 2:
            self._process_step2(request, company)
        elif step == 3:
            self._process_step3(request, company)
        elif step == 4:
            self._process_step4(request, company)
        elif step == 5:
            self._process_step5(request, company)
        elif step == 6:
            # اكتمل الإعداد
            company.setup_completed = True
            company.save(update_fields=['setup_completed'])
            messages.success(request, '🎉 تم إعداد النظام بنجاح! مرحباً بك في RITA ERP.')
            return redirect('core:dashboard')

        next_step = step + 1
        return redirect(f"{request.path}?step={next_step}&reopen=1")

    # ── معالجة خطوات الويزارد ──────────────────────────

    def _process_step1(self, request, company):
        """بيانات الشركة الأساسية"""
        for field in ['name', 'name_en', 'legal_name', 'tax_number',
                      'commercial_register', 'phone', 'email', 'address',
                      'city', 'governorate', 'country']:
            val = request.POST.get(field, '').strip()
            if val:
                setattr(company, field, val)
        if 'logo' in request.FILES:
            company.logo = request.FILES['logo']
        company.save()
        messages.success(request, 'تم حفظ بيانات الشركة.')

    def _process_step2(self, request, company):
        """الفروع والمخازن"""
        branch_names = request.POST.getlist('branch_name')
        warehouse_names = request.POST.getlist('warehouse_name')
        for bname in branch_names:
            bname = bname.strip()
            if bname:
                Branch.objects.get_or_create(name=bname)
        for wname in warehouse_names:
            wname = wname.strip()
            if wname:
                Warehouse.objects.get_or_create(name=wname)
        messages.success(request, 'تم حفظ الفروع والمخازن.')

    def _process_step3(self, request, company):
        """الأقسام — (Department إن وجد model، وإلا تجاهل)"""
        dept_names = request.POST.getlist('dept_name')
        try:
            from apps.hr.models import Department
            for dname in dept_names:
                dname = dname.strip()
                if dname:
                    Department.objects.get_or_create(name=dname)
            messages.success(request, 'تم حفظ الأقسام.')
        except Exception:
            messages.info(request, 'تم تخطي الأقسام.')

    def _process_step4(self, request, company):
        """المستخدمون الأساسيون"""
        usernames = request.POST.getlist('username')
        full_names = request.POST.getlist('full_name')
        emails     = request.POST.getlist('user_email')
        passwords  = request.POST.getlist('password')
        for i, uname in enumerate(usernames):
            uname = uname.strip()
            if not uname:
                continue
            if not User.objects.filter(username=uname).exists():
                u = User(username=uname)
                full = full_names[i].strip() if i < len(full_names) else ''
                if ' ' in full:
                    u.first_name, u.last_name = full.split(' ', 1)
                else:
                    u.first_name = full
                em = emails[i].strip() if i < len(emails) else ''
                if em:
                    u.email = em
                pw = passwords[i].strip() if i < len(passwords) else ''
                if pw:
                    u.set_password(pw)
                else:
                    u.set_unusable_password()
                u.save()
        messages.success(request, 'تم إنشاء المستخدمين.')

    def _process_step5(self, request, company):
        """إعداد السنة المالية"""
        month = request.POST.get('fiscal_year_start_month', '').strip()
        if month:
            try:
                company.fiscal_year_start_month = int(month)
                company.save(update_fields=['fiscal_year_start_month'])
            except ValueError:
                pass
        messages.success(request, 'تم حفظ إعدادات السنة المالية.')

    # ── بناء السياق ────────────────────────────────────

    def _build_context(self, request, company, step):
        ctx = {
            'company': company,
            'step': step,
            'total_steps': self.TOTAL_STEPS,
            'step_range': range(1, self.TOTAL_STEPS + 1),
            'progress': int((step - 1) / self.TOTAL_STEPS * 100),
            'title': 'معالج الإعداد الأولي',
            'already_done': False,
        }
        if step == 2:
            ctx['branches'] = Branch.objects.filter(is_active=True)
            ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        elif step == 4:
            ctx['users'] = User.objects.filter(is_active=True)
        return ctx
