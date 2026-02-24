from __future__ import annotations
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    help = "تبديل / إنشاء العملة الافتراضية (code symbol name decimals). مثال: python manage.py switch_currency EGP ج.م 'الجنيه المصري' 2"

    def add_arguments(self, parser):
        parser.add_argument('code', help='رمز العملة (3 حروف مثلاً EGP)')
        parser.add_argument('symbol', help='رمز العرض (مثلاً ج.م)')
        parser.add_argument('name', help='الاسم العربي / الظاهر')
        parser.add_argument('decimals', type=int, help='عدد المنازل العشرية')
        parser.add_argument('--no-create', action='store_true', help='عدم الإنشاء إن لم توجد العملة')

    def handle(self, *args, **opts):
        code = opts['code'].upper()
        symbol = opts['symbol']
        name = opts['name']
        decimals = opts['decimals']
        no_create = opts['no_create']
        if len(code) != 3:
            raise CommandError('الرمز يجب أن يكون 3 حروف.')
        if decimals < 0 or decimals > 6:
            raise CommandError('عدد المنازل يجب أن يكون بين 0 و 6.')
        from core.models import Currency
        from core.utils.currency import invalidate_currency_cache
        with transaction.atomic():
            obj = Currency.objects.filter(code=code).first()
            if not obj:
                if no_create:
                    raise CommandError('العملة غير موجودة ومع خيار --no-create سيتم الإلغاء.')
                obj = Currency(code=code, name=name, symbol=symbol, decimals=decimals, is_default=True)
            else:
                obj.name = name
                obj.symbol = symbol
                obj.decimals = decimals
                obj.is_default = True
            obj.save()
            # إلغاء تعيين الافتراضية عن الآخرين
            Currency.objects.exclude(pk=obj.pk).filter(is_default=True).update(is_default=False)
        invalidate_currency_cache()
        self.stdout.write(self.style.SUCCESS(f"تم ضبط {code} كعملة افتراضية (رمز: {symbol}, منازل: {decimals})."))
