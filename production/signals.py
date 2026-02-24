from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal
import sys
from .models import (
    ProductionOrder, ProductionOrderStage, MaterialConsumption,
    ProductionTimeLog, ProductionAlert, BillOfMaterials
)


@receiver(post_save, sender=ProductionOrder)
def create_production_stages(sender, instance, created, **kwargs):
    """إنشاء مراحل الإنتاج تلقائياً عند إنشاء أمر الإنتاج"""
    if created and instance.bom:
        stages_qs = getattr(instance.bom, 'production_stages', None)
        production_stages = list(stages_qs.all().order_by('sequence')) if stages_qs is not None else []

        if production_stages:
            for stage in production_stages:
                ProductionOrderStage.objects.create(
                    production_order=instance,
                    stage=stage,
                    planned_quantity=instance.planned_quantity,
                    status='pending'
                )
        else:
            # إنشاء مراحل الإنتاج من قائمة المواد (النموذج القديم)
            for bom_stage in instance.bom.stages.all():
                ProductionOrderStage.objects.create(
                    production_order=instance,
                    stage=bom_stage.stage,
                    planned_quantity=instance.planned_quantity,
                    status='pending'
                )


@receiver(pre_save, sender=ProductionOrder)
def update_order_dates(sender, instance, **kwargs):
    """تحديث تواريخ الأمر حسب الحالة وإنشاء وحدات المنتج النهائي عند الاكتمال"""
    if instance.pk:
        try:
            old_instance = ProductionOrder.objects.get(pk=instance.pk)
            
            # إذا تم تغيير الحالة إلى "قيد الإنتاج" وليس هناك تاريخ بدء فعلي
            if (instance.status == 'in_progress' and 
                old_instance.status != 'in_progress' and 
                not instance.actual_start_date):
                instance.actual_start_date = timezone.now().date()
            
            created_finished_units = False
            # إذا تم تغيير الحالة إلى "مكتمل"
            if (instance.status == 'completed' and old_instance.status != 'completed'):
                if not instance.actual_end_date:
                    instance.actual_end_date = timezone.now().date()
                # تعيين الكمية المنتجة إلى الكمية المخططة إذا لم يتم تحديدها
                if instance.produced_quantity == 0:
                    instance.produced_quantity = instance.planned_quantity
                created_finished_units = True
            
        except ProductionOrder.DoesNotExist:
            created_finished_units = False
        
        # بعد التحديث: إذا يجب إنشاء وحدات، قم بإنشائها في transaction آمن
        if 'created_finished_units' in locals() and created_finished_units:
            from django.db import transaction
            from .models import FinishedGoodUnit, ProductManufacturingProfile
            from inventory.barcode_utils import validate_barcode
            from datetime import timedelta

            qty = int(instance.produced_quantity or 0)
            if qty > 0:
                with transaction.atomic():
                    # إعدادات الصلاحية والمقاس الافتراضي
                    shelf_life = 0
                    default_size = ''
                    try:
                        profile = ProductManufacturingProfile.objects.get(product=instance.product)
                        shelf_life = int(profile.shelf_life_days or 0)
                        default_size = profile.default_size_text or ''
                    except ProductManufacturingProfile.DoesNotExist:
                        pass

                    mfg_date = instance.actual_end_date or timezone.now().date()
                    expiry = (mfg_date + timedelta(days=shelf_life)) if shelf_life > 0 else None

                    # توليد وحدات بعدد القطع
                    # صيغة الباركود: POID(6) + تسلسل(4) → 10-12 رقم كحد أدنى، نكمل للأطول بالأصفار
                    created_units = []
                    for i in range(1, qty + 1):
                        raw_code = f"{instance.id:06d}{i:04d}"
                        # أطوّل لحد 12 رقم لأجل توافق مولد Code128/الأرقام
                        barcode_code = raw_code.ljust(12, '0')
                        is_valid, _ = validate_barcode(barcode_code)
                        if not is_valid:
                            # fallback بسيط: timestamp آخر 12 رقم
                            barcode_code = f"{int(timezone.now().timestamp())}"[-12:]
                        unit = FinishedGoodUnit.objects.create(
                            product=instance.product,
                            production_order=instance,
                            unit_serial=f"{instance.number}-{i:04d}",
                            barcode=barcode_code,
                            manufacture_date=mfg_date,
                            expiry_date=expiry,
                            size_text=default_size,
                        )
                        created_units.append(unit)
                    
                    # طباعة تلقائية للباركود على طابعة Zebra
                    if created_units:
                        from inventory.barcode_utils import print_finished_unit_label_auto
                        import logging
                        logger = logging.getLogger(__name__)
                        
                        for unit in created_units:
                            success, message = print_finished_unit_label_auto(unit)
                            if 'test' in sys.argv:
                                # تجنب أخطاء الترميز في مخرجات الاختبارات عند استخدام رموز عربية في وحدات الطباعة
                                continue
                            if not success:
                                logger.warning(f"فشل طباعة باركود للوحدة {unit.unit_serial}: {message}")
                            else:
                                logger.info(f"تمت طباعة باركود للوحدة {unit.unit_serial}")


@receiver(post_save, sender=ProductionOrder)
def check_for_delays(sender, instance, **kwargs):
    """فحص التأخيرات وإنشاء تنبيهات"""
    if instance.status in ['confirmed', 'in_progress', 'quality_check']:
        today = timezone.now().date()
        
        # فحص تأخير البدء
        if (instance.planned_start_date < today and 
            not instance.actual_start_date and
            instance.status == 'confirmed'):
            
            # التحقق من عدم وجود تنبيه مماثل
            if not ProductionAlert.objects.filter(
                production_order=instance,
                alert_type='delay',
                status__in=['new', 'acknowledged']
            ).exists():
                ProductionAlert.objects.create(
                    title=f'تأخير في بدء أمر الإنتاج {instance.number}',
                    alert_type='delay',
                    priority='high',
                    production_order=instance,
                    description=f'تأخر بدء أمر الإنتاج {instance.number} عن التاريخ المخطط {instance.planned_start_date}',
                    suggested_action='مراجعة الجدولة وإعادة تحديد موعد البدء',
                    created_by_id=1  # يمكن تحسين هذا لاحقاً
                )
        
        # فحص تأخير الانتهاء
        if (instance.planned_end_date < today and 
            instance.status != 'completed'):
            
            if not ProductionAlert.objects.filter(
                production_order=instance,
                alert_type='delay',
                title__contains='انتهاء',
                status__in=['new', 'acknowledged']
            ).exists():
                ProductionAlert.objects.create(
                    title=f'تأخير في انتهاء أمر الإنتاج {instance.number}',
                    alert_type='delay',
                    priority='critical',
                    production_order=instance,
                    description=f'تأخر انتهاء أمر الإنتاج {instance.number} عن التاريخ المخطط {instance.planned_end_date}',
                    suggested_action='مراجعة حالة الإنتاج واتخاذ إجراءات لتسريع العملية',
                    created_by_id=1
                )


@receiver(post_save, sender=MaterialConsumption)
def check_material_variance(sender, instance, **kwargs):
    """فحص انحرافات استهلاك المواد"""
    if instance.variance_percentage > 10:  # إذا كان الانحراف أكثر من 10%
        # إنشاء تنبيه عن زيادة الاستهلاك
        if not ProductionAlert.objects.filter(
            production_order=instance.production_order,
            alert_type='material_shortage',
            description__contains=instance.material.name,
            status__in=['new', 'acknowledged']
        ).exists():
            ProductionAlert.objects.create(
                title=f'زيادة في استهلاك المواد - {instance.material.name}',
                alert_type='material_shortage',
                priority='medium',
                production_order=instance.production_order,
                description=f'زيادة غير متوقعة في استهلاك المادة {instance.material.name} بنسبة {instance.variance_percentage:.1f}%',
                suggested_action='مراجعة عملية الإنتاج والتحقق من وجود هدر غير ضروري',
                created_by_id=1
            )


@receiver(post_save, sender=ProductionTimeLog)
def calculate_production_costs(sender, instance, created, **kwargs):
    """حساب تكاليف الإنتاج تلقائياً"""
    if created and instance.total_cost > 0:
        # تحديث تكلفة العمالة في أمر الإنتاج
        order = instance.production_order
        total_labor_cost = order.time_logs.aggregate(
            total=models.Sum('total_cost')
        )['total'] or 0
        
        order.actual_labor_cost = total_labor_cost
        order.save(update_fields=['actual_labor_cost'])


@receiver(pre_save, sender=BillOfMaterials)
def calculate_bom_costs(sender, instance, **kwargs):
    """حساب تكاليف قائمة المواد"""
    if instance.pk:
        # حساب تكلفة المواد
        material_cost = sum(
            item.total_cost for item in instance.items.all()
        )
        instance.total_material_cost = material_cost
        
        # حساب تكلفة العمالة (من المراحل)
        labor_cost = sum(
            stage.stage.labor_cost_per_unit * instance.base_quantity
            for stage in instance.stages.all()
        )
        instance.total_labor_cost = labor_cost
        
        # حساب التكاليف الإضافية (15% من التكاليف المباشرة)
        direct_costs = material_cost + labor_cost
        instance.total_overhead_cost = direct_costs * Decimal('0.15')


@receiver(post_save, sender=ProductionOrder)
def broadcast_production_order_update(sender, instance, **kwargs):
    """بث تحديثات أوامر الإنتاج إلى لوحة متابعة المصنع عبر WebSocket."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        planned = float(instance.planned_quantity or 0)
        produced = float(instance.produced_quantity or 0)
        progress = (produced / planned * 100) if planned > 0 else 0

        # Work center from first stage
        work_center_name = '—'
        first_stage = instance.order_stages.select_related('stage__work_center').first()
        if first_stage and first_stage.stage and first_stage.stage.work_center:
            work_center_name = first_stage.stage.work_center.name

        data = {
            'id': instance.id,
            'number': instance.number,
            'product_name': instance.product.name if instance.product else '—',
            'product_sku': instance.product.sku if instance.product else '—',
            'bom_name': instance.bom.name if instance.bom else '—',
            'work_center': work_center_name,
            'status': instance.status,
            'status_display': instance.get_status_display(),
            'priority': instance.priority,
            'priority_display': instance.get_priority_display(),
            'planned_quantity': planned,
            'produced_quantity': produced,
            'scrap_quantity': float(instance.scrap_quantity or 0),
            'progress': round(progress, 1),
            'planned_end': (
                instance.planned_end_date.isoformat()
                if instance.planned_end_date else None
            ),
            'actual_start': (
                instance.actual_start_date.isoformat()
                if instance.actual_start_date else None
            ),
            'is_overdue': (
                instance.planned_end_date is not None
                and instance.planned_end_date < timezone.now().date()
                and instance.status != 'completed'
            ),
        }

        async_to_sync(channel_layer.group_send)(
            'production_tv_dashboard',
            {
                'type': 'production_order_updated',
                'data': data,
                'timestamp': timezone.now().isoformat(),
            }
        )
    except Exception:
        # Never let a broadcast failure break a save
        pass


def create_low_stock_alerts():
    """إنشاء تنبيهات عن نقص المخزون - يمكن استدعاؤها من مهمة دورية"""
    from inventory.models import Product
    
    low_stock_products = Product.objects.filter(
        current_stock__lte=models.F('min_stock')
    )
    
    for product in low_stock_products:
        # التحقق من عدم وجود تنبيه مماثل حديث
        recent_alert = ProductionAlert.objects.filter(
            alert_type='material_shortage',
            description__contains=product.name,
            status__in=['new', 'acknowledged'],
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).exists()
        
        if not recent_alert:
            ProductionAlert.objects.create(
                title=f'نقص في مخزون المادة - {product.name}',
                alert_type='material_shortage',
                priority='high',
                description=f'المادة {product.name} تحتاج إلى إعادة تخزين. المخزون الحالي: {product.current_stock}, الحد الأدنى: {product.min_stock}',
                suggested_action='طلب شراء عاجل للمادة لضمان استمرارية الإنتاج',
                created_by_id=1
            )