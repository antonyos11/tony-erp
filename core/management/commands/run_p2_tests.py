import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from django.db import transaction
from hr.models import Employee, Department, JobPosition
from crm.models import Opportunity, OpportunityStage, Customer as CRMCustomer
from sales.models import Invoice, InvoiceItem  # فواتير المبيعات
from partners.models import Customer as SalesCustomer
from inventory.models import Product, Location, Stock
from purchases.models import Supplier, PurchaseBill, PurchaseItem
from accounting.models import Account, JournalEntry
from core.sequence_utils import next_sequence, format_code
import random

class Command(BaseCommand):
    help = "تشغيل حزمة اختبارات P2 (HR + CRM + تدفق شراء→بيع + قيد محاسبي)"

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **opts):
        username = opts['username']
        password = opts['password']
        report: dict[str, dict] = {}
        failures = 0

        def record(name: str, ok: bool, detail=None):
            nonlocal failures
            if not ok:
                failures += 1
            report[name] = {'ok': ok, 'detail': detail}

        # 1. Auth
        client = Client()
        resp = client.post('/accounts/login/', {'username': username, 'password': password})
        record('login', resp.status_code in (200, 302), f"status={resp.status_code}")

        # 2. HR: create or fetch department + employee minimal
        try:
            # Department (ensure code exists if creating new)
            dept = Department.objects.filter(name='الإنتاج').first()
            if not dept:
                dept = Department.objects.create(name='الإنتاج', code='PRD', description='قسم الإنتاج')
            # JobPosition
            pos = JobPosition.objects.filter(code='POS-P2').first()
            if not pos:
                pos = JobPosition.objects.create(
                    title='عامل عام', code='POS-P2', department=dept,
                    description='وصف مختصر', requirements='لا متطلبات',
                    min_salary=Decimal('3000'), max_salary=Decimal('6000')
                )
            User = get_user_model()
            test_username = 'hr_p2_user'
            user, _ = User.objects.get_or_create(username=test_username, defaults={'is_staff': False, 'email':'hr_p2@test.local'})
            if not user.password:
                user.set_password('Temp12345!')
                user.save(update_fields=['password'])
            emp_defaults = {
                'user': user,
                'first_name': 'Test',
                'last_name': 'User',
                'arabic_name': 'موظف اختبار',
                'national_id': '12345678901234',
                'gender': 'M',
                'birth_date': timezone.now().date(),
                'marital_status': 'single',
                'phone': '01000000000',
                'email': 'hr_p2@test.local',
                'address': 'عنوان تجريبي',
                'emergency_contact_name': 'قريب',
                'emergency_contact_phone': '01000000001',
                'department': dept,
                'position': pos,
                'hire_date': timezone.now().date(),
                'basic_salary': Decimal('5000'),
                'housing_allowance': Decimal('0'),
                'transportation_allowance': Decimal('0'),
                'other_allowances': Decimal('0'),
            }
            emp, created_emp = Employee.objects.get_or_create(employee_id='EMP-P2-001', defaults=emp_defaults)
            if not created_emp:
                changed = False
                for k, v in emp_defaults.items():
                    if getattr(emp, k, None) in (None, ''):
                        setattr(emp, k, v)
                        changed = True
                if changed:
                    emp.save()
            record('hr_employee', True, f"emp_id={emp.id}")
        except Exception as e:
            record('hr_employee', False, str(e))

        # 3. CRM: create opportunity at first stage
        try:
            stage = OpportunityStage.objects.order_by('order').first()
            if not stage:
                stage = OpportunityStage.objects.create(name='مبدئي', probability=10, order=1)
            # CRM Customer (not sales customer)
            crm_cust = CRMCustomer.objects.order_by('id').first()
            if not crm_cust:
                crm_cust = CRMCustomer.objects.create(
                    customer_code='CUS-P2-001', first_name='عميل', last_name='اختبار',
                    phone='01010000000', email='crm_p2@test.local'
                )
            # assign to an existing user (superadmin) for required field assigned_to
            User = get_user_model()
            assigned = User.objects.filter(is_superuser=True).first() or User.objects.first()
            from datetime import timedelta
            opp, _ = Opportunity.objects.get_or_create(name='فرصة اختبار P2', defaults={
                'estimated_value': Decimal('1000'),
                'probability': getattr(stage, 'probability', 10),
                'expected_close_date': timezone.now().date() + timedelta(days=14),
                'stage': stage,
                'customer': crm_cust,
                'assigned_to': assigned,
            })
            record('crm_opportunity', True, f"opp_id={opp.id} stage={stage.name}")
        except Exception as e:
            record('crm_opportunity', False, str(e))

        # 4. Purchase → Stock → Sale
        try:
            with transaction.atomic():
                supplier = Supplier.objects.order_by('id').first() or Supplier.objects.create(name='مورد P2', email='sup2@test.local')
                product = Product.objects.order_by('id').first()
                if not product:
                    product = Product.objects.create(sku='SKU-P2-001', name='منتج P2', price=Decimal('150'), cost=Decimal('90'), min_stock=3)
                loc = Location.objects.order_by('id').first()
                if not loc:
                    raise RuntimeError('لا يوجد Location')
                bill_seq = next_sequence('PURCHASE_BILL_P2')
                bill_number = format_code('PB2', bill_seq)
                bill = PurchaseBill.objects.create(number=bill_number, supplier=supplier)
                qty_in = random.randint(3,7)
                PurchaseItem.objects.create(bill=bill, product=product, location=loc, quantity=qty_in, cost=product.cost)
                stock, _ = Stock.objects.get_or_create(product=product, location=loc, defaults={'quantity':0})
                stock.quantity += qty_in
                stock.save(update_fields=['quantity'])
                # sale
                customer = SalesCustomer.objects.order_by('id').first() or SalesCustomer.objects.create(name='عميل بيع P2')
                inv_seq = next_sequence('INVOICE_P2')
                inv_number = format_code('INV2', inv_seq)
                inv = Invoice.objects.create(number=inv_number, customer=customer, date=timezone.now().date())
                qty_out = min(2, stock.quantity)
                InvoiceItem.objects.create(invoice=inv, product=product, location=loc, quantity=qty_out, price=product.price)
                stock.refresh_from_db()
                stock.quantity -= qty_out
                stock.save(update_fields=['quantity'])
                record('purchase_sale_flow', True, f"in={qty_in} out={qty_out} remain={stock.quantity}")
        except Exception as e:
            record('purchase_sale_flow', False, str(e))

        # 5. Accounting journal (link to opportunity value partial)
        try:
            acc_sales, _ = Account.objects.get_or_create(code='411100', defaults={'name':'مبيعات اختبار','account_type':'income'})
            acc_cash, _ = Account.objects.get_or_create(code='111200', defaults={'name':'صندوق اختبار','account_type':'asset'})
            je_seq = next_sequence('JENTRY_P2')
            je_number = f"JE2-{je_seq:06d}"
            je = JournalEntry.objects.create(number=je_number, description='قيد مبيعات P2')
            je.items.create(account=acc_cash, type='debit', amount=Decimal('150'))
            je.items.create(account=acc_sales, type='credit', amount=Decimal('150'))
            debit_total = sum(i.amount for i in je.items.filter(type='debit'))
            credit_total = sum(i.amount for i in je.items.filter(type='credit'))
            balanced = debit_total == credit_total == Decimal('150')
            record('journal_entry', balanced, f"debit={debit_total} credit={credit_total}")
        except Exception as e:
            record('journal_entry', False, str(e))

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
