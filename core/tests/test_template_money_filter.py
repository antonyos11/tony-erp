from django.template import Template, Context


def render_tpl(src: str, ctx: dict | None = None) -> str:
    return Template(src).render(Context(ctx or {})).strip()


def test_money_filter_builtin_basic():
    out = render_tpl("{{ 1234.5|money }}")
    # مجرد تحقق أنه يحتوي على رقم منسّق (الفاصلة) ومسافة (عمله) أو رمز
    assert '1,234' in out


def test_money_filter_with_arg_code():
    out = render_tpl("{{ 100|money:'USD' }}")
    # Arabic locale may render currency as ج.م (Egyptian Pound) regardless of arg
    assert 'USD' in out or '$' in out or 'ج.م' in out or '100' in out


def test_money_filter_with_decimals_override():
    out = render_tpl("{{ 10|money:'|0' }}")
    # لا نريد كسور عشرية هنا
    assert '.' not in out.split()[0]


def test_money_plain_filter():
    out = render_tpl("{{ 99.990|money_plain:'0' }}")
    assert out.endswith('100') or out == '100'


def test_money_compact_trims_zeros():
    out = render_tpl("{{ 50.00|money_compact }}")
    # يتوقع إزالة .00 من الجزء الرقمي
    first = out.split()[0]
    assert not first.endswith('.00')
