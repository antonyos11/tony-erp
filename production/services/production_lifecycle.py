"""
خدمات متقدمة للإنتاج
تتضمن:
- إدارة دورة حياة أوامر الإنتاج بالكامل
- التكامل الأوتوماتيكي بين المخزون والمحاسبة
- حساب التكاليف الفعلية
- إنشاء القيود والحركات تلقائياً
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from production.models import ProductionOrder, ProductionSettings
from production.services.inventory_integration import ProductionInventoryService
from production.services.accounting_integration import ProductionAccountingService


class ProductionLifecycleService:
    """خدمة إدارة دورة حياة أوامر الإنتاج"""
    
    @staticmethod
    @transaction.atomic
    def start_production_order(
        production_order: 'ProductionOrder',
        user: 'User'
    ) -> Tuple[bool, str, Dict]:
        """
        بدء أمر الإنتاج:
        1. التحقق من توفر المواد
        2. إنشاء سند صرف المواد
        3. ترحيل السند
        4. إنشاء القيد المحاسبي
        5. تحديث حالة الأمر
        
        Args:
            production_order: أمر الإنتاج
            user: المستخدم
            
        Returns:
            (success, message, details_dict)
        """
        try:
            # التحقق من الحالة
            if production_order.status not in ['draft', 'confirmed']:
                return False, f"لا يمكن بدء الأمر، الحالة الحالية: {production_order.get_status_display()}", {}
            
            # 1. التحقق من توفر المواد
            all_available, materials_status = ProductionInventoryService.check_material_availability(
                production_order
            )
            
            if not all_available:
                shortage_list = [
                    f"{m.get('material_name', 'غير معروف')}: نقص {m.get('shortage', '?')}"
                    for m in materials_status if not m.get('is_available', False) and 'error' not in m
                ]
                error_list = [m.get('error', '') for m in materials_status if 'error' in m]
                detail_msg = "\n".join(shortage_list + error_list) if (shortage_list or error_list) else "نقص غير محدد"
                return False, f"نقص في المواد:\n{detail_msg}", {
                    'materials_status': materials_status
                }
            
            # 2. إنشاء سند صرف المواد
            success, msg, issue = ProductionInventoryService.issue_materials_for_order(
                production_order,
                user,
                f"بدء الإنتاج - أمر {production_order.number}"
            )
            
            if not success or issue is None:
                return False, f"فشل إنشاء سند الصرف: {msg}", {}
            
            # 3. ترحيل السند
            success, msg = ProductionInventoryService.post_material_issue(
                issue,
                production_order
            )
            
            if not success:
                return False, f"فشل ترحيل السند: {msg}", {}
            
            # 4. إنشاء القيد المحاسبي للمواد
            success, msg, entry = ProductionAccountingService.create_material_issue_entry(
                production_order,
                production_order.actual_material_cost,
                f"صرف مواد - بدء أمر {production_order.number}"
            )
            
            if success and entry:
                entry.status = 'posted'
                entry.save()
            
            # 5. تحديث حالة الأمر
            production_order.status = 'in_progress'
            production_order.actual_start_date = timezone.now().date()
            production_order.save(update_fields=['status', 'actual_start_date'])
            
            return True, f"تم بدء أمر الإنتاج {production_order.number} بنجاح", {
                'issue_id': issue.id,
                'journal_entry_id': entry.id if entry else None,
                'material_cost': float(production_order.actual_material_cost),
                'materials_status': materials_status
            }
            
        except Exception as e:
            return False, f"خطأ في بدء أمر الإنتاج: {str(e)}", {}
    
    @staticmethod
    @transaction.atomic
    def record_production_output(
        production_order: 'ProductionOrder',
        quantity: Decimal,
        user: 'User',
        generate_barcodes: bool = False,
        size_text: str = ""
    ) -> Tuple[bool, str, Dict]:
        """
        تسجيل إنتاج منتجات تامة:
        1. إنشاء سند استلام المنتجات التامة
        2. ترحيل السند
        3. إنشاء القيد المحاسبي
        4. توليد الباركودات (اختياري)
        5. تحديث حالة الأمر
        
        Args:
            production_order: أمر الإنتاج
            quantity: الكمية المنتجة
            user: المستخدم
            generate_barcodes: هل نولد باركودات فردية
            size_text: نص المقاس للباركودات
            
        Returns:
            (success, message, details_dict)
        """
        try:
            # التحقق من الحالة
            if production_order.status not in ['in_progress', 'quality_check']:
                return False, f"لا يمكن تسجيل الإنتاج، الحالة الحالية: {production_order.get_status_display()}", {}
            
            # 1. استلام المنتجات التامة (تحديث المخزون مباشرة)
            success, msg, receipt_data = ProductionInventoryService.receive_finished_goods(
                production_order,
                quantity,
                user,
                quality_approved=True,
                notes=f"إنتاج {quantity} وحدة"
            )
            
            if not success:
                return False, f"فشل استلام المنتجات: {msg}", {}
            
            # 2. ترحيل (للتوافق - البيانات محدثة مسبقاً)
            success, msg = ProductionInventoryService.post_finished_goods_receipt(
                receipt_data or {},
                production_order
            )
            
            if not success:
                return False, f"فشل ترحيل السند: {msg}", {}
            
            # 3. حساب تكلفة الوحدة وإنشاء القيد المحاسبي
            unit_cost = production_order.actual_total_cost / production_order.produced_quantity if production_order.produced_quantity > 0 else Decimal('0')
            
            success, msg, entry = ProductionAccountingService.create_finished_goods_entry(
                production_order,
                quantity,
                unit_cost,
                f"استلام منتجات تامة - أمر {production_order.number}"
            )
            
            if success and entry:
                entry.status = 'posted'
                entry.save()
            
            # 4. توليد الباركودات (اختياري)
            barcodes_generated = []
            if generate_barcodes:
                success_bc, msg_bc, units = ProductionInventoryService.generate_barcodes_for_finished_goods(
                    production_order,
                    int(quantity),
                    size_text
                )
                if success_bc:
                    barcodes_generated = [
                        {'serial': u.unit_serial, 'barcode': u.barcode, 'size': u.size_text}
                        for u in units
                    ]
            
            # 5. تحديث حالة الأمر
            production_order.refresh_from_db()
            
            return True, f"تم تسجيل إنتاج {quantity} وحدة بنجاح", {
                'receipt_data': receipt_data,
                'journal_entry_id': entry.id if entry else None,
                'quantity': float(quantity),
                'unit_cost': float(unit_cost),
                'total_cost': float(quantity * unit_cost),
                'barcodes': barcodes_generated,
                'order_status': production_order.status,
                'completion_percentage': float(production_order.completion_percentage)
            }
            
        except Exception as e:
            return False, f"خطأ في تسجيل الإنتاج: {str(e)}", {}
    
    @staticmethod
    @transaction.atomic
    def record_labor_cost(
        production_order: 'ProductionOrder',
        labor_cost: Decimal,
        description: str = ""
    ) -> Tuple[bool, str]:
        """
        تسجيل تكلفة العمالة لأمر الإنتاج
        
        Args:
            production_order: أمر الإنتاج
            labor_cost: تكلفة العمالة
            description: وصف
            
        Returns:
            (success, message)
        """
        try:
            # تحديث التكلفة في الأمر
            production_order.actual_labor_cost += labor_cost
            production_order.save(update_fields=['actual_labor_cost'])
            
            # إنشاء القيد المحاسبي
            success, msg, entry = ProductionAccountingService.create_labor_cost_entry(
                production_order,
                labor_cost,
                description or f"تكلفة عمالة - أمر {production_order.number}"
            )
            
            if success and entry:
                entry.status = 'posted'
                entry.save()
                return True, f"تم تسجيل تكلفة العمالة: {labor_cost}"
            else:
                return False, f"فشل إنشاء القيد المحاسبي: {msg}"
                
        except Exception as e:
            return False, f"خطأ في تسجيل تكلفة العمالة: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def calculate_and_apply_overhead(
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, str]:
        """
        حساب وتطبيق التكاليف الإضافية
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            (success, message)
        """
        try:
            # حساب التكاليف الإضافية
            overhead_cost = ProductionAccountingService.calculate_overhead_allocation(
                production_order
            )
            
            if overhead_cost <= 0:
                return True, "لا توجد تكاليف إضافية للتطبيق"
            
            # تحديث التكلفة في الأمر
            production_order.actual_overhead_cost = overhead_cost
            production_order.save(update_fields=['actual_overhead_cost'])
            
            # إنشاء القيد المحاسبي
            success, msg, entry = ProductionAccountingService.create_overhead_entry(
                production_order,
                overhead_cost,
                f"تكاليف إضافية - أمر {production_order.number}"
            )
            
            if success and entry:
                entry.status = 'posted'
                entry.save()
                return True, f"تم تطبيق التكاليف الإضافية: {overhead_cost}"
            else:
                return False, f"فشل إنشاء القيد المحاسبي: {msg}"
                
        except Exception as e:
            return False, f"خطأ في حساب التكاليف الإضافية: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def complete_production_order(
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, str, Dict]:
        """
        إكمال أمر الإنتاج:
        1. التحقق من اكتمال الكمية
        2. حساب التكاليف النهائية
        3. إنشاء القيود النهائية
        4. تحديث الحالة
        5. تحليل الانحرافات
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            (success, message, analysis_dict)
        """
        try:
            # التحقق من الحالة
            if production_order.status == 'completed':
                return False, "الأمر مكتمل مسبقاً", {}
            
            # 1. حساب التكاليف الإضافية إذا لم تكن محسوبة
            if production_order.actual_overhead_cost == 0:
                ProductionLifecycleService.calculate_and_apply_overhead(production_order)
            
            # 2. إنشاء جميع القيود المحاسبية المتبقية
            success, msg, entries = ProductionAccountingService.complete_production_order_accounting(
                production_order
            )
            
            # 3. تحديث الحالة
            production_order.status = 'completed'
            production_order.actual_end_date = timezone.now().date()
            production_order.save()
            
            # 4. تحليل الانحرافات
            variance_analysis = ProductionAccountingService.calculate_cost_variance(
                production_order
            )
            
            return True, "تم إكمال أمر الإنتاج بنجاح", {
                'order_number': production_order.number,
                'produced_quantity': float(production_order.produced_quantity),
                'planned_quantity': float(production_order.planned_quantity),
                'completion_percentage': float(production_order.completion_percentage),
                'total_cost': float(production_order.actual_total_cost),
                'unit_cost': float(production_order.unit_cost),
                'variance_analysis': variance_analysis,
                'journal_entries': [e.id for e in entries]
            }
            
        except Exception as e:
            return False, f"خطأ في إكمال أمر الإنتاج: {str(e)}", {}
    
    @staticmethod
    def get_order_status_summary(
        production_order: 'ProductionOrder'
    ) -> Dict:
        """
        الحصول على ملخص شامل لحالة أمر الإنتاج
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            قاموس يحتوي على كل التفاصيل
        """
        try:
            # حالة المواد
            all_available, materials_status = ProductionInventoryService.check_material_availability(
                production_order
            )
            
            # تحليل التكاليف
            variance_analysis = ProductionAccountingService.calculate_cost_variance(
                production_order
            )
            
            return {
                'order_info': {
                    'number': production_order.number,
                    'product': production_order.product.name,
                    'status': production_order.status,
                    'status_display': production_order.get_status_display(),
                    'priority': production_order.priority,
                    'priority_display': production_order.get_priority_display(),
                },
                'quantities': {
                    'planned': float(production_order.planned_quantity),
                    'produced': float(production_order.produced_quantity),
                    'remaining': float(production_order.remaining_quantity),
                    'scrap': float(production_order.scrap_quantity),
                    'completion_percentage': float(production_order.completion_percentage),
                },
                'dates': {
                    'order_date': str(production_order.order_date),
                    'planned_start': str(production_order.planned_start_date),
                    'planned_end': str(production_order.planned_end_date),
                    'actual_start': str(production_order.actual_start_date) if production_order.actual_start_date else None,
                    'actual_end': str(production_order.actual_end_date) if production_order.actual_end_date else None,
                },
                'costs': {
                    'estimated': {
                        'material': float(production_order.estimated_material_cost),
                        'labor': float(production_order.estimated_labor_cost),
                        'overhead': float(production_order.estimated_overhead_cost),
                        'total': float(production_order.estimated_total_cost),
                    },
                    'actual': {
                        'material': float(production_order.actual_material_cost),
                        'labor': float(production_order.actual_labor_cost),
                        'overhead': float(production_order.actual_overhead_cost),
                        'total': float(production_order.actual_total_cost),
                    },
                    'unit_cost': float(production_order.unit_cost),
                    'variance': variance_analysis,
                },
                'materials': {
                    'all_available': all_available,
                    'status': materials_status,
                },
            }
            
        except Exception as e:
            return {'error': str(e)}
