"""
خدمة تكامل الإنتاج مع المحاسبة
تتعامل مع:
- القيود المحاسبية لصرف المواد
- القيود المحاسبية لاستلام المنتجات التامة
- تكاليف العمالة والتكاليف الإضافية
- تحليل التكاليف والانحرافات
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any

from accounting.models import (
    Account, JournalEntry, JournalEntryItem, CostCenter
)
from production.models import (
    ProductionOrder, ProductionSettings, MaterialConsumption,
    ProductionTimeLog, ProductionOrderStage
)


class ProductionAccountingService:
    """خدمة إدارة تكامل الإنتاج والمحاسبة"""
    
    @staticmethod
    def get_production_accounts() -> Dict[str, Optional[Account]]:
        """الحصول على الحسابات المحاسبية للإنتاج"""
        try:
            settings = ProductionSettings.objects.first()
            if settings is None:
                return {}
            
            return {
                'wip': settings.wip_account,  # حساب الإنتاج تحت التشغيل
                'finished_goods': settings.finished_goods_account,  # البضائع التامة
                'raw_materials': settings.raw_materials_account,  # المواد الخام
                'labor_cost': settings.labor_cost_account,  # تكلفة العمالة
                'overhead': settings.overhead_account,  # التكاليف الإضافية
            }
        except Exception:
            return {}
    
    @staticmethod
    @transaction.atomic
    def create_material_issue_entry(
        production_order: 'ProductionOrder',
        material_cost: Decimal,
        description: str = "",
        cost_center: Optional['CostCenter'] = None
    ) -> Tuple[bool, str, Optional['JournalEntry']]:
        """
        إنشاء قيد صرف المواد الخام للإنتاج
        
        القيد:
        من ح/ الإنتاج تحت التشغيل (WIP)
            إلى ح/ المواد الخام
        
        Args:
            production_order: أمر الإنتاج
            material_cost: قيمة المواد المصروفة
            description: وصف القيد
            cost_center: مركز التكلفة
            
        Returns:
            (success, message, journal_entry)
        """
        try:
            accounts = ProductionAccountingService.get_production_accounts()
            
            if not accounts.get('wip') or not accounts.get('raw_materials'):
                return False, "لم يتم تكوين حسابات الإنتاج في الإعدادات", None
            
            # إنشاء القيد
            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=description or f"صرف مواد خام لأمر إنتاج {production_order.number}",
                reference_type='production_order',
                reference_id=production_order.id,
                total_debit=material_cost,
                total_credit=material_cost,
                status='draft'
            )
            
            # الجانب المدين: WIP
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['wip'],
                debit=material_cost,
                credit=Decimal('0'),
                description=f"تكلفة مواد - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            # الجانب الدائن: المواد الخام
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['raw_materials'],
                debit=Decimal('0'),
                credit=material_cost,
                description=f"صرف مواد - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            return True, f"تم إنشاء قيد محاسبي رقم {entry.id}", entry
            
        except Exception as e:
            return False, f"خطأ في إنشاء القيد: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def create_labor_cost_entry(
        production_order: 'ProductionOrder',
        labor_cost: Decimal,
        description: str = "",
        cost_center: Optional['CostCenter'] = None
    ) -> Tuple[bool, str, Optional['JournalEntry']]:
        """
        إنشاء قيد تكلفة العمالة
        
        القيد:
        من ح/ الإنتاج تحت التشغيل (WIP)
            إلى ح/ تكلفة العمالة
        
        Args:
            production_order: أمر الإنتاج
            labor_cost: تكلفة العمالة
            description: وصف القيد
            cost_center: مركز التكلفة
            
        Returns:
            (success, message, journal_entry)
        """
        try:
            accounts = ProductionAccountingService.get_production_accounts()
            
            if not accounts.get('wip') or not accounts.get('labor_cost'):
                return False, "لم يتم تكوين حسابات الإنتاج في الإعدادات", None
            
            # إنشاء القيد
            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=description or f"تكلفة عمالة لأمر إنتاج {production_order.number}",
                reference_type='production_order',
                reference_id=production_order.id,
                total_debit=labor_cost,
                total_credit=labor_cost,
                status='draft'
            )
            
            # الجانب المدين: WIP
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['wip'],
                debit=labor_cost,
                credit=Decimal('0'),
                description=f"تكلفة عمالة - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            # الجانب الدائن: تكلفة العمالة
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['labor_cost'],
                debit=Decimal('0'),
                credit=labor_cost,
                description=f"عمالة مباشرة - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            return True, f"تم إنشاء قيد تكلفة العمالة رقم {entry.id}", entry
            
        except Exception as e:
            return False, f"خطأ في إنشاء القيد: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def create_overhead_entry(
        production_order: 'ProductionOrder',
        overhead_cost: Decimal,
        description: str = "",
        cost_center: Optional['CostCenter'] = None
    ) -> Tuple[bool, str, Optional['JournalEntry']]:
        """
        إنشاء قيد التكاليف الإضافية (Overhead)
        
        القيد:
        من ح/ الإنتاج تحت التشغيل (WIP)
            إلى ح/ التكاليف الإضافية
        
        Args:
            production_order: أمر الإنتاج
            overhead_cost: التكاليف الإضافية
            description: وصف القيد
            cost_center: مركز التكلفة
            
        Returns:
            (success, message, journal_entry)
        """
        try:
            accounts = ProductionAccountingService.get_production_accounts()
            
            if not accounts.get('wip') or not accounts.get('overhead'):
                return False, "لم يتم تكوين حسابات الإنتاج في الإعدادات", None
            
            # إنشاء القيد
            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=description or f"تكاليف إضافية لأمر إنتاج {production_order.number}",
                reference_type='production_order',
                reference_id=production_order.id,
                total_debit=overhead_cost,
                total_credit=overhead_cost,
                status='draft'
            )
            
            # الجانب المدين: WIP
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['wip'],
                debit=overhead_cost,
                credit=Decimal('0'),
                description=f"تكاليف إضافية - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            # الجانب الدائن: التكاليف الإضافية
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['overhead'],
                debit=Decimal('0'),
                credit=overhead_cost,
                description=f"تحميل تكاليف - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            return True, f"تم إنشاء قيد التكاليف الإضافية رقم {entry.id}", entry
            
        except Exception as e:
            return False, f"خطأ في إنشاء القيد: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def create_finished_goods_entry(
        production_order: 'ProductionOrder',
        quantity: Decimal,
        unit_cost: Decimal,
        description: str = "",
        cost_center: Optional['CostCenter'] = None
    ) -> Tuple[bool, str, Optional['JournalEntry']]:
        """
        إنشاء قيد نقل المنتجات التامة
        
        القيد:
        من ح/ البضائع التامة
            إلى ح/ الإنتاج تحت التشغيل (WIP)
        
        Args:
            production_order: أمر الإنتاج
            quantity: الكمية المنتجة
            unit_cost: تكلفة الوحدة
            description: وصف القيد
            cost_center: مركز التكلفة
            
        Returns:
            (success, message, journal_entry)
        """
        try:
            accounts = ProductionAccountingService.get_production_accounts()
            
            if not accounts.get('wip') or not accounts.get('finished_goods'):
                return False, "لم يتم تكوين حسابات الإنتاج في الإعدادات", None
            
            total_cost = quantity * unit_cost
            
            # إنشاء القيد
            entry = JournalEntry.objects.create(
                date=timezone.now().date(),
                description=description or f"نقل منتجات تامة من أمر {production_order.number}",
                reference_type='production_order',
                reference_id=production_order.id,
                total_debit=total_cost,
                total_credit=total_cost,
                status='draft'
            )
            
            # الجانب المدين: البضائع التامة
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['finished_goods'],
                debit=total_cost,
                credit=Decimal('0'),
                description=f"منتجات تامة {quantity} وحدة - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            # الجانب الدائن: WIP
            JournalEntryItem.objects.create(
                journal_entry=entry,
                account=accounts['wip'],
                debit=Decimal('0'),
                credit=total_cost,
                description=f"نقل من WIP - أمر {production_order.number}",
                cost_center=cost_center
            )
            
            return True, f"تم إنشاء قيد المنتجات التامة رقم {entry.id}", entry
            
        except Exception as e:
            return False, f"خطأ في إنشاء القيد: {str(e)}", None
    
    @staticmethod
    @transaction.atomic
    def complete_production_order_accounting(
        production_order: 'ProductionOrder'
    ) -> Tuple[bool, str, List['JournalEntry']]:
        """
        إتمام جميع القيود المحاسبية لأمر إنتاج مكتمل
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            (success, message, list_of_entries)
        """
        try:
            entries = []
            
            # 1. قيد المواد (إذا لم يكن موجوداً)
            if production_order.actual_material_cost > 0:
                success, msg, entry = ProductionAccountingService.create_material_issue_entry(
                    production_order,
                    production_order.actual_material_cost,
                    f"إجمالي تكلفة المواد - أمر {production_order.number}"
                )
                if success and entry:
                    entry.status = 'posted'
                    entry.save()
                    entries.append(entry)
            
            # 2. قيد العمالة
            if production_order.actual_labor_cost > 0:
                success, msg, entry = ProductionAccountingService.create_labor_cost_entry(
                    production_order,
                    production_order.actual_labor_cost,
                    f"إجمالي تكلفة العمالة - أمر {production_order.number}"
                )
                if success and entry:
                    entry.status = 'posted'
                    entry.save()
                    entries.append(entry)
            
            # 3. قيد التكاليف الإضافية
            if production_order.actual_overhead_cost > 0:
                success, msg, entry = ProductionAccountingService.create_overhead_entry(
                    production_order,
                    production_order.actual_overhead_cost,
                    f"إجمالي التكاليف الإضافية - أمر {production_order.number}"
                )
                if success and entry:
                    entry.status = 'posted'
                    entry.save()
                    entries.append(entry)
            
            # 4. قيد المنتجات التامة
            if production_order.produced_quantity > 0:
                unit_cost = production_order.actual_total_cost / production_order.produced_quantity
                success, msg, entry = ProductionAccountingService.create_finished_goods_entry(
                    production_order,
                    production_order.produced_quantity,
                    unit_cost,
                    f"منتجات تامة - أمر {production_order.number}"
                )
                if success and entry:
                    entry.status = 'posted'
                    entry.save()
                    entries.append(entry)
            
            return True, f"تم إنشاء {len(entries)} قيد محاسبي", entries
            
        except Exception as e:
            return False, f"خطأ في إتمام القيود: {str(e)}", []
    
    @staticmethod
    def calculate_cost_variance(
        production_order: 'ProductionOrder'
    ) -> Dict[str, Any]:
        """
        حساب انحرافات التكلفة
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            قاموس يحتوي على تفاصيل الانحرافات
        """
        try:
            # انحراف المواد
            material_variance = production_order.actual_material_cost - production_order.estimated_material_cost
            material_variance_pct = (
                (material_variance / production_order.estimated_material_cost * 100)
                if production_order.estimated_material_cost > 0 else 0
            )
            
            # انحراف العمالة
            labor_variance = production_order.actual_labor_cost - production_order.estimated_labor_cost
            labor_variance_pct = (
                (labor_variance / production_order.estimated_labor_cost * 100)
                if production_order.estimated_labor_cost > 0 else 0
            )
            
            # انحراف التكاليف الإضافية
            overhead_variance = production_order.actual_overhead_cost - production_order.estimated_overhead_cost
            overhead_variance_pct = (
                (overhead_variance / production_order.estimated_overhead_cost * 100)
                if production_order.estimated_overhead_cost > 0 else 0
            )
            
            # الانحراف الكلي
            total_variance = production_order.cost_variance
            total_variance_pct = (
                (total_variance / production_order.estimated_total_cost * 100)
                if production_order.estimated_total_cost > 0 else 0
            )
            
            return {
                'material': {
                    'estimated': float(production_order.estimated_material_cost),
                    'actual': float(production_order.actual_material_cost),
                    'variance': float(material_variance),
                    'variance_pct': float(material_variance_pct),
                    'status': 'favorable' if material_variance < 0 else 'unfavorable'
                },
                'labor': {
                    'estimated': float(production_order.estimated_labor_cost),
                    'actual': float(production_order.actual_labor_cost),
                    'variance': float(labor_variance),
                    'variance_pct': float(labor_variance_pct),
                    'status': 'favorable' if labor_variance < 0 else 'unfavorable'
                },
                'overhead': {
                    'estimated': float(production_order.estimated_overhead_cost),
                    'actual': float(production_order.actual_overhead_cost),
                    'variance': float(overhead_variance),
                    'variance_pct': float(overhead_variance_pct),
                    'status': 'favorable' if overhead_variance < 0 else 'unfavorable'
                },
                'total': {
                    'estimated': float(production_order.estimated_total_cost),
                    'actual': float(production_order.actual_total_cost),
                    'variance': float(total_variance),
                    'variance_pct': float(total_variance_pct),
                    'status': 'favorable' if total_variance < 0 else 'unfavorable'
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def calculate_overhead_allocation(
        production_order: 'ProductionOrder'
    ) -> Decimal:
        """
        حساب التكاليف الإضافية المخصصة لأمر الإنتاج
        
        Args:
            production_order: أمر الإنتاج
            
        Returns:
            قيمة التكاليف الإضافية المحسوبة
        """
        try:
            settings = ProductionSettings.objects.first()
            if not settings:
                return Decimal('0')
            
            method = settings.overhead_allocation_method
            rate = settings.overhead_rate
            
            if method == 'labor_hours':
                # حساب إجمالي ساعات العمل
                total_hours = ProductionTimeLog.objects.filter(
                    production_order=production_order
                ).aggregate(
                    total=models.Sum('duration_hours')
                )['total'] or Decimal('0')
                
                return total_hours * rate
                
            elif method == 'labor_cost':
                # نسبة من تكلفة العمالة
                return production_order.actual_labor_cost * rate
                
            elif method == 'material_cost':
                # نسبة من تكلفة المواد
                return production_order.actual_material_cost * rate
                
            elif method == 'machine_hours':
                # حساب ساعات التشغيل
                machine_hours = ProductionTimeLog.objects.filter(
                    production_order=production_order,
                    activity_type='operation'
                ).aggregate(
                    total=models.Sum('duration_hours')
                )['total'] or Decimal('0')
                
                return machine_hours * rate
            
            return Decimal('0')
            
        except Exception:
            return Decimal('0')
