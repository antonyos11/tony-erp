"""
محرك الإنتاج
يدير أوامر الإنتاج من البداية للنهاية
يصرف خامات تلقائياً من BOM
يحسب التكلفة الفعلية
يربط مع المخزون والمحاسبة
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.production.models import (
    ProductionOrder, ProductionStage, MaterialConsumption,
    ProductionStageTemplate, StageStep
)
from apps.inventory.services.stock_engine import StockEngine
from apps.accounts.services.journal_engine import JournalEngine


class ProductionEngine:
    """محرك الإنتاج"""

    @staticmethod
    def _generate_order_number():
        today = timezone.now()
        count = ProductionOrder.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1
        return f"PRD-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_production_order(cls, product, bom, quantity, production_line,
                                 warehouse_raw, warehouse_finished,
                                 expected_date=None, user=None):
        """
        إنشاء أمر إنتاج جديد
        """
        # التحقق من أن المنتج نهائي أو نصف مصنع
        if product.product_type not in ('finished', 'semi_finished'):
            raise ValueError("لا يمكن إنشاء أمر إنتاج لخامة!")

        # التحقق من توفر الخامات
        shortages = []
        for bom_line in bom.lines.all():
            required = bom_line.quantity * quantity * (1 + bom_line.waste_percentage / 100)
            available = StockEngine.get_stock_level(bom_line.raw_material, warehouse_raw)
            if available < required:
                shortages.append({
                    'material': bom_line.raw_material.name,
                    'required': required,
                    'available': available,
                    'deficit': required - available,
                })

        if shortages:
            shortage_text = "\n".join(
                f"- {s['material']}: مطلوب {s['required']}، متاح {s['available']}، نقص {s['deficit']}"
                for s in shortages
            )
            raise ValueError(f"نقص في الخامات:\n{shortage_text}")

        order = ProductionOrder.objects.create(
            order_number=cls._generate_order_number(),
            date=timezone.now().date(),
            product=product,
            bom=bom,
            quantity=quantity,
            production_line=production_line,
            status='draft',
            expected_date=expected_date,
            warehouse_raw=warehouse_raw,
            warehouse_finished=warehouse_finished,
            created_by=user,
            updated_by=user,
        )

        # إنشاء مراحل الإنتاج من القالب
        try:
            template = ProductionStageTemplate.objects.get(
                product_category=product.category
            )
            for step in template.steps.all():
                ProductionStage.objects.create(
                    production_order=order,
                    step=step,
                    status='pending',
                    created_by=user,
                    updated_by=user,
                )
        except ProductionStageTemplate.DoesNotExist:
            pass  # لا يوجد قالب — يمكن إضافة المراحل يدوياً

        # إنشاء سطور استهلاك الخامات المخططة
        for bom_line in bom.lines.all():
            planned_qty = bom_line.quantity * quantity
            waste_qty = planned_qty * (bom_line.waste_percentage / 100)
            MaterialConsumption.objects.create(
                production_order=order,
                raw_material=bom_line.raw_material,
                planned_quantity=planned_qty + waste_qty,
                actual_quantity=Decimal('0'),
                waste_quantity=Decimal('0'),
                created_by=user,
                updated_by=user,
            )

        return order

    @classmethod
    @transaction.atomic
    def confirm_order(cls, order, user=None):
        """
        تأكيد أمر الإنتاج — يبدأ التصنيع
        """
        if order.status != 'draft':
            raise ValueError(f"لا يمكن تأكيد أمر في حالة {order.get_status_display()}")

        order.status = 'confirmed'
        order.updated_by = user
        order.save()
        return order

    @classmethod
    @transaction.atomic
    def start_production(cls, order, user=None):
        """
        بدء الإنتاج — صرف الخامات تلقائياً
        """
        if order.status != 'confirmed':
            raise ValueError("الأمر يجب أن يكون مؤكداً أولاً")

        total_material_cost = Decimal('0')

        # صرف الخامات من المخزون
        for consumption in order.material_consumptions.all():
            move = StockEngine.production_issue(
                product=consumption.raw_material,
                warehouse=order.warehouse_raw,
                quantity=consumption.planned_quantity,
                production_order=order,
                user=user,
            )
            consumption.actual_quantity = consumption.planned_quantity
            consumption.unit_cost = move.unit_cost
            consumption.total_cost = move.total_cost
            consumption.stock_move = move
            consumption.save()
            total_material_cost += move.total_cost

        # تحديث تكلفة الخامات في الأمر
        order.material_cost = total_material_cost
        order.status = 'in_progress'
        order.updated_by = user
        order.save()

        # إنشاء قيد صرف خامات للإنتاج
        JournalEngine.create_production_issue_entry(order, user=user)

        # بدء المرحلة الأولى
        first_stage = order.stages.filter(status='pending').order_by('step__order').first()
        if first_stage:
            first_stage.status = 'in_progress'
            first_stage.started_at = timezone.now()
            first_stage.save()

        return order

    @classmethod
    @transaction.atomic
    def complete_stage(cls, stage, worker_count=0, actual_hours=0, notes='', user=None):
        """
        إكمال مرحلة إنتاج والانتقال للتالية
        """
        if stage.status != 'in_progress':
            raise ValueError("المرحلة يجب أن تكون جارية")

        stage.status = 'completed'
        stage.completed_at = timezone.now()
        stage.worker_count = worker_count
        stage.actual_hours = actual_hours
        stage.notes = notes
        if hasattr(stage, 'updated_by'):
            stage.updated_by = user
        stage.save()

        # بدء المرحلة التالية
        next_stage = stage.production_order.stages.filter(
            status='pending'
        ).order_by('step__order').first()

        if next_stage:
            next_stage.status = 'in_progress'
            next_stage.started_at = timezone.now()
            next_stage.save()
        else:
            # كل المراحل اكتملت — ننتقل لمرحلة فحص الجودة
            stage.production_order.status = 'quality_check'
            stage.production_order.save()

        return stage

    @classmethod
    @transaction.atomic
    def add_labor_cost(cls, order, labor_amount, user=None):
        """
        إضافة تكلفة عمالة مباشرة
        """
        order.labor_cost += labor_amount
        order.save()
        JournalEngine.create_labor_cost_entry(order, labor_amount, user=user)
        return order

    @classmethod
    @transaction.atomic
    def add_overhead_cost(cls, order, overhead_amount, description='تكاليف غير مباشرة', user=None):
        """
        إضافة تكاليف صناعية غير مباشرة
        """
        order.overhead_cost += overhead_amount
        order.save()
        JournalEngine.create_overhead_entry(order, overhead_amount, description, user=user)
        return order

    @classmethod
    @transaction.atomic
    def complete_production(cls, order, quantity_produced, quantity_wasted=0, user=None):
        """
        إكمال أمر الإنتاج — استلام المنتج النهائي
        """
        if order.status not in ('in_progress', 'quality_check'):
            raise ValueError(f"لا يمكن إكمال أمر في حالة {order.get_status_display()}")

        # حساب التكلفة الإجمالية
        order.quantity_produced = quantity_produced
        order.quantity_wasted = quantity_wasted
        order.total_cost = order.material_cost + order.labor_cost + order.overhead_cost

        if quantity_produced > 0:
            order.unit_cost = (order.total_cost / quantity_produced).quantize(Decimal('0.01'))

        order.status = 'completed'
        order.actual_completion_date = timezone.now().date()
        order.updated_by = user
        order.save()

        # استلام المنتج في مخزن المنتجات التامة
        if quantity_produced > 0:
            StockEngine.production_receive(
                product=order.product,
                warehouse=order.warehouse_finished,
                quantity=quantity_produced,
                unit_cost=order.unit_cost,
                production_order=order,
                user=user,
            )

            # قيد استلام إنتاج تام
            JournalEngine.create_production_complete_entry(order, user=user)

        return order

    @classmethod
    @transaction.atomic
    def cancel_order(cls, order, reason='', user=None):
        """
        إلغاء أمر إنتاج
        لو الخامات اتصرفت — ترجع للمخزون
        """
        if order.status in ('completed', 'cancelled'):
            raise ValueError("لا يمكن إلغاء أمر مكتمل أو ملغي")

        # لو الخامات اتصرفت — نرجعها
        if order.status == 'in_progress':
            for consumption in order.material_consumptions.filter(actual_quantity__gt=0):
                StockEngine.receive_stock(
                    product=consumption.raw_material,
                    warehouse=order.warehouse_raw,
                    quantity=consumption.actual_quantity,
                    unit_cost=consumption.unit_cost,
                    source_type='ProductionOrder',
                    source_id=str(order.id),
                    notes=f'إرجاع خامات - إلغاء أمر إنتاج {order.order_number}',
                    user=user,
                )

        order.status = 'cancelled'
        order.notes = f'{order.notes}\nسبب الإلغاء: {reason}'
        order.updated_by = user
        order.save()
        return order

    @classmethod
    def get_production_cost_breakdown(cls, order):
        """
        تفصيل تكلفة أمر الإنتاج
        """
        material_details = []
        for c in order.material_consumptions.all():
            material_details.append({
                'material': c.raw_material.name,
                'planned_qty': c.planned_quantity,
                'actual_qty': c.actual_quantity,
                'waste_qty': c.waste_quantity,
                'unit_cost': c.unit_cost,
                'total_cost': c.total_cost,
            })

        unit_cost = order.unit_cost if order.unit_cost else Decimal('0')
        retail_price = order.product.retail_price if order.product.retail_price else Decimal('0')

        return {
            'order_number': order.order_number,
            'product': order.product.name,
            'quantity_produced': order.quantity_produced,
            'material_cost': order.material_cost,
            'labor_cost': order.labor_cost,
            'overhead_cost': order.overhead_cost,
            'total_cost': order.total_cost,
            'unit_cost': unit_cost,
            'material_details': material_details,
            'margin': retail_price - unit_cost if unit_cost > 0 else Decimal('0'),
        }
