"""
محرك المشتريات
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.purchases.models import PurchaseOrder, PurchaseOrderLine
from apps.inventory.services.stock_engine import StockEngine
from apps.accounts.services.journal_engine import JournalEngine
from apps.accounts.services.vat_engine import VATEngine


class PurchaseEngine:

    @staticmethod
    def _generate_order_number():
        today = timezone.now()
        count = PurchaseOrder.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1
        return f"PO-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_purchase_order(cls, supplier, branch, warehouse, items,
                              is_taxable=True, notes='', user=None):
        """
        إنشاء أمر شراء
        items = [{'product': obj, 'quantity': 100, 'unit_cost': 50}, ...]
        """
        order = PurchaseOrder.objects.create(
            order_number=cls._generate_order_number(),
            date=timezone.now(),
            supplier=supplier,
            branch=branch,
            warehouse=warehouse,
            is_taxable=is_taxable,
            notes=notes,
            created_by=user,
            updated_by=user,
        )

        subtotal = Decimal('0')
        for item in items:
            line_total = Decimal(str(item['quantity'])) * Decimal(str(item['unit_cost']))
            PurchaseOrderLine.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                unit_cost=item['unit_cost'],
                total=line_total,
            )
            subtotal += line_total

        tax_amount = Decimal('0')
        if is_taxable:
            vat = VATEngine.calculate_tax(subtotal)
            tax_amount = vat['tax_amount']

        order.subtotal = subtotal
        order.tax_amount = tax_amount
        order.total = subtotal + tax_amount
        order.remaining_amount = order.total
        order.save()
        return order

    @classmethod
    @transaction.atomic
    def receive_purchase(cls, order, user=None):
        """
        استلام أمر شراء — إضافة للمخزون + قيد
        """
        if order.status not in ('draft', 'confirmed'):
            raise ValueError("الأمر ليس في حالة تسمح بالاستلام")

        for line in order.lines.all():
            StockEngine.receive_stock(
                product=line.product,
                warehouse=order.warehouse,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                source_type='PurchaseOrder',
                source_id=str(order.id),
                notes=f'شراء من {order.supplier.name} - أمر {order.order_number}',
                user=user,
            )
            line.received_quantity = line.quantity
            line.save()

        # قيد المشتريات
        lines_data = [
            {
                'account_code': '1141',
                'debit': order.subtotal,
                'credit': 0,
                'description': f'شراء خامات - {order.order_number}',
            }
        ]

        if order.is_taxable and order.tax_amount > 0:
            lines_data.append({
                'account_code': '115',
                'debit': order.tax_amount,
                'credit': 0,
                'description': f'ضريبة مشتريات - {order.order_number}',
            })

        supplier_account = order.supplier.account.code if order.supplier.account else '2111'
        lines_data.append({
            'account_code': supplier_account,
            'debit': 0,
            'credit': order.total,
            'description': f'شراء من {order.supplier.name}',
            'partner_type': 'supplier',
            'partner_id': order.supplier.id,
        })

        entry = JournalEngine.create_entry(
            source='purchase',
            description=f'شراء - {order.order_number} - {order.supplier.name}',
            branch=order.branch,
            lines_data=lines_data,
            source_document=order.order_number,
            user=user,
            auto_post=True,
        )

        if order.is_taxable and order.tax_amount > 0:
            VATEngine.record_tax_transaction(
                tax_type='input',
                amount_before_tax=order.subtotal,
                tax_amount=order.tax_amount,
                journal_entry=entry,
            )

        order.journal_entry = entry
        order.status = 'received'
        order.updated_by = user
        order.save()
        return order
