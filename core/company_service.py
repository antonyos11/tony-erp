"""
خدمة مركزية لجلب بيانات الشركة
تُستخدم في جميع المطبوعات والمتجر الإلكتروني والإيصالات
"""
from django.core.cache import cache


COMPANY_CACHE_KEY = 'company_full_data'
COMPANY_CACHE_TIMEOUT = 300  # 5 دقائق


def get_company_data():
    """
    جلب بيانات الشركة الكاملة مع التخزين المؤقت.
    يُستخدم في كل مكان يحتاج بيانات الشركة:
    - المطبوعات (فواتير، إيصالات، كشوف حساب)
    - المتجر الإلكتروني
    - الإيميلات والإشعارات
    """
    cached = cache.get(COMPANY_CACHE_KEY)
    if cached:
        return cached
    
    from core.models import Company, CompanyPhone
    
    company = Company.objects.first()
    if not company:
        return {
            'name': 'Tony ERP',
            'logo': None,
            'logo_url': '',
            'address': '',
            'phone': '',
            'mobile': '',
            'email': '',
            'tax_id': '',
            'commercial_register': '',
            'invoice_prefix': 'INV',
            'slogan': '',
            'footer_text': '',
            'website': '',
            'facebook': '',
            'instagram': '',
            'twitter': '',
            'whatsapp': '',
            'tiktok': '',
            'youtube': '',
            'linkedin': '',
            'phones': [],
            'print_phones': [],
            'store_phones': [],
            'currency': 'EGP',
            'currency_symbol': 'ج.م',
        }
    
    # أرقام الهواتف المتعددة
    all_phones = list(
        CompanyPhone.objects.filter(company=company, is_active=True)
        .order_by('sort_order')
        .values('phone_type', 'phone_number', 'contact_person',
                'show_on_print', 'show_on_store')
    )
    
    # أضف اسم النوع المعرب
    phone_type_map = dict(CompanyPhone.PHONE_TYPE_CHOICES)
    for p in all_phones:
        p['phone_type_display'] = phone_type_map.get(p['phone_type'], p['phone_type'])
    
    # جلب بيانات العملة
    currency_code = 'EGP'
    currency_symbol = 'ج.م'
    try:
        cur = company.get_currency()
        if cur:
            currency_code = cur.code
            currency_symbol = cur.symbol
    except Exception:
        pass
    
    data = {
        'name': company.name or 'Tony ERP',
        'logo': company.logo if company.logo else None,
        'logo_url': company.logo.url if company.logo else '',
        'address': company.address or '',
        'phone': company.phone or '',
        'mobile': company.mobile or '',
        'email': company.email or '',
        'tax_id': company.tax_id or '',
        'commercial_register': company.commercial_register or '',
        'invoice_prefix': company.invoice_prefix or 'INV',
        'slogan': company.slogan or '',
        'footer_text': company.footer_text or '',
        'website': company.website or '',
        'facebook': company.facebook or '',
        'instagram': company.instagram or '',
        'twitter': company.twitter or '',
        'whatsapp': company.whatsapp or '',
        'tiktok': company.tiktok or '',
        'youtube': company.youtube or '',
        'linkedin': company.linkedin or '',
        'phones': all_phones,
        'print_phones': [p for p in all_phones if p['show_on_print']],
        'store_phones': [p for p in all_phones if p['show_on_store']],
        'currency': currency_code,
        'currency_symbol': currency_symbol,
        'default_vat_rate': float(company.default_vat_rate) if company.default_vat_rate else 14.0,
    }
    
    cache.set(COMPANY_CACHE_KEY, data, COMPANY_CACHE_TIMEOUT)
    return data


def invalidate_company_cache():
    """تفريغ كاش بيانات الشركة - يُستدعى عند حفظ أي تغيير"""
    cache.delete(COMPANY_CACHE_KEY)
    cache.delete('company_singleton')
