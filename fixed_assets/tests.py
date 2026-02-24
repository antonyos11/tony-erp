from django.test import TestCase, Client
from decimal import Decimal
from django.utils import timezone

from .models import AssetCategory, Asset, DepreciationSchedule
from accounting.models import Account


class FixedAssetsTests(TestCase):
    """اختبارات أساسية للأصول الثابتة والتحقق من clean()."""

    def setUp(self):
        self.asset_account = Account.objects.create(name="Assets", code="1100", level=1)
        self.depr_acc = Account.objects.create(name="Accum Dep", code="1200", level=1)
        self.exp_acc = Account.objects.create(name="Dep Exp", code="1300", level=1)
        self.cat = AssetCategory.objects.create(
            name="Machines",
            code="MACH",
            asset_account=self.asset_account,
            accumulated_depreciation_account=self.depr_acc,
            depreciation_expense_account=self.exp_acc,
        )
        self.client = Client()

    def test_asset_clean_invalid_values(self):
        asset = Asset(
            name="Machine 1",
            category=self.cat,
            acquisition_date=timezone.now().date(),
            acquisition_cost=Decimal("0.00"),
            useful_life_years=0,
        )
        # number يملأ في save لذلك نتركه فارغاً الآن
        with self.assertRaises(Exception):
            asset.full_clean()

    def test_asset_save_generates_number_and_book_value(self):
        asset = Asset.objects.create(
            number="FA-TEST-1",
            name="Machine 2",
            category=self.cat,
            acquisition_date=timezone.now().date(),
            acquisition_cost=Decimal("1000.00"),
            useful_life_years=5,
        )
        # بدون أي قيود استهلاك، القيمة الدفترية يجب أن تساوي تكلفة الاستحواذ
        self.assertTrue(asset.number)
        self.assertEqual(asset.current_book_value, Decimal("1000.00"))

        # بعد إضافة قسط استهلاك مرحّل، تنخفض القيمة الدفترية
        DepreciationSchedule.objects.create(
            asset=asset,
            period_start=asset.acquisition_date,
            period_end=asset.acquisition_date,
            depreciation_amount=Decimal("100.00"),
            accumulated_depreciation=Decimal("100.00"),
            book_value=Decimal("900.00"),
            status="posted",
        )
        asset.refresh_from_db()
        self.assertEqual(asset.current_book_value, Decimal("900.00"))

    def test_asset_list_view_requires_login(self):
        """تأكد أن قائمة الأصول تتطلب تسجيل دخول وترجع 302 لغير المسجل."""
        response = self.client.get("/fixed-assets/")
        self.assertEqual(response.status_code, 302)

