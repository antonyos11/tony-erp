"""
محرك التكاليف الصناعية — RITA ERP Sprint 22B
═══════════════════════════════════════════════
يُدير:
1. تحميل التكاليف على أوامر الإنتاج
2. حساب WIP
3. إقفال أمر إنتاج محاسبياً
4. حساب تكلفة الوحدة الفعلية
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from apps.accounts.models import CostAllocation, WIPAccount
from apps.accounts.services.journal_engine import JournalEngine


class ManufacturingCostEngine:

    # ═══════════════════════════════
    # تحميل خامات
    # ═══════════════════════════════

    @classmethod
    @transaction.atomic
    def allocate_material_cost(cls, production_order, materials, user=None):
        """
        تحميل تكلفة الخامات المصروفة على أمر الإنتاج
        materials: [{'product': obj, 'quantity': 10, 'unit_cost': 50}, ...]

        القيد:
        من حـ/ إنتاج تحت التشغيل (WIP) — 131
        إلى حـ/ مخزون الخامات — 121
        """
        total = Decimal('0')
        for mat in materials:
            amount = Decimal(str(mat['quantity'])) * Decimal(str(mat['unit_cost']))
            CostAllocation.objects.create(
                production_order=production_order,
                cost_center=cls._get_production_cost_center(production_order),
                cost_type='material',
                description=f"خامة: {mat['product'].name} × {mat['quantity']}",
                amount=amount,
                date=timezone.now().date(),
                created_by=user, updated_by=user,
            )
            total += amount

        # القيد المحاسبي
        branch = production_order.branch if hasattr(production_order, 'branch') else None
        entry = JournalEngine.create_entry(
            source='production',
            description=f"صرف خامات لأمر إنتاج {production_order.order_number}",
            branch=branch,
            lines_data=[
                {'account_code': '131', 'debit': total, 'credit': 0,
                 'description': f'WIP - خامات - {production_order.order_number}'},
                {'account_code': '121', 'debit': 0, 'credit': total,
                 'description': f'صرف خامات - {production_order.order_number}'},
            ],
            source_document=production_order.order_number,
            user=user, auto_post=True,
        )

        cls._update_wip(production_order)
        return total, entry

    # ═══════════════════════════════
    # تحميل عمالة
    # ═══════════════════════════════

    @classmethod
    @transaction.atomic
    def allocate_labor_cost(cls, production_order, amount, description='', user=None):
        """
        تحميل تكلفة العمالة المباشرة

        القيد:
        من حـ/ إنتاج تحت التشغيل (WIP) — 131
        إلى حـ/ أجور مستحقة — 212
        """
        CostAllocation.objects.create(
            production_order=production_order,
            cost_center=cls._get_production_cost_center(production_order),
            cost_type='labor',
            description=description or f"عمالة مباشرة - {production_order.order_number}",
            amount=amount,
            date=timezone.now().date(),
            created_by=user, updated_by=user,
        )

        branch = production_order.branch if hasattr(production_order, 'branch') else None
        entry = JournalEngine.create_entry(
            source='production',
            description=f"عمالة مباشرة - {production_order.order_number}",
            branch=branch,
            lines_data=[
                {'account_code': '131', 'debit': amount, 'credit': 0,
                 'description': f'WIP - عمالة - {production_order.order_number}'},
                {'account_code': '212', 'debit': 0, 'credit': amount,
                 'description': f'أجور مستحقة - {production_order.order_number}'},
            ],
            source_document=production_order.order_number,
            user=user, auto_post=True,
        )

        cls._update_wip(production_order)
        return entry

    # ═══════════════════════════════
    # تحميل overhead
    # ═══════════════════════════════

    @classmethod
    @transaction.atomic
    def allocate_overhead(cls, production_order, amount, cost_type='overhead', description='', user=None):
        """
        تحميل تكاليف غير مباشرة (كهرباء، إهلاك، صيانة، إلخ)

        القيد:
        من حـ/ إنتاج تحت التشغيل (WIP) — 131
        إلى حـ/ تكاليف صناعية غير مباشرة — 513
        """
        CostAllocation.objects.create(
            production_order=production_order,
            cost_center=cls._get_production_cost_center(production_order),
            cost_type=cost_type,
            description=description or f"تكاليف غير مباشرة - {production_order.order_number}",
            amount=amount,
            date=timezone.now().date(),
            created_by=user, updated_by=user,
        )

        branch = production_order.branch if hasattr(production_order, 'branch') else None
        entry = JournalEngine.create_entry(
            source='production',
            description=f"تكاليف غير مباشرة - {production_order.order_number}",
            branch=branch,
            lines_data=[
                {'account_code': '131', 'debit': amount, 'credit': 0,
                 'description': f'WIP - overhead - {production_order.order_number}'},
                {'account_code': '513', 'debit': 0, 'credit': amount,
                 'description': f'ت. غير مباشرة - {production_order.order_number}'},
            ],
            source_document=production_order.order_number,
            user=user, auto_post=True,
        )

        cls._update_wip(production_order)
        return entry

    # ═══════════════════════════════
    # إقفال أمر إنتاج
    # ═══════════════════════════════

    @classmethod
    @transaction.atomic
    def close_production_order(cls, production_order, user=None):
        """
        إقفال أمر إنتاج محاسبياً
        تحويل من WIP إلى مخزون المنتجات التامة

        القيد:
        من حـ/ مخزون منتجات تامة — 122
        إلى حـ/ إنتاج تحت التشغيل (WIP) — 131
        """
        wip = cls._get_or_create_wip(production_order)

        if wip.is_closed:
            raise ValueError("أمر الإنتاج مُقفل محاسبياً بالفعل!")

        wip.recalculate()
        total = wip.total_cost

        if total <= 0:
            raise ValueError("لا توجد تكاليف محمّلة على هذا الأمر!")

        branch = production_order.branch if hasattr(production_order, 'branch') else None
        entry = JournalEngine.create_entry(
            source='production',
            description=f"إقفال إنتاج - {production_order.order_number} - تكلفة فعلية: {total}",
            branch=branch,
            lines_data=[
                {'account_code': '122', 'debit': total, 'credit': 0,
                 'description': f'منتجات تامة - {production_order.product.name}'},
                {'account_code': '131', 'debit': 0, 'credit': total,
                 'description': f'إقفال WIP - {production_order.order_number}'},
            ],
            source_document=production_order.order_number,
            user=user, auto_post=True,
        )

        wip.is_closed = True
        wip.closed_at = timezone.now()
        wip.save()

        # تحديث تكلفة المنتج الفعلية
        product = production_order.product
        qty = production_order.quantity_produced or production_order.quantity
        if qty > 0:
            product.cost_price = wip.unit_cost
            product.save()

        return wip, entry

    # ═══════════════════════════════
    # تقارير التكلفة
    # ═══════════════════════════════

    @classmethod
    def get_production_cost_report(cls, production_order):
        """تقرير تكلفة أمر إنتاج"""
        wip = cls._get_or_create_wip(production_order)
        wip.recalculate()

        allocations = production_order.cost_allocations.all()

        return {
            'order': production_order,
            'material_cost': wip.material_cost,
            'labor_cost': wip.labor_cost,
            'overhead_cost': wip.overhead_cost,
            'total_cost': wip.total_cost,
            'unit_cost': wip.unit_cost,
            'quantity': production_order.quantity_produced or production_order.quantity,
            'is_closed': wip.is_closed,
            'allocations': allocations,
            'material_breakdown': allocations.filter(cost_type='material'),
            'labor_breakdown': allocations.filter(cost_type='labor'),
            'overhead_breakdown': allocations.filter(
                cost_type__in=['overhead', 'depreciation', 'utility', 'other']
            ),
        }

    @classmethod
    def get_wip_summary(cls):
        """ملخص كل أوامر الإنتاج المفتوحة (WIP)"""
        open_wips = WIPAccount.objects.filter(is_closed=False).select_related(
            'production_order', 'production_order__product'
        )

        total_wip = open_wips.aggregate(total=Sum('total_cost'))['total'] or 0

        return {
            'open_orders': open_wips,
            'total_wip_value': total_wip,
            'count': open_wips.count(),
        }

    @classmethod
    def get_unit_cost_comparison(cls, product, last_n=10):
        """مقارنة تكلفة الوحدة عبر أوامر الإنتاج"""
        wips = WIPAccount.objects.filter(
            production_order__product=product,
            is_closed=True,
        ).order_by('-closed_at')[:last_n]

        return [{
            'order_number': w.production_order.order_number,
            'date': w.closed_at,
            'quantity': w.production_order.quantity_produced,
            'unit_cost': w.unit_cost,
            'total_cost': w.total_cost,
        } for w in wips]

    # ═══════════════════════════════
    # Helper
    # ═══════════════════════════════

    @classmethod
    def _get_or_create_wip(cls, production_order):
        wip, _ = WIPAccount.objects.get_or_create(production_order=production_order)
        return wip

    @classmethod
    def _update_wip(cls, production_order):
        wip = cls._get_or_create_wip(production_order)
        wip.recalculate()
        return wip

    @classmethod
    def _get_production_cost_center(cls, production_order):
        from apps.accounts.models import CostCenter
        if hasattr(production_order, 'production_line') and production_order.production_line:
            cc = CostCenter.objects.filter(
                center_type='product_line',
            ).first()
            if cc:
                return cc
        return None
