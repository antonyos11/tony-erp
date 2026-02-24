"""
أمر لإنشاء طرق الدفع الافتراضية
"""
from django.core.management.base import BaseCommand
from payments.models import PaymentMethod


class Command(BaseCommand):
    help = 'إنشاء طرق الدفع الافتراضية'

    def handle(self, *args, **options):
        payment_methods = [
            {'name': 'نقداً', 'type': 'cash', 'display_order': 1},
            {'name': 'بطاقة ائتمانية', 'type': 'credit_card', 'display_order': 2},
            {'name': 'تحويل بنكي', 'type': 'bank_transfer', 'display_order': 3},
            {'name': 'شيك', 'type': 'check', 'display_order': 4},
            {'name': 'إنستا باي', 'type': 'instapay', 'display_order': 5},
            {'name': 'فودافون كاش', 'type': 'vodafone_cash', 'display_order': 6},
            {'name': 'أورنج كاش', 'type': 'orange_cash', 'display_order': 7},
            {'name': 'اتصالات كاش', 'type': 'etisalat_cash', 'display_order': 8},
            {'name': 'STC Pay', 'type': 'stc_pay', 'display_order': 9},
            {'name': 'Apple Pay', 'type': 'apple_pay', 'display_order': 10},
            {'name': 'Google Pay', 'type': 'google_pay', 'display_order': 11},
            {'name': 'PayPal', 'type': 'paypal', 'display_order': 12},
            {'name': 'مدى', 'type': 'mada', 'display_order': 13},
            {'name': 'محفظة إلكترونية', 'type': 'wallet', 'display_order': 14},
            {'name': 'تقسيط', 'type': 'installment', 'display_order': 15},
        ]

        created_count = 0
        for pm_data in payment_methods:
            pm, created = PaymentMethod.objects.get_or_create(
                type=pm_data['type'],
                defaults={
                    'name': pm_data['name'],
                    'display_order': pm_data['display_order'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'تم إنشاء: {pm.name}'))
            else:
                self.stdout.write(f'موجود بالفعل: {pm.name}')

        self.stdout.write(self.style.SUCCESS(f'\nتم إنشاء {created_count} طريقة دفع جديدة'))
