"""
محرك القيود المحاسبية التلقائية
كل عملية في النظام تنشئ قيد محاسبي تلقائياً من خلال هذا المحرك
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import JournalEntry, JournalLine, Account, FiscalYear, TaxTransaction


class JournalEngine:
    """محرك القيود التلقائية"""

    @staticmethod
    def _get_active_fiscal_year():
        """جلب السنة المالية النشطة"""
        try:
            return FiscalYear.objects.get(is_active=True, is_closed=False)
        except FiscalYear.DoesNotExist:
            raise ValueError("لا توجد سنة مالية نشطة. يرجى إنشاء سنة مالية أولاً.")

    @staticmethod
    def _get_account(code):
        """جلب حساب بالكود"""
        try:
            return Account.objects.get(code=code, is_active=True)
        except Account.DoesNotExist:
            raise ValueError(f"الحساب رقم {code} غير موجود أو غير نشط")

    @staticmethod
    def _generate_entry_number(source):
        """توليد رقم قيد تلقائي"""
        today = timezone.now()
        prefix_map = {
            'manual':     'MAN',
            'purchase':   'PUR',
            'sale':       'SAL',
            'production': 'PRD',
            'stock_move': 'STK',
            'payroll':    'PAY',
            'expense':    'EXP',
            'adjustment': 'ADJ',
        }
        prefix = prefix_map.get(source, 'GEN')
        count = JournalEntry.objects.filter(
            date__year=today.year,
            date__month=today.month,
            source=source
        ).count() + 1
        return f"{prefix}-{today.strftime('%Y%m')}-{count:04d}"

    @classmethod
    @transaction.atomic
    def create_entry(cls, source, description, branch, lines_data,
                     source_document='', user=None, auto_post=False):
        """
        إنشاء قيد محاسبي

        lines_data = [
            {'account_code': '1111', 'debit': 1000, 'credit': 0, 'description': 'بيان', 'cost_center': None},
            {'account_code': '411',  'debit': 0, 'credit': 877.19, 'description': 'بيان', 'cost_center': None},
            {'account_code': '213',  'debit': 0, 'credit': 122.81, 'description': 'ضريبة', 'cost_center': None},
        ]
        """
        fiscal_year = cls._get_active_fiscal_year()
        entry_number = cls._generate_entry_number(source)

        # حساب الإجماليات
        total_debit  = sum(Decimal(str(line.get('debit',  0))) for line in lines_data)
        total_credit = sum(Decimal(str(line.get('credit', 0))) for line in lines_data)

        # التحقق من توازن القيد
        if total_debit != total_credit:
            raise ValueError(
                f"القيد غير متوازن! المدين: {total_debit} ≠ الدائن: {total_credit}"
            )

        if total_debit == 0:
            raise ValueError("لا يمكن إنشاء قيد بقيمة صفر")

        # إنشاء القيد
        entry = JournalEntry.objects.create(
            entry_number=entry_number,
            date=timezone.now().date(),
            fiscal_year=fiscal_year,
            description=description,
            source=source,
            source_document=source_document,
            status='posted' if auto_post else 'draft',
            branch=branch,
            total_debit=total_debit,
            total_credit=total_credit,
            created_by=user,
            updated_by=user,
        )

        # إنشاء سطور القيد
        for line_data in lines_data:
            account = cls._get_account(line_data['account_code'])

            if not account.is_detail:
                raise ValueError(f"لا يمكن القيد على حساب رئيسي: {account.code} - {account.name}")

            JournalLine.objects.create(
                entry=entry,
                account=account,
                debit=Decimal(str(line_data.get('debit', 0))),
                credit=Decimal(str(line_data.get('credit', 0))),
                description=line_data.get('description', ''),
                cost_center=line_data.get('cost_center'),
                partner_type=line_data.get('partner_type', ''),
                partner_id=line_data.get('partner_id'),
            )

        return entry

    # ══════════════════════════════════════════
    # القيود التلقائية الجاهزة
    # ══════════════════════════════════════════

    @classmethod
    def create_purchase_entry(cls, purchase_invoice, user=None):
        """
        قيد شراء خامات
        من ح/ المخزون (خامات)  1141
        من ح/ ضريبة مشتريات    115   (لو ضريبي)
        إلى ح/ المورد           2111/2112
        """
        lines = []

        # المخزون (مدين)
        lines.append({
            'account_code': '1141',
            'debit': purchase_invoice.amount_before_tax,
            'credit': 0,
            'description': f'شراء خامات - فاتورة {purchase_invoice.invoice_number}',
        })

        # ضريبة مشتريات (مدين) — لو ضريبي
        if purchase_invoice.is_taxable and purchase_invoice.tax_amount > 0:
            lines.append({
                'account_code': '115',
                'debit': purchase_invoice.tax_amount,
                'credit': 0,
                'description': f'ضريبة مشتريات - فاتورة {purchase_invoice.invoice_number}',
            })

        # المورد (دائن)
        supplier_account = (
            purchase_invoice.supplier.account.code
            if purchase_invoice.supplier.account
            else '2111'
        )
        lines.append({
            'account_code': supplier_account,
            'debit': 0,
            'credit': purchase_invoice.total,
            'description': f'شراء من {purchase_invoice.supplier.name}',
            'partner_type': 'supplier',
            'partner_id': purchase_invoice.supplier.id,
        })

        return cls.create_entry(
            source='purchase',
            description=f'شراء خامات - فاتورة {purchase_invoice.invoice_number} - {purchase_invoice.supplier.name}',
            branch=purchase_invoice.branch,
            lines_data=lines,
            source_document=purchase_invoice.invoice_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_sale_entry(cls, sales_invoice, user=None):
        """
        قيد بيع
        من ح/ العميل أو الخزينة
        إلى ح/ المبيعات (حسب القناة)
        إلى ح/ ضريبة مبيعات (لو ضريبي)
        ─────────────────────
        من ح/ تكلفة بضاعة مباعة
        إلى ح/ مخزون منتجات تامة
        """
        lines = []

        # تحديد حساب العميل
        if sales_invoice.payment_method == 'cash':
            debit_account = '1111'  # الخزينة
        else:
            # حسب نوع العميل
            customer_type_accounts = {
                'retail':      '1121',
                'wholesale':   '1122',
                'franchise':   '1123',
                'distributor': '1124',
                'online':      '1125',
            }
            debit_account = customer_type_accounts.get(
                sales_invoice.customer.customer_type, '1121'
            )
            if sales_invoice.customer.account:
                debit_account = sales_invoice.customer.account.code

        # العميل/الخزينة (مدين)
        lines.append({
            'account_code': debit_account,
            'debit': sales_invoice.total,
            'credit': 0,
            'description': f'بيع - فاتورة {sales_invoice.invoice_number}',
            'partner_type': 'customer',
            'partner_id': sales_invoice.customer.id,
        })

        # تحديد حساب المبيعات حسب القناة
        channel_accounts = {
            'retail':      '411',
            'wholesale':   '412',
            'franchise':   '413',
            'distributor': '414',
            'online':      '415',
        }
        sales_account = channel_accounts.get(
            sales_invoice.customer.customer_type, '411'
        )

        # صافي المبيعات (دائن)
        net_amount = sales_invoice.total
        if sales_invoice.is_taxable and sales_invoice.tax_amount > 0:
            net_amount = sales_invoice.total - sales_invoice.tax_amount

        lines.append({
            'account_code': sales_account,
            'debit': 0,
            'credit': net_amount,
            'description': f'مبيعات - فاتورة {sales_invoice.invoice_number}',
        })

        # ضريبة مبيعات (دائن) — لو ضريبي
        if sales_invoice.is_taxable and sales_invoice.tax_amount > 0:
            lines.append({
                'account_code': '213',
                'debit': 0,
                'credit': sales_invoice.tax_amount,
                'description': f'ضريبة مبيعات - فاتورة {sales_invoice.invoice_number}',
            })

        # إنشاء قيد البيع
        sale_entry = cls.create_entry(
            source='sale',
            description=f'بيع - فاتورة {sales_invoice.invoice_number} - {sales_invoice.customer.name}',
            branch=sales_invoice.branch,
            lines_data=lines,
            source_document=sales_invoice.invoice_number,
            user=user,
            auto_post=True,
        )

        # قيد تكلفة البضاعة المباعة (منفصل)
        cost_lines = []
        total_cost = Decimal('0')
        for line in sales_invoice.lines.all():
            total_cost += line.cost_price * line.quantity

        if total_cost > 0:
            cost_lines.append({
                'account_code': '51',
                'debit': total_cost,
                'credit': 0,
                'description': f'تكلفة بضاعة مباعة - فاتورة {sales_invoice.invoice_number}',
            })
            cost_lines.append({
                'account_code': '1143',
                'debit': 0,
                'credit': total_cost,
                'description': f'خصم مخزون منتجات تامة - فاتورة {sales_invoice.invoice_number}',
            })

            cls.create_entry(
                source='sale',
                description=f'تكلفة مبيعات - فاتورة {sales_invoice.invoice_number}',
                branch=sales_invoice.branch,
                lines_data=cost_lines,
                source_document=sales_invoice.invoice_number,
                user=user,
                auto_post=True,
            )

        return sale_entry

    @classmethod
    def create_production_issue_entry(cls, production_order, user=None):
        """
        قيد صرف خامات للإنتاج
        من ح/ تحت التشغيل    1142
        إلى ح/ مخزون خامات   1141
        """
        total_cost = sum(
            c.total_cost for c in production_order.material_consumptions.all()
        )

        if total_cost <= 0:
            return None

        lines = [
            {
                'account_code': '1142',
                'debit': total_cost,
                'credit': 0,
                'description': f'صرف خامات لأمر إنتاج {production_order.order_number}',
            },
            {
                'account_code': '1141',
                'debit': 0,
                'credit': total_cost,
                'description': f'خصم خامات - أمر إنتاج {production_order.order_number}',
            },
        ]

        return cls.create_entry(
            source='production',
            description=f'صرف خامات - أمر إنتاج {production_order.order_number} - {production_order.product.name}',
            branch=production_order.warehouse_raw.branch,
            lines_data=lines,
            source_document=production_order.order_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_production_complete_entry(cls, production_order, user=None):
        """
        قيد استلام إنتاج تام
        من ح/ منتجات تامة     1143
        إلى ح/ تحت التشغيل   1142
        """
        total_cost = production_order.total_cost

        if total_cost <= 0:
            return None

        lines = [
            {
                'account_code': '1143',
                'debit': total_cost,
                'credit': 0,
                'description': f'استلام إنتاج تام - أمر {production_order.order_number}',
            },
            {
                'account_code': '1142',
                'debit': 0,
                'credit': total_cost,
                'description': f'تحويل من تحت التشغيل - أمر {production_order.order_number}',
            },
        ]

        return cls.create_entry(
            source='production',
            description=f'إنتاج تام - أمر {production_order.order_number} - {production_order.product.name}',
            branch=production_order.warehouse_finished.branch,
            lines_data=lines,
            source_document=production_order.order_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_labor_cost_entry(cls, production_order, labor_amount, user=None):
        """
        قيد تحميل عمالة مباشرة
        من ح/ تحت التشغيل     1142
        إلى ح/ رواتب مستحقة   215
        """
        lines = [
            {
                'account_code': '1142',
                'debit': labor_amount,
                'credit': 0,
                'description': f'عمالة مباشرة - أمر {production_order.order_number}',
            },
            {
                'account_code': '215',
                'debit': 0,
                'credit': labor_amount,
                'description': f'رواتب مستحقة - أمر {production_order.order_number}',
            },
        ]

        return cls.create_entry(
            source='production',
            description=f'تحميل عمالة - أمر {production_order.order_number}',
            branch=production_order.warehouse_raw.branch,
            lines_data=lines,
            source_document=production_order.order_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_overhead_entry(cls, production_order, overhead_amount, description_text, user=None):
        """
        قيد تحميل تكاليف صناعية غير مباشرة
        من ح/ تحت التشغيل                  1142
        إلى ح/ تكاليف صناعية غير مباشرة   54
        """
        lines = [
            {
                'account_code': '1142',
                'debit': overhead_amount,
                'credit': 0,
                'description': f'تكاليف غير مباشرة - {description_text}',
            },
            {
                'account_code': '54',
                'debit': 0,
                'credit': overhead_amount,
                'description': f'تحميل overhead - {description_text}',
            },
        ]

        return cls.create_entry(
            source='production',
            description=f'تكاليف غير مباشرة - أمر {production_order.order_number} - {description_text}',
            branch=production_order.warehouse_raw.branch,
            lines_data=lines,
            source_document=production_order.order_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_expense_entry(cls, expense_account_code, amount, description_text, branch, user=None):
        """
        قيد مصروف
        من ح/ المصروف (حسب النوع)
        إلى ح/ الخزينة   1111
        """
        lines = [
            {
                'account_code': expense_account_code,
                'debit': amount,
                'credit': 0,
                'description': description_text,
            },
            {
                'account_code': '1111',
                'debit': 0,
                'credit': amount,
                'description': f'صرف - {description_text}',
            },
        ]

        return cls.create_entry(
            source='expense',
            description=description_text,
            branch=branch,
            lines_data=lines,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_sales_return_entry(cls, sales_return, user=None):
        """
        قيد مرتجع مبيعات
        من ح/ مردودات المبيعات  43
        إلى ح/ العميل/الخزينة
        """
        original = sales_return.original_invoice
        if original.payment_method == 'cash':
            credit_account = '1111'
        else:
            customer_type_accounts = {
                'retail':      '1121',
                'wholesale':   '1122',
                'franchise':   '1123',
                'distributor': '1124',
                'online':      '1125',
            }
            credit_account = customer_type_accounts.get(
                sales_return.customer.customer_type, '1121'
            )

        lines = [
            {
                'account_code': '43',
                'debit': sales_return.total,
                'credit': 0,
                'description': f'مرتجع مبيعات - {sales_return.return_number}',
            },
            {
                'account_code': credit_account,
                'debit': 0,
                'credit': sales_return.total,
                'description': f'مرتجع من {sales_return.customer.name}',
                'partner_type': 'customer',
                'partner_id': sales_return.customer.id,
            },
        ]

        return cls.create_entry(
            source='sale',
            description=f'مرتجع مبيعات - {sales_return.return_number} - {sales_return.customer.name}',
            branch=sales_return.branch,
            lines_data=lines,
            source_document=sales_return.return_number,
            user=user,
            auto_post=True,
        )

    @classmethod
    def create_stock_transfer_entry(cls, transfer, user=None):
        """
        قيد تحويل مخزون بين المخازن
        لا يوجد أثر مالي — القيد للتوثيق فقط
        من ح/ مخزون المخزن المستلم
        إلى ح/ مخزون المخزن المرسل
        التحويل بين نفس الفرع: لا قيد
        التحويل بين فروع مختلفة: قيد توثيقي
        """
        # لو التحويل بين مخازن نفس الفرع — لا قيد
        if transfer.warehouse_from.branch == transfer.warehouse_to.branch:
            return None

        lines = [
            {
                'account_code': '1143',
                'debit': transfer.total_cost,
                'credit': 0,
                'description': f'تحويل وارد من {transfer.warehouse_from.name}',
            },
            {
                'account_code': '1143',
                'debit': 0,
                'credit': transfer.total_cost,
                'description': f'تحويل صادر إلى {transfer.warehouse_to.name}',
            },
        ]

        return cls.create_entry(
            source='stock_move',
            description=f'تحويل مخزون - {transfer.move_number}',
            branch=transfer.warehouse_from.branch,
            lines_data=lines,
            source_document=transfer.move_number,
            user=user,
            auto_post=True,
        )
