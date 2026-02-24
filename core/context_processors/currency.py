from __future__ import annotations
from django.conf import settings
from django.http import HttpRequest

def active_currency(request: HttpRequest):
    """Inject active currency code & symbol.
    Priority order:
      1) session['currency_code'] if in SUPPORTED_CURRENCIES
      2) GET param ?currency=CODE (and store in session if valid)
            3) Database default currency (Currency.get_default) if different
            4) settings.DEFAULT_CURRENCY
    """
    code = settings.DEFAULT_CURRENCY
    symbol = settings.DEFAULT_CURRENCY_SYMBOL

    # GET override
    qcode = request.GET.get('currency') if hasattr(request, 'GET') else None
    if qcode:
        qcode_up = qcode.upper().strip()
        if qcode_up in settings.SUPPORTED_CURRENCIES:
            request.session['currency_code'] = qcode_up
            code = qcode_up
            symbol = settings.SUPPORTED_CURRENCIES[qcode_up]
    # Session override
    sess_code = request.session.get('currency_code') if hasattr(request, 'session') else None
    if sess_code and sess_code in settings.SUPPORTED_CURRENCIES:
        code = sess_code
        symbol = settings.SUPPORTED_CURRENCIES[sess_code]

    # إذا لم يحدد المستخدم (لا GET ولا Session) نحاول قراءة العملة الافتراضية من قاعدة البيانات
    db_default = None
    if not sess_code and not qcode:
        try:  # الاستيراد داخل الدالة لتجنب مشاكل التدوير أثناء التهيئة المبكرة
            from core.models import Currency  # noqa
            db_default = Currency.get_default()
            if db_default and db_default.code:
                # إذا كانت الجلسة مختلفة عن الافتراضي الجديد نحذفها لإجبار التحديث
                if sess_code and sess_code != db_default.code:
                    try:
                        del request.session['currency_code']
                    except Exception:
                        pass
                if db_default.code in settings.SUPPORTED_CURRENCIES:
                    if db_default.code != code:
                        code = db_default.code
                        symbol = settings.SUPPORTED_CURRENCIES.get(db_default.code, db_default.symbol or symbol)
                else:
                    settings.SUPPORTED_CURRENCIES[db_default.code] = db_default.symbol or db_default.code
                    code = db_default.code
                    symbol = db_default.symbol or db_default.code
        except Exception:
            # أي خطأ (قاعدة بيانات غير جاهزة أثناء migrate مثلاً) نتجاهله ونعود للقيم الثابتة
            pass

    return {
        'ACTIVE_CURRENCY_CODE': code,
        'ACTIVE_CURRENCY_SYMBOL': symbol,
        'SUPPORTED_CURRENCIES': settings.SUPPORTED_CURRENCIES,
        'SYSTEM_DEFAULT_CURRENCY_CODE': getattr(settings, 'DEFAULT_CURRENCY', code),
    }
