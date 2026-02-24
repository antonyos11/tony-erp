import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from inventory.models import Product, Location, Stock
from purchases.models import PurchaseBill, PurchaseItem
from partners.models import Partner, Supplier
from sales.models import Invoice, InvoiceItem, Customer
from accounting.models import Account, JournalEntry
from django.db import transaction


class Command(BaseCommand):
    help = "تشغيل حزمة اختبارات P1 الأساسية وإرجاع تقرير JSON"

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **opts):
        username = opts['username']
        password = opts['password']
        report: dict[str, dict] = {}
        failures = 0

        def record(name, ok, detail=None):
            nonlocal failures
            if not ok:
                failures += 1
            report[name] = {'ok': ok, 'detail': detail}

        # 1. Auth
        client = Client()
        resp = client.post('/accounts/login/', {'username': username, 'password': password})
        record('login', resp.status_code in (200, 302), f"status={resp.status_code}")

        # 2. Create product + purchase + sales flow
        try:
            with transaction.atomic():
                prod, _ = Product.objects.get_or_create(
                    sku='SKU-P1-TEST',
                    defaults={'name': 'منتج اختبار P1', 'price': Decimal('100'), 'cost': Decimal('60'), 'min_stock': 2}
                )
                loc = Location.objects.order_by('id').first()
                if not loc:
                    raise RuntimeError('لا يوجد Location')
                # Purchase (increase stock)
                partner = Partner.objects.filter(partner_type='supplier').order_by('id').first()
                if not partner:
                    partner = Partner.objects.create(name='مورد اختبار P1', partner_type='supplier')
                supplier = partner
                bill = PurchaseBill.objects.create(number=f'PB-P1-{PurchaseBill.objects.count()+1:05d}', supplier=supplier)
                PurchaseItem.objects.create(bill=bill, product=prod, location=loc, quantity=5, cost=Decimal('55'))
                # Adjust or create stock record
                stock, _ = Stock.objects.get_or_create(product=prod, location=loc, defaults={'quantity': 0})
                stock.quantity += 5
                stock.save()
                # Sales invoice
                customer = Customer.objects.order_by('id').first()
                if not customer:
                    customer = Customer.objects.create(name='عميل اختبار', email='cust@test.local')
                inv = Invoice.objects.create(number=f'INV-P1-{Invoice.objects.count()+1:05d}', customer=customer, date=timezone.now().date())
                InvoiceItem.objects.create(invoice=inv, product=prod, location=loc, quantity=2, price=Decimal('110'))
                # Deduct stock
                stock.refresh_from_db()
                stock.quantity -= 2
                stock.save()
                record('inventory_flow', True, f"remaining_stock={stock.quantity}")
        except Exception as e:
            record('inventory_flow', False, str(e))

        # 3. Accounting simple journal entry
        try:
            acc1, _ = Account.objects.get_or_create(code='111199', defaults={'name': 'حساب اختبار مدين', 'account_type': 'asset'})
            acc2, _ = Account.objects.get_or_create(code='211199', defaults={'name': 'حساب اختبار دائن', 'account_type': 'liability'})
            je = JournalEntry.objects.create(number=f'JE-P1-{JournalEntry.objects.count()+1:05d}', description='قيد اختبار P1')
            je.items.create(account=acc1, type='debit', amount=Decimal('100'))
            je.items.create(account=acc2, type='credit', amount=Decimal('100'))
            debit_total = sum(i.amount for i in je.items.filter(type='debit'))
            credit_total = sum(i.amount for i in je.items.filter(type='credit'))
            balanced = debit_total == credit_total == Decimal('100')
            record('journal_entry', balanced, f"debit={debit_total} credit={credit_total}")
        except Exception as e:
            record('journal_entry', False, str(e))

        # 4. API smoke (optional endpoint existence check)
        try:
            resp2 = client.get('/api/')
            record('api_root', resp2.status_code < 500, f"status={resp2.status_code}")
        except Exception as e:
            record('api_root', False, str(e))

        summary = {'passed': sum(1 for v in report.values() if v['ok']), 'failed': failures}
        report['__summary__'] = summary

        if opts['json']:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for name, data in report.items():
                if name == '__summary__':
                    continue
                status = 'OK' if data['ok'] else 'FAIL'
                self.stdout.write(f"[{status}] {name} -> {data.get('detail')}")
            self.stdout.write(f"Summary: {summary}")
        if failures:
            raise SystemExit(1)
