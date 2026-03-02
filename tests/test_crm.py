"""
اختبارات CRM — Sprint 19
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User, Branch
from apps.crm.models import Lead, Interaction, Complaint, CustomerRating, CustomerGroup
from apps.crm.services.crm_engine import CRMEngine
from apps.sales.models import Customer


class LeadTestCase(TestCase):
    """اختبارات Lead"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.branch = Branch.objects.create(name='فرع رئيسي')

    def test_create_lead(self):
        lead = CRMEngine.create_lead(
            name='أحمد محمد',
            phone='01012345678',
            source='walk_in',
            branch=self.branch,
            user=self.user,
        )
        self.assertEqual(lead.name, 'أحمد محمد')
        self.assertEqual(lead.status, 'new')
        self.assertEqual(lead.branch, self.branch)

    def test_lead_str(self):
        lead = Lead.objects.create(
            name='علي حسن', phone='01012345679',
            source='phone', status='new',
            branch=self.branch,
            created_by=self.user,
        )
        self.assertIn('علي حسن', str(lead))

    def test_convert_lead_to_customer(self):
        lead = CRMEngine.create_lead(
            name='سارة أحمد', phone='01098765432',
            source='facebook', branch=self.branch,
            user=self.user,
        )
        customer = CRMEngine.convert_lead_to_customer(lead, user=self.user)
        self.assertEqual(customer.name, 'سارة أحمد')
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'won')
        self.assertEqual(lead.converted_to_customer, customer)

    def test_convert_lead_twice_raises(self):
        lead = CRMEngine.create_lead(
            name='محمود سيد', phone='01011111111',
            source='referral', branch=self.branch,
            user=self.user,
        )
        CRMEngine.convert_lead_to_customer(lead, user=self.user)
        lead.refresh_from_db()
        with self.assertRaises(ValueError):
            CRMEngine.convert_lead_to_customer(lead, user=self.user)

    def test_lead_pipeline(self):
        for status in ['new', 'new', 'contacted', 'interested']:
            Lead.objects.create(
                name=f'عميل {status}', phone='010',
                source='phone', status=status,
                branch=self.branch,
            )
        pipeline = CRMEngine.get_lead_pipeline(branch=self.branch)
        self.assertEqual(pipeline['new'], 2)
        self.assertEqual(pipeline['contacted'], 1)
        self.assertEqual(pipeline['interested'], 1)


class InteractionTestCase(TestCase):
    """اختبارات التفاعلات"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser2', password='pass')
        self.branch = Branch.objects.create(name='فرع ثانوي')
        self.customer = Customer.objects.create(
            code='C0001', name='عميل اختبار', branch=self.branch
        )

    def test_log_interaction(self):
        interaction = CRMEngine.log_interaction(
            interaction_type='call_out',
            subject='مكالمة تسويقية',
            details='تم التواصل مع العميل وأبدى اهتماماً',
            customer=self.customer,
            handled_by=self.user,
            branch=self.branch,
            user=self.user,
        )
        self.assertEqual(interaction.interaction_type, 'call_out')
        self.assertEqual(interaction.customer, self.customer)

    def test_interaction_with_follow_up(self):
        from datetime import date, timedelta
        follow_date = date.today() + timedelta(days=3)
        interaction = CRMEngine.log_interaction(
            interaction_type='whatsapp',
            subject='واتساب',
            details='تفاصيل',
            customer=self.customer,
            follow_up_date=follow_date,
            user=self.user,
        )
        self.assertTrue(interaction.follow_up_required)
        self.assertEqual(interaction.follow_up_date, follow_date)


class ComplaintTestCase(TestCase):
    """اختبارات الشكاوى"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser3', password='pass')
        self.branch = Branch.objects.create(name='فرع ثالث')
        self.customer = Customer.objects.create(
            code='C0002', name='عميل شكوى', branch=self.branch
        )

    def test_create_complaint(self):
        complaint = CRMEngine.create_complaint(
            customer=self.customer,
            complaint_type='product_defect',
            subject='عيب في المنتج',
            description='وجدت خدش في السطح',
            branch=self.branch,
            user=self.user,
        )
        self.assertIsNotNone(complaint.complaint_number)
        self.assertTrue(complaint.complaint_number.startswith('CMP-'))
        self.assertEqual(complaint.status, 'open')

    def test_resolve_complaint(self):
        complaint = CRMEngine.create_complaint(
            customer=self.customer,
            complaint_type='service',
            subject='تأخير',
            description='تأخر التوصيل',
            branch=self.branch,
            user=self.user,
        )
        CRMEngine.resolve_complaint(
            complaint=complaint,
            resolution='تم اعتذار العميل',
            resolution_type='apologized',
            user=self.user,
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'resolved')
        self.assertIsNotNone(complaint.resolution_date)


class CustomerRatingTestCase(TestCase):
    """اختبارات تقييم العملاء"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser4', password='pass')
        self.branch = Branch.objects.create(name='فرع رابع')
        self.customer = Customer.objects.create(
            code='C0003', name='عميل تقييم', branch=self.branch
        )

    def test_update_customer_rating_new_customer(self):
        rating = CRMEngine.update_customer_rating(self.customer)
        self.assertIsNotNone(rating)
        self.assertIn(rating.grade, ['A+', 'A', 'B', 'C', 'D', 'F'])
        self.assertGreaterEqual(rating.score, 0)
        self.assertLessEqual(rating.score, 100)

    def test_customer_grade_with_no_purchases(self):
        rating = CRMEngine.update_customer_rating(self.customer)
        # عميل بلا مشتريات — تحقق من أن التصنيف صالح فقط
        self.assertIn(rating.grade, ['A+', 'A', 'B', 'C', 'D', 'F'])


class CustomerGroupTestCase(TestCase):
    """اختبارات مجموعات العملاء"""

    def test_create_customer_group(self):
        group = CustomerGroup.objects.create(
            name='VIP',
            discount_percentage=Decimal('10.00'),
            credit_limit=Decimal('50000.00'),
            color='#ffc107',
        )
        self.assertEqual(str(group), 'VIP')
        self.assertTrue(group.is_active)


class CRMViewsTestCase(TestCase):
    """اختبارات الصفحات"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='viewuser', password='pass', is_staff=True)
        self.branch = Branch.objects.create(name='فرع اختبار Views')
        self.client.login(username='viewuser', password='pass')

    def test_dashboard_200(self):
        resp = self.client.get(reverse('crm:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_lead_list_200(self):
        resp = self.client.get(reverse('crm:lead_list'))
        self.assertEqual(resp.status_code, 200)

    def test_lead_kanban_200(self):
        resp = self.client.get(reverse('crm:lead_kanban'))
        self.assertEqual(resp.status_code, 200)

    def test_lead_create_200(self):
        resp = self.client.get(reverse('crm:lead_create'))
        self.assertEqual(resp.status_code, 200)

    def test_customer_search_200(self):
        resp = self.client.get(reverse('crm:customer_search'))
        self.assertEqual(resp.status_code, 200)

    def test_interaction_list_200(self):
        resp = self.client.get(reverse('crm:interaction_list'))
        self.assertEqual(resp.status_code, 200)

    def test_interaction_create_200(self):
        resp = self.client.get(reverse('crm:interaction_create'))
        self.assertEqual(resp.status_code, 200)

    def test_follow_up_list_200(self):
        resp = self.client.get(reverse('crm:follow_up_list'))
        self.assertEqual(resp.status_code, 200)

    def test_complaint_list_200(self):
        resp = self.client.get(reverse('crm:complaint_list'))
        self.assertEqual(resp.status_code, 200)

    def test_complaint_create_200(self):
        resp = self.client.get(reverse('crm:complaint_create'))
        self.assertEqual(resp.status_code, 200)

    def test_task_list_200(self):
        resp = self.client.get(reverse('crm:task_list'))
        self.assertEqual(resp.status_code, 200)

    def test_task_create_200(self):
        resp = self.client.get(reverse('crm:task_create'))
        self.assertEqual(resp.status_code, 200)

    def test_group_list_200(self):
        resp = self.client.get(reverse('crm:group_list'))
        self.assertEqual(resp.status_code, 200)

    def test_group_create_200(self):
        resp = self.client.get(reverse('crm:group_create'))
        self.assertEqual(resp.status_code, 200)

    def test_rating_report_200(self):
        resp = self.client.get(reverse('crm:rating_report'))
        self.assertEqual(resp.status_code, 200)

    def test_lead_source_report_200(self):
        resp = self.client.get(reverse('crm:lead_source_report'))
        self.assertEqual(resp.status_code, 200)

    def test_salesman_report_200(self):
        resp = self.client.get(reverse('crm:salesman_report'))
        self.assertEqual(resp.status_code, 200)

    def test_customer_profile_200(self):
        customer = Customer.objects.create(code='C9001', name='عميل', branch=self.branch)
        resp = self.client.get(reverse('crm:customer_profile', kwargs={'pk': customer.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        resp = self.client.get(reverse('crm:dashboard'))
        self.assertIn(resp.status_code, [302, 301])
