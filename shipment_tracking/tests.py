"""اختبارات تطبيق تتبع الشحنات - Shipment Tracking Tests"""
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class ShippingCompanyModelTest(TestCase):
    """اختبارات نموذج شركات الشحن"""

    def test_company_creation(self):
        """اختبار إنشاء شركة شحن"""
        from shipment_tracking.models import ShippingCompany
        company = ShippingCompany.objects.create(
            name='أرامكس',
            name_en='Aramex',
            phone='+201234567890',
            tracking_url_template='https://www.aramex.com/track/{tracking_number}',
        )
        self.assertEqual(company.name, 'أرامكس')

    def test_tracking_url_generation(self):
        """اختبار توليد رابط التتبع"""
        from shipment_tracking.models import ShippingCompany
        company = ShippingCompany.objects.create(
            name='فيديكس',
            name_en='FedEx',
            tracking_url_template='https://www.fedex.com/track?id={tracking_number}',
        )
        url = company.get_tracking_url('ABC123')
        self.assertIn('ABC123', url)


class ShipmentModelTest(TestCase):
    """اختبارات نموذج الشحنات"""

    def setUp(self):
        from shipment_tracking.models import ShippingCompany
        self.company = ShippingCompany.objects.create(
            name='DHL',
            name_en='DHL',
        )

    def test_shipment_creation(self):
        """اختبار إنشاء شحنة"""
        from shipment_tracking.models import Shipment
        shipment = Shipment.objects.create(
            tracking_number='TRK001',
            shipping_company=self.company,
            sender_name='المرسل',
            sender_phone='+201111111111',
            receiver_name='المستلم',
            receiver_phone='+201222222222',
            receiver_city='القاهرة',
            status='pending',
        )
        self.assertIsNotNone(shipment.pk)
        self.assertFalse(shipment.is_delivered())

    def test_shipment_delivered_status(self):
        """اختبار حالة التسليم"""
        from shipment_tracking.models import Shipment
        shipment = Shipment.objects.create(
            tracking_number='TRK002',
            shipping_company=self.company,
            sender_name='المرسل',
            receiver_name='المستلم',
            receiver_city='الإسكندرية',
            status='delivered',
        )
        self.assertTrue(shipment.is_delivered())
        self.assertFalse(shipment.can_be_cancelled())

    def test_shipment_cancellation_check(self):
        """اختبار إمكانية الإلغاء"""
        from shipment_tracking.models import Shipment
        shipment = Shipment.objects.create(
            tracking_number='TRK003',
            shipping_company=self.company,
            sender_name='المرسل',
            receiver_name='المستلم',
            receiver_city='المنصورة',
            status='pending',
        )
        self.assertTrue(shipment.can_be_cancelled())


class ShipmentStatusHistoryTest(TestCase):
    """اختبارات سجل حالات الشحنة"""

    def test_status_history_creation(self):
        """اختبار تسجيل تغيير الحالة"""
        from shipment_tracking.models import ShippingCompany, Shipment, ShipmentStatusHistory
        company = ShippingCompany.objects.create(name='شركة شحن', name_en='Shipping Co')
        shipment = Shipment.objects.create(
            tracking_number='TRK004',
            shipping_company=company,
            sender_name='المرسل',
            receiver_name='المستلم',
            receiver_city='طنطا',
            status='pending',
        )
        history = ShipmentStatusHistory.objects.create(
            shipment=shipment,
            status='in_transit',
        )
        self.assertIsNotNone(history.pk)
