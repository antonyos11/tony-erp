from django.test import SimpleTestCase, RequestFactory
from django.template import Context, Template
from django.conf import settings

class MoneyFiltersTests(SimpleTestCase):
    def render(self, tpl, ctx):
        if '{% load' not in tpl:
            tpl = '{% load money_tags %}' + tpl
        return Template(tpl).render(Context(ctx)).strip()

    def test_money_basic(self):
        out = self.render("{{ 1234.0|money }}", {})
        self.assertIn('1,234', out)

    def test_money_decimals_override(self):
        out = self.render("{{ 12.3456|money:'|3' }}", {})
        self.assertTrue(out.startswith('12.346'))

    def test_money_plain(self):
        out = self.render("{{ 1234.0|money_plain }}", {})
        self.assertTrue(out.startswith('1,234'))

    def test_money_compact_removes_trailing(self):
        out = self.render("{{ 2500.00|money_compact }}", {})
        self.assertIn('2,500', out)
        self.assertNotIn('.00', out)

    def test_money_ctx_uses_context_currency(self):
        rf = RequestFactory()
        req = rf.get('/', {'currency': 'USD'})
        # Simulate context processor output
        ctx = {
            'ACTIVE_CURRENCY_CODE': 'USD',
            'ACTIVE_CURRENCY_SYMBOL': settings.SUPPORTED_CURRENCIES.get('USD', '$')
        }
        out = self.render("{% money_ctx 100 %}", ctx)
        self.assertIn('100', out)
        self.assertIn(settings.SUPPORTED_CURRENCIES.get('USD', '$'), out)

    def test_money_ctx_decimals(self):
        ctx = {
            'ACTIVE_CURRENCY_CODE': 'SAR',
            'ACTIVE_CURRENCY_SYMBOL': settings.SUPPORTED_CURRENCIES.get('SAR', '﷼')
        }
        out = self.render("{% money_ctx 12.5 '|0' %}", ctx)
        self.assertRegex(out, r'^12(,?0?)* \S+')
