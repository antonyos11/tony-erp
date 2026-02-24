from django.core.management.base import BaseCommand
from payments.models import PaymentMethod

DEFAULT_METHODS = [
    # (name, type, order)
    ('نقدي', 'cash', 1),
    ('حوالة بنكية', 'bank_transfer', 2),
    ('شيك', 'check', 3),
    ('بطاقة ائتمان', 'credit_card', 4),
    ('إنستا باي', 'instapay', 5),
    ('محفظة إلكترونية', 'wallet', 6),
    ('فودافون كاش', 'vodafone_cash', 7),
    ('أورنج كاش', 'orange_cash', 8),
    ('اتصالات كاش', 'etisalat_cash', 9),
    ('STC Pay', 'stc_pay', 10),
    ('Apple Pay', 'apple_pay', 11),
    ('Google Pay', 'google_pay', 12),
    ('PayPal', 'paypal', 13),
    ('مدى', 'mada', 14),
    ('نظام تقسيط', 'installment', 15),
]

class Command(BaseCommand):
    help = 'Seed default payment methods if they do not exist.'

    def handle(self, *args, **options):
        created = 0
        # محاولة جلب حسابات افتراضية
        from accounting.models import AccountingSettings, Account
        settings = AccountingSettings.get()
        cash_account = settings.cash_account
        ar_account = settings.ar_account
        bank_acc = None
        # heuristic: أي حساب يحتوي 'بنك' أو code يبدأ ب 1002
        bank_acc = Account.objects.filter(name__icontains='بنك').first() or Account.objects.filter(code__startswith='1002').first() or cash_account

        for name, ptype, order in DEFAULT_METHODS:
            obj, was_created = PaymentMethod.objects.get_or_create(name=name, defaults={'type': ptype, 'display_order': order})
            if not was_created and obj.type != ptype:
                # توحيد النوع في حالة اختلاف سابق
                obj.type = ptype
                obj.is_active = True
            # ضبط الترتيب إن كان القيم الافتراضي 100
            if obj.display_order == 100:
                obj.display_order = order
            # ربط حساب محاسبي بسيط
            if not obj.account:
                if ptype in ('cash', 'wallet') and cash_account:
                    obj.account = cash_account
                elif ptype in ('bank_transfer', 'check', 'credit_card', 'instapay', 'apple_pay', 'google_pay', 'paypal', 'mada', 'stc_pay') and bank_acc:
                    obj.account = bank_acc
                elif ptype in ('installment',) and ar_account:
                    obj.account = ar_account
            obj.save()
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seed complete. Created {created} methods. Total now: {PaymentMethod.objects.count()}'))
