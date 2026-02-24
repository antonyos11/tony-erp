import pytest
from django.template import Context, Template

pytestmark = pytest.mark.django_db


def render(tpl, ctx=None):
    return Template(tpl).render(Context(ctx or {})).strip()


def test_paid_percent_basic():
    out = render('{% load billing_extras %}{{ 50|tuple_pair:200|paid_percent }}')
    # Arabic locale may render 25.0 as 25,0
    normalized = out.replace(',', '.')
    assert normalized == '25.0' or normalized == '25'  # rounding formatting


def test_percent_display():
    out = render('{% load billing_extras %}{{ 25|percent_display }}')
    assert out == '25%'
    out2 = render('{% load billing_extras %}{{ 12.345|percent_display:1 }}')
    assert out2 == '12.3%'


def test_remaining_amount():
    out = render('{% load billing_extras %}{% remaining_amount 200 50 %}')
    assert out == '150.0' or out == '150'


def test_payment_status():
    tpl = '{% load billing_extras %}{% payment_status 50 200 as ps %}{{ ps.status }}|{{ ps.percent }}|{{ ps.remaining }}'
    out = render(tpl)
    parts = out.split('|')
    assert parts[0] == 'partial'
    # percent ~25
    assert parts[1].startswith('25')
    assert parts[2].startswith('150')


def test_payment_status_paid():
    tpl = '{% load billing_extras %}{% payment_status 100 100 as ps %}{{ ps.status }}|{{ ps.percent }}|{{ ps.remaining }}'
    out = render(tpl)
    assert out.startswith('paid|100') or out.startswith('paid|100.0')


def test_payment_status_overpaid():
    tpl = '{% load billing_extras %}{% payment_status 150 100 as ps %}{{ ps.status }}|{{ ps.overpaid }}'
    out = render(tpl)
    # Arabic locale may render 50.0 as 50,0
    normalized = out.replace(',', '.')
    assert normalized.startswith('overpaid|50')


def test_payment_status_unpaid():
    tpl = '{% load billing_extras %}{% payment_status 0 100 as ps %}{{ ps.status }}|{{ ps.percent }}|{{ ps.remaining }}'
    out = render(tpl)
    # Arabic locale may render with comma decimals
    normalized = out.replace(',', '.')
    assert normalized.startswith('unpaid|0') and normalized.endswith('|100') or normalized.endswith('|100.0')


def test_payment_status_badge_inclusion_tag_basic():
    tpl = '{% load billing_extras %}{% payment_status_badge 50 200 %}'
    out = render(tpl)
    # Expect keywords: partial badge and 25% and remaining 150
    assert 'مدفوعة جزئياً' in out or 'partial' in out
    assert '25' in out  # percentage text
    assert '150' in out  # remaining amount appears (raw or formatted)


def test_payment_status_badge_overpaid():
    tpl = '{% load billing_extras %}{% payment_status_badge 150 100 %}'
    out = render(tpl)
    assert 'زيادة دفع' in out or 'overpaid' in out or 'تم الدفع بزيادة' in out
    # Should show +50 somewhere
    assert '+50' in out or '50' in out
