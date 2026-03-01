"""
واجهات تطبيق المخزون — RITA ERP
"""
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView, FormView,
)

from apps.core.models import Warehouse
from apps.inventory.models import (
    Category, Product, BillOfMaterials, BOMLine, StockLevel, StockMove, UnitOfMeasure,
)
from apps.inventory.services.stock_engine import StockEngine
from apps.inventory.services.valuation import InventoryValuation
from apps.authorization.decorators import PermissionRequiredMixin


# ══════════════════════════════════════════════════════
# Forms
# ══════════════════════════════════════════════════════

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'code', 'barcode', 'name', 'product_type', 'category',
            'unit', 'valuation_method', 'cost_price', 'retail_price',
            'wholesale_price', 'reorder_level', 'is_taxable',
            'warranty_months', 'description', 'is_custom_size',
            'width', 'length', 'height', 'is_active',
        ]
        widgets = {
            'code':             forms.TextInput(attrs={'class': 'form-control'}),
            'barcode':          forms.TextInput(attrs={'class': 'form-control'}),
            'name':             forms.TextInput(attrs={'class': 'form-control'}),
            'product_type':     forms.Select(attrs={'class': 'form-select'}),
            'category':         forms.Select(attrs={'class': 'form-select'}),
            'unit':             forms.Select(attrs={'class': 'form-select'}),
            'valuation_method': forms.Select(attrs={'class': 'form-select'}),
            'cost_price':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'retail_price':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'wholesale_price':  forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reorder_level':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'warranty_months':  forms.NumberInput(attrs={'class': 'form-control'}),
            'description':      forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'width':            forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'length':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'height':           forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_taxable':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_custom_size':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active':        forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StockReceiveForm(forms.Form):
    product   = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        label='المنتج', widget=forms.Select(attrs={'class': 'form-select'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='المخزن', widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity  = forms.DecimalField(
        min_value=Decimal('0.01'), label='الكمية',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    unit_cost = forms.DecimalField(
        min_value=Decimal('0'), label='تكلفة الوحدة',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes     = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class StockIssueForm(forms.Form):
    product   = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        label='المنتج', widget=forms.Select(attrs={'class': 'form-select'})
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='المخزن', widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity  = forms.DecimalField(
        min_value=Decimal('0.01'), label='الكمية',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes     = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class StockTransferForm(forms.Form):
    product        = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        label='المنتج', widget=forms.Select(attrs={'class': 'form-select'})
    )
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='من مخزن', widget=forms.Select(attrs={'class': 'form-select'})
    )
    to_warehouse   = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='إلى مخزن', widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity       = forms.DecimalField(
        min_value=Decimal('0.01'), label='الكمية',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    notes          = forms.CharField(
        required=False, label='ملاحظات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('from_warehouse') and cleaned.get('to_warehouse'):
            if cleaned['from_warehouse'] == cleaned['to_warehouse']:
                raise forms.ValidationError('المخزن المصدر والوجهة يجب أن يكونا مختلفين')
        return cleaned


class StockAdjustmentForm(forms.Form):
    product      = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('name'),
        label='المنتج', widget=forms.Select(attrs={'class': 'form-select'})
    )
    warehouse    = forms.ModelChoiceField(
        queryset=Warehouse.objects.all().order_by('name'),
        label='المخزن', widget=forms.Select(attrs={'class': 'form-select'})
    )
    new_quantity = forms.DecimalField(
        min_value=Decimal('0'), label='الكمية الجديدة',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    reason       = forms.CharField(
        required=False, label='السبب',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )


class BOMForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterials
        fields = ['product', 'name', 'is_default', 'is_active']
        widgets = {
            'product':    forms.Select(attrs={'class': 'form-select'}),
            'name':       forms.TextInput(attrs={'class': 'form-control'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ══════════════════════════════════════════════════════
# 1. قائمة المنتجات
# ══════════════════════════════════════════════════════

class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 25

    def get_queryset(self):
        qs = Product.objects.select_related('category', 'unit').order_by('code')
        q = self.request.GET.get('q', '')
        product_type = self.request.GET.get('product_type', '')
        category = self.request.GET.get('category', '')
        status = self.request.GET.get('status', '')

        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        if product_type:
            qs = qs.filter(product_type=product_type)
        if category:
            qs = qs.filter(category_id=category)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'المنتجات'
        ctx['product_types'] = Product.PRODUCT_TYPE_CHOICES
        ctx['categories'] = Category.objects.order_by('name')
        ctx['request'] = self.request
        stock_totals = StockLevel.objects.values('product_id').annotate(total=Sum('quantity'))
        stock_map = {s['product_id']: s['total'] for s in stock_totals}
        for p in ctx['products']:
            p.total_stock = stock_map.get(p.pk, Decimal('0'))
        return ctx


# ══════════════════════════════════════════════════════
# 2. إضافة منتج
# ══════════════════════════════════════════════════════

class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_module = 'inventory'
    permission_action = 'create'
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('inventory:product_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إضافة منتج جديد'
        ctx['action'] = 'create'
        return ctx

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم إضافة المنتج بنجاح')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 3. تعديل منتج
# ══════════════════════════════════════════════════════

class ProductUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_module = 'inventory'
    permission_action = 'edit'
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'

    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'تعديل: {self.object.name}'
        ctx['action'] = 'update'
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'تم تعديل المنتج بنجاح')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 4. تفاصيل منتج
# ══════════════════════════════════════════════════════

class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = self.object.name
        ctx['stock_levels'] = StockLevel.objects.filter(
            product=self.object
        ).select_related('warehouse').order_by('warehouse__name')
        ctx['recent_moves'] = StockMove.objects.filter(
            product=self.object
        ).select_related('warehouse_from', 'warehouse_to').order_by('-date')[:20]
        ctx['boms'] = BillOfMaterials.objects.filter(
            product=self.object
        ).prefetch_related('lines__raw_material')
        return ctx


# ══════════════════════════════════════════════════════
# 5. أرصدة المخزون
# ══════════════════════════════════════════════════════

class StockLevelListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = StockLevel
    template_name = 'inventory/stock_levels.html'
    context_object_name = 'stock_levels'
    paginate_by = 40

    def get_queryset(self):
        qs = StockLevel.objects.select_related(
            'product', 'product__category', 'product__unit', 'warehouse'
        ).order_by('product__code', 'warehouse__name')

        warehouse = self.request.GET.get('warehouse', '')
        product_type = self.request.GET.get('product_type', '')

        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        if product_type:
            qs = qs.filter(product__product_type=product_type)
        return qs.filter(quantity__gte=0)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'أرصدة المخزون'
        ctx['warehouses'] = Warehouse.objects.order_by('name')
        ctx['product_types'] = Product.PRODUCT_TYPE_CHOICES
        ctx['request'] = self.request
        return ctx


# ══════════════════════════════════════════════════════
# 6. حركات المخزون
# ══════════════════════════════════════════════════════

class StockMoveListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = StockMove
    template_name = 'inventory/stock_moves.html'
    context_object_name = 'moves'
    paginate_by = 30

    def get_queryset(self):
        qs = StockMove.objects.select_related(
            'product', 'warehouse_from', 'warehouse_to'
        ).order_by('-date')

        move_type = self.request.GET.get('move_type', '')
        product = self.request.GET.get('product', '')
        warehouse = self.request.GET.get('warehouse', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if move_type:
            qs = qs.filter(move_type=move_type)
        if product:
            qs = qs.filter(product_id=product)
        if warehouse:
            qs = qs.filter(Q(warehouse_from_id=warehouse) | Q(warehouse_to_id=warehouse))
        if date_from:
            qs = qs.filter(date__date__gte=date_from)
        if date_to:
            qs = qs.filter(date__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'حركات المخزون'
        ctx['move_types'] = StockMove.MOVE_TYPE_CHOICES
        ctx['products'] = Product.objects.filter(is_active=True).order_by('name')
        ctx['warehouses'] = Warehouse.objects.order_by('name')
        ctx['request'] = self.request
        return ctx


# ══════════════════════════════════════════════════════
# 7. استلام مخزون
# ══════════════════════════════════════════════════════

class StockReceiveView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_module = 'inventory'
    permission_action = 'create'
    form_class = StockReceiveForm
    template_name = 'inventory/stock_receive.html'
    success_url = reverse_lazy('inventory:stock_moves')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'استلام مخزون (وارد)'
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            move = StockEngine.receive_stock(
                product=d['product'],
                warehouse=d['warehouse'],
                quantity=d['quantity'],
                unit_cost=d['unit_cost'],
                notes=d.get('notes', ''),
                user=self.request.user,
            )
            messages.success(self.request, f'تم استلام المخزون بنجاح — رقم الحركة: {move.move_number}')
        except Exception as e:
            messages.error(self.request, f'خطأ: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 8. صرف مخزون
# ══════════════════════════════════════════════════════

class StockIssueView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_module = 'inventory'
    permission_action = 'create'
    form_class = StockIssueForm
    template_name = 'inventory/stock_issue.html'
    success_url = reverse_lazy('inventory:stock_moves')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'صرف مخزون (صادر)'
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            move = StockEngine.issue_stock(
                product=d['product'],
                warehouse=d['warehouse'],
                quantity=d['quantity'],
                notes=d.get('notes', ''),
                user=self.request.user,
            )
            messages.success(self.request, f'تم صرف المخزون بنجاح — رقم الحركة: {move.move_number}')
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 9. تحويل بين مخازن
# ══════════════════════════════════════════════════════

class StockTransferView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_module = 'inventory'
    permission_action = 'edit'
    form_class = StockTransferForm
    template_name = 'inventory/stock_transfer.html'
    success_url = reverse_lazy('inventory:stock_moves')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تحويل مخزون بين مخازن'
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            move = StockEngine.transfer_stock(
                product=d['product'],
                from_warehouse=d['from_warehouse'],
                to_warehouse=d['to_warehouse'],
                quantity=d['quantity'],
                notes=d.get('notes', ''),
                user=self.request.user,
            )
            messages.success(self.request, f'تم التحويل بنجاح — رقم الحركة: {move.move_number}')
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 10. تسوية جرد
# ══════════════════════════════════════════════════════

class StockAdjustmentView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_module = 'inventory'
    permission_action = 'edit'
    form_class = StockAdjustmentForm
    template_name = 'inventory/stock_adjustment.html'
    success_url = reverse_lazy('inventory:stock_moves')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تسوية جرد'
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        result = StockEngine.adjust_stock(
            product=d['product'],
            warehouse=d['warehouse'],
            new_quantity=d['new_quantity'],
            reason=d.get('reason', ''),
            user=self.request.user,
        )
        if result is None:
            messages.info(self.request, 'لا يوجد فرق — الرصيد لم يتغير')
        else:
            messages.success(self.request, f'تمت التسوية بنجاح — رقم الحركة: {result.move_number}')
        return super().form_valid(form)


# ══════════════════════════════════════════════════════
# 11. تقرير المخزون المنخفض
# ══════════════════════════════════════════════════════

class LowStockView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_module = 'inventory'
    permission_action = 'view'
    template_name = 'inventory/low_stock.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تقرير المخزون المنخفض'
        ctx['low_stock_items'] = StockEngine.get_low_stock_products()
        return ctx


# ══════════════════════════════════════════════════════
# 12. تقرير تقييم المخزون
# ══════════════════════════════════════════════════════

class InventoryValuationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'inventory/valuation.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        warehouse_id = self.request.GET.get('warehouse', '')
        product_type = self.request.GET.get('product_type', '')

        warehouse = None
        if warehouse_id:
            warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

        report = InventoryValuation.get_inventory_report(
            warehouse=warehouse,
            product_type=product_type or None,
        )

        ctx['title'] = 'تقييم المخزون'
        ctx['report'] = report
        ctx['warehouses'] = Warehouse.objects.order_by('name')
        ctx['product_types'] = Product.PRODUCT_TYPE_CHOICES
        ctx['selected_warehouse'] = warehouse_id
        ctx['selected_type'] = product_type
        ctx['request'] = self.request
        return ctx


# ══════════════════════════════════════════════════════
# 13. قائمة BOMs
# ══════════════════════════════════════════════════════

class BOMListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = BillOfMaterials
    template_name = 'inventory/bom_list.html'
    context_object_name = 'boms'
    paginate_by = 25

    def get_queryset(self):
        return BillOfMaterials.objects.select_related('product').order_by('product__name', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'قوائم المواد (BOM)'
        return ctx


# ══════════════════════════════════════════════════════
# 14. إنشاء BOM
# ══════════════════════════════════════════════════════

class BOMCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_module = 'inventory'
    permission_action = 'create'
    model = BillOfMaterials
    form_class = BOMForm
    template_name = 'inventory/bom_form.html'
    success_url = reverse_lazy('inventory:bom_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'إنشاء قائمة مواد جديدة'
        ctx['raw_materials'] = Product.objects.filter(
            product_type__in=['raw_material', 'semi_finished'], is_active=True
        ).order_by('name')
        return ctx

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)

        # حفظ أسطر BOM
        materials = self.request.POST.getlist('raw_material')
        quantities = self.request.POST.getlist('line_quantity')
        wastes = self.request.POST.getlist('waste_percentage')
        line_notes = self.request.POST.getlist('line_notes')

        for i, mat_id in enumerate(materials):
            if not mat_id:
                continue
            try:
                product = Product.objects.get(pk=mat_id)
                qty = Decimal(quantities[i]) if i < len(quantities) and quantities[i] else Decimal('1')
                waste = Decimal(wastes[i]) if i < len(wastes) and wastes[i] else Decimal('0')
                note = line_notes[i] if i < len(line_notes) else ''
                BOMLine.objects.create(
                    bom=self.object,
                    raw_material=product,
                    quantity=qty,
                    waste_percentage=waste,
                    notes=note,
                )
            except (Product.DoesNotExist, Exception):
                continue

        messages.success(self.request, 'تم إنشاء قائمة المواد بنجاح')
        return response


# ══════════════════════════════════════════════════════
# 15. تفاصيل BOM
# ══════════════════════════════════════════════════════

class BOMDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_module = 'inventory'
    permission_action = 'view'
    model = BillOfMaterials
    template_name = 'inventory/bom_detail.html'
    context_object_name = 'bom'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'قائمة مواد: {self.object}'
        ctx['lines'] = self.object.lines.select_related('raw_material', 'raw_material__unit').all()
        return ctx


# ══════════════════════════════════════════════════════
# 16. التصنيفات
# ══════════════════════════════════════════════════════

class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_module = 'inventory'
    permission_action = 'view'
    template_name = 'inventory/category_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'التصنيفات'
        ctx['root_categories'] = Category.objects.filter(
            parent__isnull=True
        ).prefetch_related('children__children').order_by('name')
        ctx['all_categories'] = Category.objects.select_related('parent').order_by('name')
        return ctx
