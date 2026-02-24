from __future__ import annotations
from django.core.management.base import BaseCommand, CommandError
from core.models import Currency
from django.core.cache import cache

class Command(BaseCommand):
    help = "اضبط عملة افتراضية جديدة: python manage.py set_default_currency EGP"

    def add_arguments(self, parser):
        parser.add_argument('code', type=str, help='رمز العملة (EGP, USD, ...).')
        parser.add_argument('--symbol', type=str, help='رمز العملة إن رغبت بتعديله.')
        parser.add_argument('--name', type=str, help='اسم العملة بالعربي.')
        parser.add_argument('--decimals', type=int, default=2, help='عدد الخانات العشرية.')
        parser.add_argument('--rate', type=float, default=1.0, help='سعر الصرف مقابل العملة الافتراضية الجديدة (يُجبر على 1 للعملة الافتراضية).')

    def handle(self, *args, **options):
        code = options['code'].upper().strip()
        symbol = options.get('symbol')
        name = options.get('name')
        decimals = options.get('decimals')
        rate = options.get('rate') or 1

        if len(code) != 3:
            raise CommandError('الرمز يجب أن يكون 3 حروف.')

        cur, created = Currency.objects.get_or_create(code=code, defaults={
            'name': name or code,
            'symbol': symbol or code,
            'is_active': True,
            'is_default': True,
            'exchange_rate': 1,
            'decimal_places': decimals,
        })
        if not created:
            changed = False
            if symbol and cur.symbol != symbol:
                cur.symbol = symbol; changed = True
            if name and cur.name != name:
                cur.name = name; changed = True
            if cur.exchange_rate != 1:
                cur.exchange_rate = 1; changed = True
            if cur.decimal_places != decimals:
                cur.decimal_places = decimals; changed = True
            if not cur.is_active:
                cur.is_active = True; changed = True
            if not cur.is_default:
                cur.is_default = True; changed = True
            if changed:
                cur.save()
            else:
                # ضمان إعادة ضبط الافتراضية وحذف الافتراضية القديمة
                Currency.objects.filter(is_default=True).exclude(pk=cur.pk).update(is_default=False)
                cur.is_default = True
                cur.exchange_rate = 1
                cur.save()
        else:
            # ألغ الافتراضية عن العملات الأخرى
            Currency.objects.filter(is_default=True).exclude(pk=cur.pk).update(is_default=False)

        # تنظيف الكاش المتعلق
        cache.delete('default_currency')
        cache.delete('active_currencies')

        self.stdout.write(self.style.SUCCESS(f"تم ضبط {code} كعملة افتراضية (رمز: {cur.symbol})"))
