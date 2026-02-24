from django.test import TestCase
from core.models import Currency

class CurrencyDefaultTests(TestCase):
    def test_default_currency_is_egp_created_or_existing(self):
        c = Currency.get_default()
        self.assertIsNotNone(c, 'يجب أن توجد عملة افتراضية')
        self.assertEqual(c.code, 'EGP')
        self.assertTrue(c.is_default)
        self.assertEqual(c.exchange_rate, 1)
        self.assertIn(c.symbol, ['ج.م', 'جنيه', 'EGP'])  # السماح ببعض الاختلافات المحتملة

    def test_setting_another_default_switches_previous(self):
        egp = Currency.get_default()
        usd = Currency.objects.create(
            code='USD', name='الدولار الأمريكي', symbol='$', exchange_rate=30, is_active=True, is_default=False
        )
        # عيّن USD كافتراضي
        usd.is_default = True
        usd.save()
        # أعد تحميل الكيانات
        egp.refresh_from_db()
        usd.refresh_from_db()
        # تحقق من أن واحد فقط افتراضي
        defaults = Currency.objects.filter(is_default=True).count()
        self.assertEqual(defaults, 1, 'يجب أن تكون عملة افتراضية واحدة فقط')
        self.assertTrue(usd.is_default)
        self.assertFalse(egp.is_default)
        # أعد تعيين EGP كافتراضي للتأكد من العودة تعمل
        egp.is_default = True
        egp.save()
        egp.refresh_from_db()
        usd.refresh_from_db()
        self.assertTrue(egp.is_default)
        self.assertFalse(usd.is_default)
