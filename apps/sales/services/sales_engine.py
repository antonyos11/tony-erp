"""
محرك المبيعات
إنشاء فواتير + خصم مخزون + قيود تلقائية + ضريبة
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.sales.models import SalesInvoice, SalesInvoiceLine, SalesReturn, Customer
from apps.inventory.services.stock_engine import StockEngine
from apps.inventory.models import StockLevel
from apps.accounts.services.journal_engine import JournalEngine
from apps.accounts.services.vat_engine import VATEngine


class SalesEngine:
    """محرك المبيعات"""

    @staticmethod
    def _generate_invoice_number():
        today = timezone.now()
        count = SalesInvoice.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1
        return f"INV-{today.strftime('%Y%m')}-{count:04d}"

    @staticmethod
    def _generate_return_number():
        today = timezone.now()
        count = SalesReturn.objects.filter(
            date__year=today.year, date__month=today.month
        ).count() + 1
        return f"RET-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_invoice(cls, customer, branch, warehouse, salesperson,
                       items, payment_method='cash', sale_channel='branch',
                       discount_percentage=0, is_taxable=True,
                       delivery_required=False, delivery_address='', delivery_fee=0,
                       notes='', user=None):
        """
        إنشاء فاتورة بيع كاملة

        items = [
            {'product': product_obj, 'quantity': 5, 'unit_price': 200, 'discount_percentage': 0},
            ...
        ]
        """
        invoice = SalesInvoice.objects.create(
            invoice_number=cls._generate_invoice_number(),
            date=timezone.now(),
            customer=customer,
            branch=branch,
            warehouse=warehouse,
            salesperson=salesperson,
            status='draft',
            payment_method=payment_method,
            sale_channel=sale_channel,
            price_list=customer.price_list,
            discount_percentage=discount_percentage,
            is_taxable=is_taxable,
            delivery_required=delivery_required,
            delivery_address=delivery_address,
            delivery_fee=delivery_fee,
            notes=notes,
            created_by=user,
            updated_by=user,
        )

        subtotal = Decimal('0')
        total_discount = Decimal('0')
        total_cost = Decimal('0')

        for item in items:
            product = item['product']
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            item_discount_pct = Decimal(str(item.get('discount_percentage', 0)))

            line_total = quantity * unit_price
            line_discount = line_total * item_discount_pct / 100
            line_subtotal = line_total - line_discount

            # تكلفة المنتج الفعلية
            stock = StockLevel.objects.filter(product=product, warehouse=warehouse).first()
            cost_price = stock.average_cost if stock else product.cost_price
            line_cost = cost_price * quantity
            line_profit = line_subtotal - line_cost

            SalesInvoiceLine.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount_percentage=item_discount_pct,
                discount_amount=line_discount,
                subtotal=line_subtotal,
                cost_price=cost_price,
                profit=line_profit,
                custom_width=item.get('custom_width'),
                custom_length=item.get('custom_length'),
                notes=item.get('notes', ''),
            )

            subtotal += line_subtotal
            total_discount += line_discount
            total_cost += line_cost

        # خصم إجمالي على الفاتورة
        invoice_discount = subtotal * Decimal(str(discount_percentage)) / 100
        taxable_amount = subtotal - invoice_discount

        # حساب الضريبة
        tax_amount = Decimal('0')
        if is_taxable:
            vat = VATEngine.calculate_tax(taxable_amount)
            tax_amount = vat['tax_amount']

        total = taxable_amount + tax_amount + Decimal(str(delivery_fee))

        invoice.subtotal = subtotal
        invoice.discount_amount = invoice_discount + total_discount
        invoice.taxable_amount = taxable_amount
        invoice.tax_amount = tax_amount
        invoice.total = total
        invoice.remaining_amount = total
        invoice.save()

        return invoice

    @classmethod
    @transaction.atomic
    def confirm_invoice(cls, invoice, user=None):
        """
        تأكيد الفاتورة — خصم المخزون + إنشاء القيود
        """
        if invoice.status != 'draft':
            raise ValueError("الفاتورة ليست في حالة مسودة")

        # خصم المخزون
        for line in invoice.lines.all():
            StockEngine.issue_stock(
                product=line.product,
                warehouse=invoice.warehouse,
                quantity=line.quantity,
                source_type='SalesInvoice',
                source_id=str(invoice.id),
                notes=f'بيع - فاتورة {invoice.invoice_number}',
                user=user,
            )

        # إنشاء القيد المحاسبي
        entry = JournalEngine.create_sale_entry(invoice, user=user)
        invoice.journal_entry = entry

        # تسجيل الضريبة
        if invoice.is_taxable and invoice.tax_amount > 0:
            VATEngine.record_tax_transaction(
                tax_type='output',
                amount_before_tax=invoice.taxable_amount,
                tax_amount=invoice.tax_amount,
                journal_entry=entry,
            )

        # تحديث حالة الدفع
        if invoice.payment_method == 'cash':
            invoice.paid_amount = invoice.total
            invoice.remaining_amount = Decimal('0')
            invoice.status = 'paid'
        else:
            invoice.status = 'confirmed'

        invoice.updated_by = user
        invoice.save()
        return invoice

    @classmethod
    @transaction.atomic
    def record_payment(cls, invoice, amount, payment_method='cash', user=None):
        """
        تسجيل دفعة على فاتورة
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("مبلغ الدفع يجب أن يكون موجباً")
        if amount > invoice.remaining_amount:
            raise ValueError(f"المبلغ ({amount}) أكبر من المتبقي ({invoice.remaining_amount})")

        invoice.paid_amount += amount
        invoice.remaining_amount -= amount

        if invoice.remaining_amount <= 0:
            invoice.status = 'paid'
        else:
            invoice.status = 'partial_paid'

        invoice.updated_by = user
        invoice.save()
        return invoice

    @classmethod
    @transaction.atomic
    def create_return(cls, original_invoice, items, reason, user=None):
        """
        إنشاء مرتجع مبيعات

        items = [
            {'product': product_obj, 'quantity': 2},
            ...
        ]
        """
        total = Decimal('0')

        sales_return = SalesReturn.objects.create(
            return_number=cls._generate_return_number(),
            date=timezone.now(),
            original_invoice=original_invoice,
            customer=original_invoice.customer,
            branch=original_invoice.branch,
            status='draft',
            reason=reason,
            created_by=user,
            updated_by=user,
        )

        for item in items:
            # البحث عن السطر الأصلي للحصول على السعر
            original_line = original_invoice.lines.filter(product=item['product']).first()
            if original_line:
                line_total = Decimal(str(item['quantity'])) * original_line.unit_price
                total += line_total

        sales_return.total = total
        sales_return.save()
        return sales_return

    @classmethod
    @transaction.atomic
    def approve_return(cls, sales_return, user=None):
        """
        اعتماد المرتجع — إرجاع المخزون + قيد عكسي
        """
        if sales_return.status != 'draft':
            raise ValueError("المرتجع ليس في حالة مسودة")

        # إرجاع المخزون
        original_invoice = sales_return.original_invoice
        for line in original_invoice.lines.all():
            StockEngine.receive_stock(
                product=line.product,
                warehouse=original_invoice.warehouse,
                quantity=line.quantity,
                unit_cost=line.cost_price,
                source_type='SalesReturn',
                source_id=str(sales_return.id),
                notes=f'مرتجع - {sales_return.return_number}',
                user=user,
            )

        # قيد المرتجع
        entry = JournalEngine.create_sales_return_entry(sales_return, user=user)
        sales_return.journal_entry = entry
        sales_return.status = 'completed'
        sales_return.updated_by = user
        sales_return.save()
        return sales_return
