"""
خدمة تكامل الإنتاج مع المخزون
تتعامل مع:
- صرف المواد الخام للإنتاج
- إضافة المنتجات التامة للمخزون
- تحديث مستويات المخزون
- تتبع حركة المواد في مراحل الإنتاج
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from inventory.models import (
    Product, Location, Stock, 
    Issue, IssueItem
)
from production.models import (
    ProductionOrder, MaterialConsumption, BillOfMaterials,
    ProductionOrderStage, FinishedGoodUnit
)


class ProductionInventoryService:
    """خدمة إدارة تكامل الإنتاج والمخزون"""
    
    @staticmethod
    def get_default_locations() -> Dict[str, Optional[Location]]:
        """الحصول على المواقع الافتراضية للإنتاج"""
        return {
            'raw_material': Location.objects.filter(type='raw').first(),
            'wip': Location.objects.filter(type='wip').first(),
            'finished_goods': Location.objects.filter(type='finished').first(),
            'production': Location.objects.filter(
                name__icontains='إنتاج'
            ).first() or Location.objects.filter(type='wip').first(),
        }
    
    @staticmethod
    @transaction.atomic
    def issue_materials_for_order(
        production_order: 'ProductionOrder',
        issued_by: 'User',
        notes: str = ""
    ) -> Tuple[bool, str, Optional['Issue']]:
        """
        إنشاء سند صرف مواد خام لأمر إنتاج
        
        Args:
            production_order: أمر الإنتاج
            issued_by: المستخدم الذي يقوم بالصرف
            notes: ملاحظات إضافية
            
        Returns:
            (success, message, issue_object)
        """
        try:
            # التحقق من وجود BOM
            if not production_order.bom:
                return False, "لا توجد قائمة مواد (BOM) لهذا الأمر", None
            
            # الحصول على المواقع
            locations = ProductionInventoryService.get_default_locations()
            raw_location = locations['raw_material']
            wip_location = locations['wip']
            
            if not raw_location:
                return False, "لم يتم تكوين مخزن المواد الخام", None
            if not wip_location:
                return False, "لم يتم تكوين مخزن الإنتاج تحت التشغيل", None
            
            # إنشاء سند الصرف
            issue = Issue.objects.create(
                location=raw_location,
                to_department='production',
                reference=f"PO-{production_order.number}",
                notes=notes or f"صرف مواد لأمر إنتاج {production_order.number}",
                status='draft',
                issued_by=issued_by
            )
            
            # حساب المواد المطلوبة من BOM
            bom = production_order.bom
            quantity_multiplier = production_order.planned_quantity / bom.base_quantity
            
            total_cost = Decimal('0')
            materials_issued = []
            
            for bom_item in bom.items.all():
                # حساب الكمية المطلوبة
                required_qty = bom_item.quantity_with_wastage * quantity_multiplier
                
                # التحقق من توفر المخزون
                available_stock = Stock.objects.filter(
                    product=bom_item.material,
                    location=raw_location
                ).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0')
                
                if available_stock < required_qty:
                    # تحذير ولكن نستمر
                    materials_issued.append({
                        'material': bom_item.material.name,
                        'required': float(required_qty),
                        'available': float(available_stock),
                        'warning': 'مخزون غير كافي'
                    })
                
                # إنشاء بند الصرف
                try:
                    issue_item = IssueItem.objects.create(
                        issue=issue,
                        product=bom_item.material,
                        quantity=int(required_qty),
                    )
                    
                    item_cost = required_qty * bom_item.unit_cost
                    total_cost += item_cost
                    
                    # تسجيل في استهلاك المواد
                    MaterialConsumption.objects.create(
                        production_order=production_order,
                        material=bom_item.material,
                        planned_quantity=required_qty,
                        consumed_quantity=Decimal('0'),  # سيتم تحديثه عند الترحيل
                        unit_cost=bom_item.unit_cost,
                        location=raw_location,
                        notes=f"من سند صرف {issue.id}"
                    )
                except Exception as item_error:
                    # تسجيل الخطأ ولكن نستمر مع باقي البنود
                    materials_issued.append({
                        'material': bom_item.material.name,
                        'error': str(item_error)
                    })
            
            return True, f"تم إنشاء سند صرف رقم {issue.id} بقيمة {total_cost}", issue
            
        except Exception as e:
            return False, f"خطأ في إنشاء سند الصرف: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def post_material_issue(
        issue: 'Issue',
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, str]:
        """
        ترحيل سند صرف المواد وتحديث المخزون
        
        Args:
            issue: سند الصرف
            production_order: أمر الإنتاج المرتبط
            
        Returns:
            (success, message)
        """
        try:
            if issue.status != 'draft':
                return False, "السند مرحل مسبقاً أو ملغي"
            
            # Use the issue's confirm() method which handles stock deduction
            issue.confirm()
            
            # تحديث استهلاك المواد
            total_material_cost = Decimal('0')
            for item in issue.items.all():
                consumption = MaterialConsumption.objects.filter(
                    production_order=production_order,
                    material=item.product
                ).first()
                
                # Calculate cost from BOM item
                bom_item = production_order.bom.items.filter(material=item.product).first()
                item_cost = Decimal(str(item.quantity)) * (bom_item.unit_cost if bom_item else Decimal('0'))
                total_material_cost += item_cost
                
                if consumption:
                    consumption.consumed_quantity = item.quantity
                    consumption.total_cost = item_cost
                    consumption.save()
            
            # تحديث تكلفة المواد في أمر الإنتاج
            production_order.actual_material_cost = total_material_cost
            production_order.save(update_fields=['actual_material_cost'])
            
            return True, f"تم ترحيل سند الصرف {issue.id} بنجاح"
            
        except Exception as e:
            return False, f"خطأ في ترحيل السند: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def receive_finished_goods(
        production_order: 'ProductionOrder',
        quantity: Decimal,
        received_by: 'User',
        quality_approved: bool = True,
        notes: str = ""
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        استلام منتجات تامة الصنع من الإنتاج
        
        Args:
            production_order: أمر الإنتاج
            quantity: الكمية المنتجة
            received_by: المستخدم المستلم
            quality_approved: هل تمت الموافقة من قسم الجودة
            notes: ملاحظات
            
        Returns:
            (success, message, details_dict)
        """
        try:
            # التحقق من الكمية
            if quantity <= 0:
                return False, "الكمية يجب أن تكون أكبر من صفر", None
            
            if quantity > production_order.remaining_quantity:
                return False, f"الكمية المدخلة ({quantity}) أكبر من المتبقي ({production_order.remaining_quantity})", None
            
            # الحصول على المواقع
            locations = ProductionInventoryService.get_default_locations()
            finished_location = locations['finished_goods']
            
            if not finished_location:
                return False, "لم يتم تكوين مخزن المنتجات التامة", None
            
            # تحديث المخزون مباشرة
            stock, created = Stock.objects.get_or_create(
                product=production_order.product,
                location=finished_location,
                defaults={'quantity': Decimal('0')}
            )
            stock.quantity += quantity
            stock.save()
            
            # تحديث كمية الإنتاج في الأمر
            production_order.produced_quantity += quantity
            
            # تحديث الحالة إذا اكتمل الإنتاج
            if production_order.produced_quantity >= production_order.planned_quantity:
                production_order.status = 'completed'
                production_order.actual_end_date = timezone.now().date()
            elif production_order.status == 'confirmed':
                production_order.status = 'in_progress'
                if not production_order.actual_start_date:
                    production_order.actual_start_date = timezone.now().date()
            
            production_order.save()
            
            return True, f"تم استلام {quantity} وحدة بنجاح", {
                'quantity': float(quantity),
                'total_produced': float(production_order.produced_quantity)
            }
            
        except Exception as e:
            return False, f"خطأ في استلام المنتجات: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def post_finished_goods_receipt(
        receipt_data: Dict,
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, str]:
        """
        ترحيل استلام المنتجات التامة (للتوافق مع الكود القديم)
        
        Args:
            receipt_data: بيانات الاستلام
            production_order: أمر الإنتاج
            
        Returns:
            (success, message)
        """
        # البيانات تم تحديثها مباشرة في receive_finished_goods
        return True, "تم الترحيل بنجاح"
    
    @staticmethod
    @transaction.atomic
    def generate_barcodes_for_finished_goods(
        production_order: 'ProductionOrder',
        quantity: int,
        size_text: str = ""
    ) -> Tuple[bool, str, List['FinishedGoodUnit']]:
        """
        إنشاء باركودات فردية للمنتجات التامة
        
        Args:
            production_order: أمر الإنتاج
            quantity: عدد الوحدات
            size_text: نص المقاس (اختياري)
            
        Returns:
            (success, message, list_of_units)
        """
        try:
            from production.models import ProductManufacturingProfile
            import uuid
            
            units = []
            
            # الحصول على إعدادات التصنيع
            try:
                mfg_profile = production_order.product.mfg_profile
                shelf_life_days = mfg_profile.shelf_life_days
                default_size = size_text or mfg_profile.default_size_text
            except ProductManufacturingProfile.DoesNotExist:
                shelf_life_days = 0
                default_size = size_text
            
            manufacture_date = timezone.now().date()
            expiry_date = None
            if shelf_life_days > 0:
                from datetime import timedelta
                expiry_date = manufacture_date + timedelta(days=shelf_life_days)
            
            # إنشاء الوحدات
            for i in range(quantity):
                # إنشاء رقم تسلسلي فريد
                serial = f"{production_order.number}-{i+1:04d}"
                
                # إنشاء باركود فريد
                barcode = f"{production_order.product.id:05d}{uuid.uuid4().hex[:8].upper()}"
                
                # التحقق من عدم تكرار الباركود
                while FinishedGoodUnit.objects.filter(barcode=barcode).exists():
                    barcode = f"{production_order.product.id:05d}{uuid.uuid4().hex[:8].upper()}"
                
                unit = FinishedGoodUnit.objects.create(
                    product=production_order.product,
                    production_order=production_order,
                    unit_serial=serial,
                    barcode=barcode,
                    manufacture_date=manufacture_date,
                    expiry_date=expiry_date,
                    size_text=default_size
                )
                
                units.append(unit)
            
            return True, f"تم إنشاء {len(units)} باركود بنجاح", units
            
        except Exception as e:
            return False, f"خطأ في إنشاء الباركودات: {str(e)}", []
    
    @staticmethod
    def check_material_availability(
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, List[Dict]]:
        """
        التحقق من توفر المواد الخام لأمر الإنتاج
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            (all_available, list_of_materials_status)
        """
        try:
            if not production_order.bom:
                return False, [{'error': 'لا توجد قائمة مواد'}]
            
            locations = ProductionInventoryService.get_default_locations()
            raw_location = locations['raw_material']
            
            if not raw_location:
                return False, [{'error': 'لم يتم تكوين مخزن المواد الخام'}]
            
            bom = production_order.bom
            quantity_multiplier = production_order.planned_quantity / bom.base_quantity
            
            materials_status = []
            all_available = True
            
            for bom_item in bom.items.all():
                required_qty = bom_item.quantity_with_wastage * quantity_multiplier
                
                # الحصول على المخزون الحالي
                from django.db.models import Sum
                available_stock = Stock.objects.filter(
                    product=bom_item.material,
                    location=raw_location
                ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
                
                is_available = available_stock >= required_qty
                if not is_available:
                    all_available = False
                
                materials_status.append({
                    'material_id': bom_item.material.id,
                    'material_name': bom_item.material.name,
                    'material_code': bom_item.material.sku,
                    'required_quantity': float(required_qty),
                    'available_quantity': float(available_stock),
                    'shortage': float(max(0, required_qty - available_stock)),
                    'is_available': is_available,
                    'unit_cost': float(bom_item.unit_cost),
                    'total_cost': float(required_qty * bom_item.unit_cost)
                })
            
            return all_available, materials_status
            
        except Exception as e:
            return False, [{'error': f'خطأ في التحقق: {str(e)}'}]
