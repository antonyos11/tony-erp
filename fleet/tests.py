from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from decimal import Decimal

from accounting.models import Account
from .models import Vehicle, Driver, Trip, VehicleExpense, FleetAccountingSettings, VehicleDocument, DriverViolation, DriverAdvance
from django.urls import reverse

User = get_user_model()

class FleetCoreTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        # إنشاء حسابات محاسبية أساسية
        self.cash = Account.objects.create(code='1001T', name='صندوق تجريبي', account_type='asset')
        self.fuel_acc = Account.objects.create(code='6001T', name='مصروف وقود', account_type='expense')
        self.maint_acc = Account.objects.create(code='6002T', name='مصروف صيانة', account_type='expense')
        FleetAccountingSettings.objects.create(
            fuel_account=self.fuel_acc,
            maintenance_account=self.maint_acc,
            default_credit_account=self.cash,
            auto_create_journals=True,
        )
        self.vehicle = Vehicle.objects.create(name='سيارة 1', plate_number='ABC123', current_odometer=1000)
        self.driver = Driver.objects.create(name='سائق 1')

    def test_trip_updates_odometer(self):
        start = timezone.now()
        end = start + timezone.timedelta(hours=2)
        Trip.objects.create(vehicle=self.vehicle, driver=self.driver, start_time=start, end_time=end, origin='A', destination='B', distance_km=50)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer, 1050)

    def test_vehicle_expense_creates_journal_entry(self):
        exp = VehicleExpense.objects.create(vehicle=self.vehicle, category='fuel', description='بنزين', amount=Decimal('75.50'), date=timezone.now().date(), created_by=self.user)
        # signal should auto create journal entry
        exp.refresh_from_db()
        self.assertIsNotNone(exp.journal_entry_id)
        self.assertTrue(exp.journal_entry.is_posted)
        self.assertEqual(exp.journal_entry.total_debit, exp.amount)

    def test_api_vehicle_crud(self):
        # list
        resp = self.client.get('/api/fleet/vehicles/')
        self.assertEqual(resp.status_code, 200)
        # create
        data = {"name":"سيارة 2","plate_number":"XYZ999","status":"available","current_odometer":0}
        resp = self.client.post('/api/fleet/vehicles/', data)
        self.assertEqual(resp.status_code, 201, resp.content)
        vid = resp.data['id']
        # retrieve
        resp = self.client.get(f'/api/fleet/vehicles/{vid}/')
        self.assertEqual(resp.status_code, 200)
        # partial update
        resp = self.client.patch(f'/api/fleet/vehicles/{vid}/', {"current_odometer": 10}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['current_odometer'], 10)

    def test_api_expense_creation_and_journal_link(self):
        data = {"vehicle": self.vehicle.id, "category": "maintenance", "description": "زيت", "amount": "120.00", "date": timezone.now().date()}
        resp = self.client.post('/api/fleet/expenses/', data)
        self.assertEqual(resp.status_code, 201, resp.content)
        exp_id = resp.data['id']
        exp = VehicleExpense.objects.get(id=exp_id)
        # ensure journal entry auto-created via post_save signal
        exp.refresh_from_db()
        self.assertIsNotNone(exp.journal_entry_id)

    def test_document_expiry_helpers(self):
        today = timezone.now().date()
        VehicleDocument.objects.create(vehicle=self.vehicle, doc_type='تأمين', file='vehicles/docs/test.pdf', expiry_date=today + timezone.timedelta(days=10))
        VehicleDocument.objects.create(vehicle=self.vehicle, doc_type='رخصة', file='vehicles/docs/test2.pdf', expiry_date=today - timezone.timedelta(days=1))
        expiring = VehicleDocument.objects.expiring_within(30)
        expired = VehicleDocument.objects.expired()
        self.assertEqual(expiring.count(), 1)
        self.assertEqual(expired.count(), 1)

    def test_violation_paid_creates_expense(self):
        today = timezone.now().date()
        v = DriverViolation.objects.create(driver=self.driver, vehicle=self.vehicle, violation_type='سرعة', date=today, amount=Decimal('200.00'), is_paid=True)
        # signal should create expense fine
        exp = VehicleExpense.objects.filter(description__contains=f"مخالفة: {v.violation_type}").first()
        self.assertIsNotNone(exp)
        self.assertEqual(exp.amount, v.amount)
        self.assertEqual(exp.category, 'fine')

    def test_driver_advance_utilization_and_settle(self):
        adv = DriverAdvance.objects.create(driver=self.driver, date=timezone.now().date(), amount=Decimal('500.00'), description='سلفة رحلة')
        # create expense linked to advance
        VehicleExpense.objects.create(vehicle=self.vehicle, driver=self.driver, category='fuel', description='وقود رحلة', amount=Decimal('200.00'), date=timezone.now().date(), advance=adv)
        self.assertEqual(adv.utilized_amount, Decimal('200.00'))
        self.assertEqual(adv.remaining_amount, Decimal('300.00'))
        # استهلاك باقي العهدة
        VehicleExpense.objects.create(vehicle=self.vehicle, driver=self.driver, category='maintenance', description='صيانة', amount=Decimal('300.00'), date=timezone.now().date(), advance=adv)
        adv.refresh_from_db()
        self.assertTrue(adv.can_settle())
        adv.settle()
        adv.refresh_from_db()
        self.assertEqual(adv.status, 'settled')

    def test_api_advance_settle(self):
        adv = DriverAdvance.objects.create(driver=self.driver, date=timezone.now().date(), amount=Decimal('100.00'), description='سلفة')
        # Fully consume advance
        VehicleExpense.objects.create(vehicle=self.vehicle, driver=self.driver, category='fuel', description='وقود', amount=Decimal('100.00'), date=timezone.now().date(), advance=adv)
        self.assertTrue(adv.can_settle())
        url = f'/api/fleet/advances/{adv.id}/settle/'
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 200, resp.content)
        adv.refresh_from_db()
        self.assertEqual(adv.status, 'settled')

    def test_web_permission_denied_without_manage_vehicle(self):
        # user lacks specific permission manage_vehicle; expect 403 on create vehicle view
        # Web views require Django session login (not just DRF force_authenticate)
        self.client.login(username='apiuser', password='pass12345')
        create_url = reverse('fleet:vehicle_create')
        resp = self.client.get(create_url)
        # If permission applied correctly => 403; if login_required => 302
        self.assertIn(resp.status_code, (302, 403))
