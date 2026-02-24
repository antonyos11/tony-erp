from typing import Literal, TypedDict, Optional
from django.db import transaction
from django.contrib.auth import get_user_model

try:
    from crm.models import Customer as CRMCustomer
except Exception:  # pragma: no cover
    CRMCustomer = None  # type: ignore
try:
    from partners.models import Customer as SalesCustomer, Partner
except Exception:  # pragma: no cover
    SalesCustomer = None  # type: ignore
    Partner = None  # type: ignore


class UnifiedCustomerInfo(TypedDict, total=False):
    id: int
    full_name: str
    email: str | None
    phone: str | None
    source: Literal['crm', 'sales']


def get_or_create_unified_customer(
    name: str,
    email: str | None = None,
    phone: str | None = None,
    prefer: Literal['crm', 'sales', 'any'] = 'any',
) -> UnifiedCustomerInfo:
    """محول موحد لإرجاع (أو إنشاء) عميل من CRM أو Sales.

    المنطق:
    1. إذا كان التفضيل crm وجاهز: يُبحث بالاسم (first_name+last_name أو customer_code) ثم يُنشأ CRMCustomer.
    2. إذا كان التفضيل sales: يُبحث في partners.Customer ثم يُنشأ (مع Partner إذا احتاج).
    3. إذا كان any: يحاول أولاً CRM ثم Sales.

    لا يغير بيانات قائمة إلا إذا احتاج لإنشاء جديد.
    """
    name = name.strip()
    if not name:
        raise ValueError('اسم العميل مطلوب')

    def _crm_lookup_create():
        if CRMCustomer is None:
            return None
        # محاولة تقسيم الاسم إلى first/last
        parts = name.split()
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ''
        qs = CRMCustomer.objects.filter(first_name=first, last_name=last)
        if email:
            qs = qs.filter(email=email)
        obj = qs.first()
        if obj:
            return {'id': obj.id, 'full_name': f"{obj.first_name} {obj.last_name}".strip(), 'email': obj.email, 'phone': obj.phone, 'source': 'crm'}
        # إنشاء
        with transaction.atomic():
            code_base = 'CUS'
            seq = CRMCustomer.objects.count() + 1
            code = f"{code_base}{seq:05d}"
            obj = CRMCustomer.objects.create(
                customer_code=code,
                first_name=first,
                last_name=last or first,
                phone=phone or '',
                email=email or '',
            )
            return {'id': obj.id, 'full_name': f"{obj.first_name} {obj.last_name}".strip(), 'email': obj.email, 'phone': obj.phone, 'source': 'crm'}

    def _sales_lookup_create():
        if SalesCustomer is None:
            return None
        qs = SalesCustomer.objects.filter(name=name)
        if email:
            qs = qs.filter(email=email)
        obj = qs.first()
        if obj:
            return {'id': obj.id, 'full_name': obj.name, 'email': obj.email, 'phone': obj.phone, 'source': 'sales'}
        with transaction.atomic():
            partner = None
            if Partner is not None:
                partner = Partner.objects.create(name=name, email=email or '', phone=phone or '', partner_type='customer')
            obj = SalesCustomer.objects.create(
                partner=partner,
                name=name,
                email=email or '',
                phone=phone or '',
                address='',
            )
            return {'id': obj.id, 'full_name': obj.name, 'email': obj.email, 'phone': obj.phone, 'source': 'sales'}

    if prefer == 'crm':
        res = _crm_lookup_create()
        if res:
            return res
        # fallback
        res = _sales_lookup_create()
        if res:
            return res
    elif prefer == 'sales':
        res = _sales_lookup_create()
        if res:
            return res
        res = _crm_lookup_create()
        if res:
            return res
    else:  # any
        res = _crm_lookup_create()
        if res:
            return res
        res = _sales_lookup_create()
        if res:
            return res
    raise RuntimeError('تعذر إنشاء أو استرجاع عميل في كلا النظامين')
