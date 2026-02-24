"""
إعداد العملات للنظام - يشمل عملات عربية وعالمية شاملة
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Currency


class Command(BaseCommand):
    help = 'إعداد العملات للنظام (عربية + عالمية)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='حذف جميع العملات الموجودة وإعادة إنشائها'
        )

    def handle(self, *args, **options):
        """تنفيذ الأمر"""

        # أسعار الصرف التقريبية مقابل الجنيه المصري (فبراير 2026)
        currencies_data = [
            # ===== العملة الافتراضية =====
            {'code': 'EGP', 'name': 'الجنيه المصري', 'symbol': 'ج.م', 'exchange_rate': 1, 'decimal_places': 2, 'is_default': True, 'is_active': True},

            # ===== العملات العربية =====
            {'code': 'SAR', 'name': 'الريال السعودي', 'symbol': 'ر.س', 'exchange_rate': 13.33, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'AED', 'name': 'الدرهم الإماراتي', 'symbol': 'د.إ', 'exchange_rate': 13.62, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'KWD', 'name': 'الدينار الكويتي', 'symbol': 'د.ك', 'exchange_rate': 162.50, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'QAR', 'name': 'الريال القطري', 'symbol': 'ر.ق', 'exchange_rate': 13.74, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'OMR', 'name': 'الريال العماني', 'symbol': 'ر.ع', 'exchange_rate': 130.00, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'BHD', 'name': 'الدينار البحريني', 'symbol': 'د.ب', 'exchange_rate': 132.71, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'JOD', 'name': 'الدينار الأردني', 'symbol': 'د.ا', 'exchange_rate': 70.57, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'LBP', 'name': 'الليرة اللبنانية', 'symbol': 'ل.ل', 'exchange_rate': 0.00056, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'SYP', 'name': 'الليرة السورية', 'symbol': 'ل.س', 'exchange_rate': 0.004, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'IQD', 'name': 'الدينار العراقي', 'symbol': 'د.ع', 'exchange_rate': 0.038, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'YER', 'name': 'الريال اليمني', 'symbol': 'ر.ي', 'exchange_rate': 0.20, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'SDG', 'name': 'الجنيه السوداني', 'symbol': 'ج.س', 'exchange_rate': 0.083, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'MAD', 'name': 'الدرهم المغربي', 'symbol': 'د.م', 'exchange_rate': 5.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'TND', 'name': 'الدينار التونسي', 'symbol': 'د.ت', 'exchange_rate': 16.00, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'DZD', 'name': 'الدينار الجزائري', 'symbol': 'د.ج', 'exchange_rate': 0.37, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'LYD', 'name': 'الدينار الليبي', 'symbol': 'د.ل', 'exchange_rate': 10.35, 'decimal_places': 3, 'is_default': False, 'is_active': True},
            {'code': 'MRU', 'name': 'الأوقية الموريتانية', 'symbol': 'أ.م', 'exchange_rate': 1.26, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'SOS', 'name': 'الشلن الصومالي', 'symbol': 'Sh', 'exchange_rate': 0.088, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'DJF', 'name': 'الفرنك الجيبوتي', 'symbol': 'Fdj', 'exchange_rate': 0.28, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'KMF', 'name': 'الفرنك القمري', 'symbol': 'CF', 'exchange_rate': 0.11, 'decimal_places': 0, 'is_default': False, 'is_active': True},

            # ===== العملات العالمية الرئيسية =====
            {'code': 'USD', 'name': 'الدولار الأمريكي', 'symbol': '$', 'exchange_rate': 50.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'EUR', 'name': 'اليورو', 'symbol': '€', 'exchange_rate': 52.50, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'GBP', 'name': 'الجنيه الإسترليني', 'symbol': '£', 'exchange_rate': 63.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'JPY', 'name': 'الين الياباني', 'symbol': '¥', 'exchange_rate': 0.33, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'CHF', 'name': 'الفرنك السويسري', 'symbol': 'Fr', 'exchange_rate': 56.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CAD', 'name': 'الدولار الكندي', 'symbol': 'C$', 'exchange_rate': 35.50, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'AUD', 'name': 'الدولار الأسترالي', 'symbol': 'A$', 'exchange_rate': 32.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'NZD', 'name': 'الدولار النيوزيلندي', 'symbol': 'NZ$', 'exchange_rate': 29.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CNY', 'name': 'اليوان الصيني', 'symbol': '¥', 'exchange_rate': 6.90, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'HKD', 'name': 'الدولار الهونج كونجي', 'symbol': 'HK$', 'exchange_rate': 6.40, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'SGD', 'name': 'الدولار السنغافوري', 'symbol': 'S$', 'exchange_rate': 37.50, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'SEK', 'name': 'الكرونة السويدية', 'symbol': 'kr', 'exchange_rate': 4.70, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'NOK', 'name': 'الكرونة النرويجية', 'symbol': 'kr', 'exchange_rate': 4.60, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'DKK', 'name': 'الكرونة الدنماركية', 'symbol': 'kr', 'exchange_rate': 7.05, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'ISK', 'name': 'الكرونة الآيسلندية', 'symbol': 'kr', 'exchange_rate': 0.36, 'decimal_places': 0, 'is_default': False, 'is_active': True},

            # ===== عملات أوروبية =====
            {'code': 'PLN', 'name': 'الزلوتي البولندي', 'symbol': 'zł', 'exchange_rate': 12.40, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CZK', 'name': 'الكورونا التشيكية', 'symbol': 'Kč', 'exchange_rate': 2.15, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'HUF', 'name': 'الفورنت المجري', 'symbol': 'Ft', 'exchange_rate': 0.13, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'RON', 'name': 'الليو الروماني', 'symbol': 'lei', 'exchange_rate': 10.55, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'BGN', 'name': 'الليف البلغاري', 'symbol': 'лв', 'exchange_rate': 26.85, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'HRK', 'name': 'الكونا الكرواتية', 'symbol': 'kn', 'exchange_rate': 6.95, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'RSD', 'name': 'الدينار الصربي', 'symbol': 'din', 'exchange_rate': 0.47, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'UAH', 'name': 'الهريفنيا الأوكرانية', 'symbol': '₴', 'exchange_rate': 1.21, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'GEL', 'name': 'اللاري الجورجي', 'symbol': '₾', 'exchange_rate': 18.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'RUB', 'name': 'الروبل الروسي', 'symbol': '₽', 'exchange_rate': 0.53, 'decimal_places': 2, 'is_default': False, 'is_active': True},

            # ===== عملات آسيوية =====
            {'code': 'INR', 'name': 'الروبية الهندية', 'symbol': '₹', 'exchange_rate': 0.59, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'PKR', 'name': 'الروبية الباكستانية', 'symbol': 'Rs', 'exchange_rate': 0.18, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'BDT', 'name': 'التاكا البنجلاديشية', 'symbol': '৳', 'exchange_rate': 0.42, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'LKR', 'name': 'الروبية السريلانكية', 'symbol': 'Rs', 'exchange_rate': 0.15, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'NPR', 'name': 'الروبية النيبالية', 'symbol': 'Rs', 'exchange_rate': 0.37, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'THB', 'name': 'البات التايلاندي', 'symbol': '฿', 'exchange_rate': 1.45, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'MYR', 'name': 'الرينجيت الماليزي', 'symbol': 'RM', 'exchange_rate': 11.20, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'IDR', 'name': 'الروبية الإندونيسية', 'symbol': 'Rp', 'exchange_rate': 0.0031, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'PHP', 'name': 'البيزو الفلبيني', 'symbol': '₱', 'exchange_rate': 0.87, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'VND', 'name': 'الدونج الفيتنامي', 'symbol': '₫', 'exchange_rate': 0.002, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'KRW', 'name': 'الوون الكوري', 'symbol': '₩', 'exchange_rate': 0.035, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'TWD', 'name': 'الدولار التايواني', 'symbol': 'NT$', 'exchange_rate': 1.54, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'MMK', 'name': 'الكيات الميانماري', 'symbol': 'K', 'exchange_rate': 0.024, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'KHR', 'name': 'الريال الكمبودي', 'symbol': '៛', 'exchange_rate': 0.012, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'LAK', 'name': 'الكيب اللاوسي', 'symbol': '₭', 'exchange_rate': 0.0023, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'MNT', 'name': 'التوغريك المنغولي', 'symbol': '₮', 'exchange_rate': 0.015, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'KZT', 'name': 'التينغة الكازاخستانية', 'symbol': '₸', 'exchange_rate': 0.10, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'UZS', 'name': 'السوم الأوزبكستاني', 'symbol': 'soʻm', 'exchange_rate': 0.004, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'AFN', 'name': 'الأفغاني الأفغانستاني', 'symbol': '؋', 'exchange_rate': 0.70, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'IRR', 'name': 'الريال الإيراني', 'symbol': '﷼', 'exchange_rate': 0.0012, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'TRY', 'name': 'الليرة التركية', 'symbol': '₺', 'exchange_rate': 1.37, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'ILS', 'name': 'الشيكل الإسرائيلي', 'symbol': '₪', 'exchange_rate': 13.70, 'decimal_places': 2, 'is_default': False, 'is_active': True},

            # ===== عملات أفريقية =====
            {'code': 'ZAR', 'name': 'الراند الجنوب أفريقي', 'symbol': 'R', 'exchange_rate': 2.70, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'NGN', 'name': 'النايرا النيجيرية', 'symbol': '₦', 'exchange_rate': 0.031, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'GHS', 'name': 'السيدي الغاني', 'symbol': 'GH₵', 'exchange_rate': 3.20, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'KES', 'name': 'الشلن الكيني', 'symbol': 'KSh', 'exchange_rate': 0.39, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'TZS', 'name': 'الشلن التنزاني', 'symbol': 'TSh', 'exchange_rate': 0.019, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'UGX', 'name': 'الشلن الأوغندي', 'symbol': 'USh', 'exchange_rate': 0.013, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'ETB', 'name': 'البر الإثيوبي', 'symbol': 'Br', 'exchange_rate': 0.42, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'XOF', 'name': 'فرنك غرب أفريقيا', 'symbol': 'CFA', 'exchange_rate': 0.080, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'XAF', 'name': 'فرنك وسط أفريقيا', 'symbol': 'FCFA', 'exchange_rate': 0.080, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'RWF', 'name': 'الفرنك الرواندي', 'symbol': 'RF', 'exchange_rate': 0.037, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'MZN', 'name': 'الميتيكال الموزمبيقي', 'symbol': 'MT', 'exchange_rate': 0.78, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'AOA', 'name': 'الكوانزا الأنغولية', 'symbol': 'Kz', 'exchange_rate': 0.055, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CDF', 'name': 'الفرنك الكونغولي', 'symbol': 'FC', 'exchange_rate': 0.018, 'decimal_places': 2, 'is_default': False, 'is_active': True},

            # ===== عملات أمريكا اللاتينية =====
            {'code': 'BRL', 'name': 'الريال البرازيلي', 'symbol': 'R$', 'exchange_rate': 8.60, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'MXN', 'name': 'البيزو المكسيكي', 'symbol': 'Mex$', 'exchange_rate': 2.90, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'ARS', 'name': 'البيزو الأرجنتيني', 'symbol': 'AR$', 'exchange_rate': 0.046, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CLP', 'name': 'البيزو التشيلي', 'symbol': 'CL$', 'exchange_rate': 0.052, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'COP', 'name': 'البيزو الكولومبي', 'symbol': 'CO$', 'exchange_rate': 0.012, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'PEN', 'name': 'السول البيروفي', 'symbol': 'S/', 'exchange_rate': 13.30, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'UYU', 'name': 'البيزو الأوروغوياني', 'symbol': '$U', 'exchange_rate': 1.17, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'BOB', 'name': 'البوليفيانو البوليفي', 'symbol': 'Bs', 'exchange_rate': 7.24, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'PYG', 'name': 'الغواراني الباراغوياني', 'symbol': '₲', 'exchange_rate': 0.0065, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'DOP', 'name': 'البيزو الدومينيكاني', 'symbol': 'RD$', 'exchange_rate': 0.84, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'CRC', 'name': 'الكولون الكوستاريكي', 'symbol': '₡', 'exchange_rate': 0.097, 'decimal_places': 0, 'is_default': False, 'is_active': True},
            {'code': 'GTQ', 'name': 'الكيتزال الغواتيمالي', 'symbol': 'Q', 'exchange_rate': 6.45, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'HNL', 'name': 'اللمبيرا الهندوراسية', 'symbol': 'L', 'exchange_rate': 2.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'NIO', 'name': 'الكوردوبا النيكاراغوية', 'symbol': 'C$', 'exchange_rate': 1.36, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'PAB', 'name': 'البالبوا البنمية', 'symbol': 'B/', 'exchange_rate': 50.00, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'JMD', 'name': 'الدولار الجامايكي', 'symbol': 'J$', 'exchange_rate': 0.32, 'decimal_places': 2, 'is_default': False, 'is_active': True},
            {'code': 'TTD', 'name': 'الدولار الترينيدادي', 'symbol': 'TT$', 'exchange_rate': 7.36, 'decimal_places': 2, 'is_default': False, 'is_active': True},
        ]

        with transaction.atomic():
            if options['reset']:
                self.stdout.write('حذف جميع العملات الموجودة...')
                Currency.objects.all().delete()

            self.stdout.write('إنشاء العملات...')

            created_count = 0
            updated_count = 0

            for currency_data in currencies_data:
                currency, created = Currency.objects.get_or_create(
                    code=currency_data['code'],
                    defaults=currency_data
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  + {currency.name} ({currency.code})')
                    )
                else:
                    for key, value in currency_data.items():
                        if key not in ('code', 'is_default'):
                            setattr(currency, key, value)
                    if currency_data.get('is_default'):
                        currency.is_default = True
                    currency.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ~ {currency.name} ({currency.code}) [تحديث]')
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('تم الانتهاء بنجاح!'))
        self.stdout.write(f'   تم إنشاء: {created_count} عملة جديدة')
        self.stdout.write(f'   تم تحديث: {updated_count} عملة موجودة')
        self.stdout.write(f'   إجمالي العملات: {Currency.objects.count()}')

        default_currency = Currency.objects.filter(is_default=True).first()
        if default_currency:
            self.stdout.write(self.style.SUCCESS(f'   العملة الافتراضية: {default_currency.name}'))
        else:
            self.stdout.write(self.style.ERROR('   لا توجد عملة افتراضية!'))