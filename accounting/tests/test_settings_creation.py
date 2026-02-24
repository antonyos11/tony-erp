from django.test import TestCase
from accounting.models import AccountingSettings, Account


class AccountingSettingsCreationTests(TestCase):
    def test_get_creates_core_accounts_if_missing(self):
        # Ensure target codes absent
        target_codes = {'1004', '2001', '1101', '1551', '2551', '1001'}
        Account.objects.filter(code__in=target_codes).delete()
        settings = AccountingSettings.get()
        self.assertIsNotNone(settings.inventory_account)
        self.assertIsNotNone(settings.ap_account)
        self.assertIsNotNone(settings.ar_account)
        self.assertIsNotNone(settings.cash_account)
        self.assertIsNotNone(settings.vat_input_account)
        self.assertIsNotNone(settings.vat_output_account)
        # All required codes now exist
        existing = set(Account.objects.filter(code__in=target_codes).values_list('code', flat=True))
        self.assertTrue(target_codes.issubset(existing))
