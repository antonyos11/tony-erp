"""
واجهات تطبيق الإنتاج — RITA ERP
"""
from decimal import Decimal, InvalidOperation
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.models import Warehouse
from apps.inventory.models import BillOfMaterials, Product
from apps.inventory.services.stock_engine import StockEngine
from apps.production.models import (
    ProductionLine, ProductionOrder, ProductionStage,
)
from apps.production.services.production_engine import ProductionEngine
from apps.authorization.decorators import PermissionRequiredMixin


# ═══════════════════════════════════════════════
# الفورمات
# ═══════════════════════════════════════════════

class ProductionOrderForm(forms.Form):
    """فورم إنشاء أمر إنتاج"""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            product_type__in=('finished', 'semi_finished'), is_active=True
        ).order_by('name'),
        label='المنتج',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_product'}),
    )
    bom = forms.ModelChoiceField(
        queryset=BillOfMaterials.objects.all(),
        label='قائمة المواد (BOM)',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_bom'}),
        required=False,
    )
    quantity = forms.DecimalField(
        label='الكمية المطلوبة',
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    )
    production_line = forms.ModelChoiceField(
        queryset=ProductionLine.objects.filter(is_active=True).order_by('name'),
        label='خط الإنتاج',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    warehouse_raw = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(warehouse_type='raw_materials'),
        label='مخزن الخامات',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    warehouse_finished = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(warehouse_type='finished'),
        label='مخزن المنتجات التامة',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    expected_date = forms.DateField(
        label='التاريخ المتوقع للانتهاء',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
    )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        bom = cleaned.get('bom')
        if product and not bom:
            default_bom = BillOfMaterials.objects.filter(
                product=product, is_default=True
            ).first()
            if not default_bom:
                default_bom = BillOfMaterials.objects.filter(product=product).first()
            if default_bom:
                cleaned['bom'] = default_bom
            else:
                self.add_error('bom', 'لا توجد قائمة مواد لهذا المنتج. يرجى اختيار BOM.')
        return cleaned


class CompleteStageForm(forms.Form):
    """فورم إكمال مرحلة"""
    worker_count = forms.IntegerField(
        label='عدد العمال',
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
    )
    actual_hours = forms.DecimalField(
        label='الساعات الفعلية',
        min_value=Decimal('0'),
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.5'}),
    )
    notes = forms.CharField(
        label='ملاحظات',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
    )


class CompleteProductionForm(forms.Form):
    """فورم إكمال الإنتاج"""
    quantity_produced = forms.DecimalField(
        label='الكمية المنتجة',
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    )
    quantity_wasted = forms.DecimalField(
        label='كمية الهالك',
        min_value=Decimal('0'),
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    )


class AddLaborForm(forms.Form):
    """فورم إضافة تكلفة عمالة"""
    labor_amount = forms.DecimalField(
        label='مبلغ العمالة',
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    )


class AddOverheadForm(forms.Form):
    """فورم إضافة تكاليف غير مباشرة"""
    overhead_amount = forms.DecimalField(
        label='المبلغ',
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
    )
    description = forms.CharField(
        label='البيان',
        max_length=200,
        initial='تكاليف غير مباشرة',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
    )


class CancelOrderForm(forms.Form):
    """فورم إلغاء أمر إنتاج"""
    reason = forms.CharField(
        label='سبب الإلغاء',
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
    )


# ═══════════════════════════════════════════════
# الواجهات
# ═══════════════════════════════════════════════

class ProductionOrderListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """قائمة أوامر الإنتاج"""
    permission_module = 'production'
    permission_action = 'view'
    template_name = 'production/order_list.html'

    def get(self, request):
        qs = ProductionOrder.objects.select_related(
            'product', 'production_line', 'warehouse_raw', 'warehouse_finished'
        ).order_by('-date', '-order_number')

        status = request.GET.get('status', '')
        line = request.GET.get('line', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        q = request.GET.get('q', '')

        if status:
            qs = qs.filter(status=status)
        if line:
            qs = qs.filter(production_line_id=line)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) | Q(product__name__icontains=q)
            )

        paginator = Paginator(qs, 20)
        page = paginator.get_page(request.GET.get('page', 1))

        return render(request, self.template_name, {
            'page_obj': page,
            'statuses': ProductionOrder.STATUS_CHOICES,
            'lines': ProductionLine.objects.filter(is_active=True),
            'status_colors': {
                'draft': 'secondary',
                'confirmed': 'info',
                'in_progress': 'warning',
                'quality_check': 'primary',
                'completed': 'success',
                'cancelled': 'danger',
            },
        })


class ProductionOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إنشاء أمر إنتاج جديد"""
    permission_module = 'production'
    permission_action = 'create'
    template_name = 'production/order_form.html'

    def get(self, request):
        form = ProductionOrderForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            try:
                order = ProductionEngine.create_production_order(
                    product=form.cleaned_data['product'],
                    bom=form.cleaned_data['bom'],
                    quantity=form.cleaned_data['quantity'],
                    production_line=form.cleaned_data.get('production_line'),
                    warehouse_raw=form.cleaned_data['warehouse_raw'],
                    warehouse_finished=form.cleaned_data['warehouse_finished'],
                    expected_date=form.cleaned_data.get('expected_date'),
                    user=request.user,
                )
                messages.success(request, f'تم إنشاء أمر الإنتاج {order.order_number} بنجاح.')
                return redirect('production:order_detail', pk=order.pk)
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form})


class ProductionOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تفاصيل أمر الإنتاج"""
    permission_module = 'production'
    permission_action = 'view'
    template_name = 'production/order_detail.html'

    def get(self, request, pk):
        order = get_object_or_404(
            ProductionOrder.objects.select_related(
                'product', 'bom', 'production_line',
                'warehouse_raw', 'warehouse_finished',
            ),
            pk=pk
        )
        stages = order.stages.select_related('step').order_by('step__order')
        consumptions = order.material_consumptions.select_related('raw_material')
        cost_breakdown = ProductionEngine.get_production_cost_breakdown(order)

        status_colors = {
            'draft': 'secondary',
            'confirmed': 'info',
            'in_progress': 'warning',
            'quality_check': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
        }

        actions = {
            'can_confirm': order.status == 'draft',
            'can_start': order.status == 'confirmed',
            'can_complete': order.status in ('in_progress', 'quality_check'),
            'can_cancel': order.status not in ('completed', 'cancelled'),
            'can_add_costs': order.status in ('in_progress', 'quality_check'),
            'current_stage': stages.filter(status='in_progress').first(),
        }

        return render(request, self.template_name, {
            'order': order,
            'stages': stages,
            'consumptions': consumptions,
            'cost_breakdown': cost_breakdown,
            'status_colors': status_colors,
            'actions': actions,
        })


class ConfirmOrderView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تأكيد أمر الإنتاج"""
    permission_module = 'production'
    permission_action = 'approve'

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        try:
            ProductionEngine.confirm_order(order, user=request.user)
            messages.success(request, f'تم تأكيد أمر الإنتاج {order.order_number}.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('production:order_detail', pk=pk)


class StartProductionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """بدء الإنتاج وصرف الخامات"""
    permission_module = 'production'
    permission_action = 'edit'

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        try:
            ProductionEngine.start_production(order, user=request.user)
            messages.success(request, f'تم بدء الإنتاج وصرف الخامات لأمر {order.order_number}.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('production:order_detail', pk=pk)


class CompleteStageView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إكمال مرحلة إنتاج"""
    permission_module = 'production'
    permission_action = 'edit'
    template_name = 'production/complete_stage_form.html'

    def get(self, request, pk):
        stage = get_object_or_404(ProductionStage, pk=pk)
        form = CompleteStageForm()
        return render(request, self.template_name, {'form': form, 'stage': stage})

    def post(self, request, pk):
        stage = get_object_or_404(ProductionStage, pk=pk)
        form = CompleteStageForm(request.POST)
        if form.is_valid():
            try:
                ProductionEngine.complete_stage(
                    stage=stage,
                    worker_count=form.cleaned_data['worker_count'],
                    actual_hours=form.cleaned_data['actual_hours'],
                    notes=form.cleaned_data.get('notes', ''),
                    user=request.user,
                )
                messages.success(request, f'تم إكمال مرحلة {stage.step.name}.')
                return redirect('production:order_detail', pk=stage.production_order_id)
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'stage': stage})


class CompleteProductionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إكمال أمر الإنتاج"""
    permission_module = 'production'
    permission_action = 'edit'
    template_name = 'production/complete_production_form.html'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = CompleteProductionForm(initial={'quantity_produced': order.quantity})
        return render(request, self.template_name, {'form': form, 'order': order})

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = CompleteProductionForm(request.POST)
        if form.is_valid():
            try:
                ProductionEngine.complete_production(
                    order=order,
                    quantity_produced=form.cleaned_data['quantity_produced'],
                    quantity_wasted=form.cleaned_data.get('quantity_wasted') or Decimal('0'),
                    user=request.user,
                )
                messages.success(request, f'تم إكمال أمر الإنتاج {order.order_number} بنجاح.')
                return redirect('production:order_detail', pk=pk)
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'order': order})


class AddLaborCostView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إضافة تكلفة عمالة"""
    permission_module = 'production'
    permission_action = 'edit'
    template_name = 'production/labor_form.html'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = AddLaborForm()
        return render(request, self.template_name, {'form': form, 'order': order})

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = AddLaborForm(request.POST)
        if form.is_valid():
            try:
                ProductionEngine.add_labor_cost(
                    order=order,
                    labor_amount=form.cleaned_data['labor_amount'],
                    user=request.user,
                )
                messages.success(request, 'تم إضافة تكلفة العمالة بنجاح.')
                return redirect('production:order_detail', pk=pk)
            except Exception as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'order': order})


class AddOverheadCostView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إضافة تكاليف غير مباشرة"""
    permission_module = 'production'
    permission_action = 'edit'
    template_name = 'production/overhead_form.html'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = AddOverheadForm()
        return render(request, self.template_name, {'form': form, 'order': order})

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = AddOverheadForm(request.POST)
        if form.is_valid():
            try:
                ProductionEngine.add_overhead_cost(
                    order=order,
                    overhead_amount=form.cleaned_data['overhead_amount'],
                    description=form.cleaned_data['description'],
                    user=request.user,
                )
                messages.success(request, 'تم إضافة التكاليف غير المباشرة بنجاح.')
                return redirect('production:order_detail', pk=pk)
            except Exception as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'order': order})


class CancelOrderView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """إلغاء أمر إنتاج"""
    permission_module = 'production'
    permission_action = 'delete'
    template_name = 'production/cancel_form.html'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = CancelOrderForm()
        return render(request, self.template_name, {'form': form, 'order': order})

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        form = CancelOrderForm(request.POST)
        if form.is_valid():
            try:
                ProductionEngine.cancel_order(
                    order=order,
                    reason=form.cleaned_data['reason'],
                    user=request.user,
                )
                messages.success(request, f'تم إلغاء أمر الإنتاج {order.order_number}.')
                return redirect('production:order_list')
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {'form': form, 'order': order})


class ProductionCostReportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تقرير تكلفة الإنتاج"""
    permission_module = 'reports'
    permission_action = 'view'
    template_name = 'production/cost_report.html'

    def get(self, request):
        qs = ProductionOrder.objects.filter(
            status='completed'
        ).select_related('product', 'production_line').order_by('-actual_completion_date')

        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        product_q = request.GET.get('product', '')

        if date_from:
            qs = qs.filter(actual_completion_date__gte=date_from)
        if date_to:
            qs = qs.filter(actual_completion_date__lte=date_to)
        if product_q:
            qs = qs.filter(product__name__icontains=product_q)

        totals = qs.aggregate(
            total_material=Sum('material_cost'),
            total_labor=Sum('labor_cost'),
            total_overhead=Sum('overhead_cost'),
            total_cost=Sum('total_cost'),
        )

        return render(request, self.template_name, {
            'orders': qs,
            'totals': totals,
            'date_from': date_from,
            'date_to': date_to,
            'product_q': product_q,
        })


# ═══════════════════════════════════════════════
# AJAX
# ═══════════════════════════════════════════════

class GetBOMForProductView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """جلب BOMs الخاصة بمنتج (AJAX)"""
    permission_module = 'production'
    permission_action = 'view'

    def get(self, request):
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'boms': []})
        boms = BillOfMaterials.objects.filter(product_id=product_id).values(
            'id', 'name', 'is_default'
        )
        return JsonResponse({'boms': list(boms)})


class GetBOMDetailsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """جلب تفاصيل BOM مع أرصدة المخزون (AJAX)"""
    permission_module = 'production'
    permission_action = 'view'

    def get(self, request):
        bom_id = request.GET.get('bom_id')
        warehouse_id = request.GET.get('warehouse_id')
        quantity = request.GET.get('quantity', '1')
        try:
            qty = Decimal(quantity)
        except InvalidOperation:
            qty = Decimal('1')

        if not bom_id:
            return JsonResponse({'lines': [], 'shortages': []})

        try:
            bom = BillOfMaterials.objects.get(pk=bom_id)
        except BillOfMaterials.DoesNotExist:
            return JsonResponse({'lines': [], 'shortages': []})

        lines = []
        shortages = []

        for line in bom.lines.select_related('raw_material'):
            required = line.quantity * qty * (1 + line.waste_percentage / 100)
            available = Decimal('0')

            if warehouse_id:
                try:
                    wh = Warehouse.objects.get(pk=warehouse_id)
                    available = StockEngine.get_stock_level(line.raw_material, wh)
                except Exception:
                    pass

            line_data = {
                'material': line.raw_material.name,
                'quantity': float(line.quantity),
                'waste_pct': float(line.waste_percentage),
                'required': float(required),
                'available': float(available),
                'sufficient': float(available) >= float(required),
            }
            lines.append(line_data)
            if float(available) < float(required):
                shortages.append(line_data)

        return JsonResponse({'lines': lines, 'shortages': shortages})


# ══════════════════════════════════════════════════════
# Sprint 20 — Views إضافية للإنتاج
# ══════════════════════════════════════════════════════

class ExtraMaterialView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """صرف خامات إضافية أثناء الإنتاج"""
    permission_module = 'production'
    permission_action = 'edit'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        return render(request, 'production/extra_material.html', {
            'title': f'خامات إضافية — {order.order_number}',
            'order': order,
            'products': Product.objects.filter(product_type='raw_material', is_active=True),
        })

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        product_id = request.POST.get('product')
        quantity = request.POST.get('quantity', '0')
        notes = request.POST.get('notes', '')

        try:
            product = Product.objects.get(pk=product_id)
            qty = Decimal(str(quantity))
            warehouse = getattr(order, 'warehouse_raw', None)
            if warehouse:
                StockEngine.issue_stock(
                    product=product,
                    warehouse=warehouse,
                    quantity=qty,
                    source_type='production_extra',
                    source_id=order.pk,
                    notes=f'خامات إضافية — أمر إنتاج {order.order_number} — {notes}',
                    user=request.user,
                )
                messages.success(request, f'تم صرف {qty} من {product.name}')
        except Exception as e:
            messages.error(request, f'خطأ: {e}')

        return redirect('production:order_detail', pk=pk)


class ProductionWasteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تسجيل هالك أثناء الإنتاج"""
    permission_module = 'production'
    permission_action = 'edit'

    def get(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        return render(request, 'production/production_waste.html', {
            'title': f'تسجيل هالك — {order.order_number}',
            'order': order,
        })

    def post(self, request, pk):
        order = get_object_or_404(ProductionOrder, pk=pk)
        waste_description = request.POST.get('description', '')
        waste_quantity = request.POST.get('quantity', '0')
        notes = request.POST.get('notes', '')

        try:
            qty = Decimal(str(waste_quantity))
            # تسجيل الهالك كحركة مخزون
            warehouse = getattr(order, 'warehouse_raw', None)
            if warehouse and order.product:
                StockEngine.issue_stock(
                    product=order.product,
                    warehouse=warehouse,
                    quantity=qty,
                    source_type='production_waste',
                    source_id=order.pk,
                    notes=f'هالك إنتاج — {order.order_number} — {waste_description} — {notes}',
                    user=request.user,
                )
                messages.success(request, f'تم تسجيل {qty} هالك في أمر الإنتاج {order.order_number}')
        except Exception as e:
            messages.error(request, f'خطأ في تسجيل الهالك: {e}')

        return redirect('production:order_detail', pk=pk)


class DuplicateOrderView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """نسخ أمر إنتاج"""
    permission_module = 'production'
    permission_action = 'create'

    def post(self, request, pk):
        original = get_object_or_404(ProductionOrder, pk=pk)
        try:
            # نسخ الأمر
            new_order = ProductionOrder.objects.create(
                product=original.product,
                bom=original.bom,
                planned_quantity=original.planned_quantity,
                warehouse_raw=original.warehouse_raw,
                warehouse_finished=getattr(original, 'warehouse_finished', None),
                production_line=getattr(original, 'production_line', None),
                expected_date=original.expected_date,
                notes=f'نسخة من {original.order_number}',
                status='draft',
                created_by=request.user,
                updated_by=request.user,
            )
            messages.success(request, f'تم إنشاء نسخة جديدة: {new_order.order_number}')
            return redirect('production:order_detail', pk=new_order.pk)
        except Exception as e:
            messages.error(request, f'خطأ في النسخ: {e}')
            return redirect('production:order_detail', pk=pk)


class ProductionEfficiencyView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """تقرير كفاءة الإنتاج"""
    permission_module = 'production'
    permission_action = 'view'
    template_name = 'production/efficiency_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'تقرير كفاءة الإنتاج'

        from django.utils import timezone as tz
        now = tz.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        orders = ProductionOrder.objects.filter(
            created_at__gte=month_start
        ).select_related('product', 'production_line')

        ctx['orders'] = orders
        ctx['total_orders'] = orders.count()
        ctx['completed_orders'] = orders.filter(status='completed').count()
        ctx['delayed_orders'] = orders.filter(
            status__in=['confirmed', 'in_progress'],
            expected_date__lt=now.date(),
        ).count()

        # حساب الكفاءة الإجمالية
        completed = orders.filter(status='completed')
        if completed.exists():
            total_planned = completed.aggregate(t=Sum('quantity'))['t'] or Decimal('0')
            total_actual = completed.aggregate(t=Sum('quantity_produced'))['t'] or Decimal('0')
            ctx['efficiency_rate'] = (
                round(float(total_actual) / float(total_planned) * 100, 1)
                if total_planned > 0 else 0
            )
        else:
            ctx['efficiency_rate'] = 0

        return ctx
