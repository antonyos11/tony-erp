"""
أمر إنشاء دليل الحسابات الصناعي الكامل
يُشغَّل مرة واحدة عند إعداد النظام
python manage.py setup_chart_of_accounts
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.accounts.models import Account, FiscalYear


class Command(BaseCommand):
    help = 'ينشئ دليل الحسابات الصناعي الكامل والسنة المالية الافتراضية'

    def handle(self, *args, **options):
        self.stdout.write('🚀 بدء إنشاء دليل الحسابات الصناعي...')
        self._create_accounts()
        self._create_fiscal_year()
        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء دليل الحسابات والسنة المالية بنجاح'))

    def _create_accounts(self):
        """قائمة دليل الحسابات الكاملة"""

        # ══════════════════════════════════════════
        # البنية: (كود, اسم, نوع, طبيعة, كود_الأب, is_detail, is_system)
        # ══════════════════════════════════════════
        accounts_data = [
            # ─── 1 الأصول ───────────────────────────────────────────
            ('1',     'الأصول',                       'asset',     'debit',  None,    False, False),
            ('11',    'الأصول المتداولة',              'asset',     'debit',  '1',     False, False),
            ('111',   'النقدية والبنوك',               'asset',     'debit',  '11',    False, False),
            ('1111',  'الخزينة الرئيسية',              'asset',     'debit',  '111',   True,  True),
            ('1112',  'البنوك',                        'asset',     'debit',  '111',   False, False),
            ('11121', 'بنك مصر',                       'asset',     'debit',  '1112',  True,  False),
            ('11122', 'البنك الأهلي',                  'asset',     'debit',  '1112',  True,  False),
            ('112',   'العملاء',                       'asset',     'debit',  '11',    False, False),
            ('1121',  'عملاء قطاعي',                   'asset',     'debit',  '112',   False, False),
            ('1122',  'عملاء جملة',                    'asset',     'debit',  '112',   False, False),
            ('1123',  'عملاء توكيلات',                 'asset',     'debit',  '112',   False, False),
            ('1124',  'عملاء موزعين',                  'asset',     'debit',  '112',   False, False),
            ('1125',  'عملاء أونلاين',                 'asset',     'debit',  '112',   False, False),
            ('113',   'أوراق القبض (شيكات واردة)',      'asset',     'debit',  '11',    True,  False),
            ('114',   'المخزون',                       'asset',     'debit',  '11',    False, False),
            ('1141',  'مخزون خامات',                   'asset',     'debit',  '114',   True,  True),
            ('1142',  'مخزون تحت التشغيل',             'asset',     'debit',  '114',   True,  True),
            ('1143',  'مخزون منتجات تامة',             'asset',     'debit',  '114',   True,  True),
            ('1144',  'مخزون مستهلكات',                'asset',     'debit',  '114',   True,  False),
            ('115',   'ضريبة مشتريات (VAT Input)',      'asset',     'debit',  '11',    True,  True),
            ('116',   'مدينون متنوعون',                'asset',     'debit',  '11',    True,  False),
            ('12',    'الأصول الثابتة',                'asset',     'debit',  '1',     False, False),
            ('121',   'أراضي ومباني',                  'asset',     'debit',  '12',    True,  False),
            ('122',   'آلات ومعدات',                   'asset',     'debit',  '12',    True,  False),
            ('123',   'سيارات ووسائل نقل',             'asset',     'debit',  '12',    True,  False),
            ('124',   'أثاث وتجهيزات',                 'asset',     'debit',  '12',    True,  False),
            ('125',   'مجمع الإهلاك',                  'asset',     'credit', '12',    True,  False),

            # ─── 2 الخصوم ───────────────────────────────────────────
            ('2',     'الخصوم',                        'liability', 'credit', None,    False, False),
            ('21',    'الخصوم المتداولة',               'liability', 'credit', '2',     False, False),
            ('211',   'الموردون',                      'liability', 'credit', '21',    False, False),
            ('2111',  'موردون محليون',                  'liability', 'credit', '211',   False, False),
            ('2112',  'موردون دوليون',                  'liability', 'credit', '211',   False, False),
            ('212',   'أوراق الدفع (شيكات صادرة)',       'liability', 'credit', '21',    True,  False),
            ('213',   'ضريبة مبيعات (VAT Output)',       'liability', 'credit', '21',    True,  True),
            ('214',   'دائنون متنوعون',                 'liability', 'credit', '21',    True,  False),
            ('215',   'رواتب مستحقة',                   'liability', 'credit', '21',    True,  False),
            ('22',    'الخصوم طويلة الأجل',             'liability', 'credit', '2',     False, False),
            ('221',   'قروض بنكية',                    'liability', 'credit', '22',    True,  False),

            # ─── 3 حقوق الملكية ─────────────────────────────────────
            ('3',     'حقوق الملكية',                  'equity',    'credit', None,    False, False),
            ('31',    'رأس المال',                      'equity',    'credit', '3',     True,  False),
            ('32',    'أرباح مرحّلة',                   'equity',    'credit', '3',     True,  False),
            ('33',    'أرباح العام',                    'equity',    'credit', '3',     True,  False),

            # ─── 4 الإيرادات ─────────────────────────────────────────
            ('4',     'الإيرادات',                     'revenue',   'credit', None,    False, False),
            ('41',    'إيرادات المبيعات',               'revenue',   'credit', '4',     False, False),
            ('411',   'مبيعات قطاعي',                   'revenue',   'credit', '41',    True,  True),
            ('412',   'مبيعات جملة',                    'revenue',   'credit', '41',    True,  True),
            ('413',   'مبيعات توكيلات',                 'revenue',   'credit', '41',    True,  True),
            ('414',   'مبيعات موزعين',                  'revenue',   'credit', '41',    True,  True),
            ('415',   'مبيعات أونلاين',                 'revenue',   'credit', '41',    True,  True),
            ('42',    'إيرادات أخرى',                   'revenue',   'credit', '4',     True,  False),
            ('43',    'مردودات المبيعات',               'revenue',   'debit',  '4',     True,  True),
            ('44',    'خصم مسموح به',                   'revenue',   'debit',  '4',     True,  True),

            # ─── 5 تكلفة المبيعات ────────────────────────────────────
            ('5',     'تكلفة المبيعات',                'cogs',      'debit',  None,    False, False),
            ('51',    'تكلفة بضاعة مباعة',              'cogs',      'debit',  '5',     True,  True),
            ('52',    'تكلفة خامات مباشرة',             'cogs',      'debit',  '5',     True,  True),
            ('53',    'تكلفة عمالة مباشرة',             'cogs',      'debit',  '5',     True,  True),
            ('54',    'تكاليف صناعية غير مباشرة',       'cogs',      'debit',  '5',     True,  True),
            ('55',    'فروق أسعار خامات',               'cogs',      'debit',  '5',     True,  True),

            # ─── 6 المصروفات ─────────────────────────────────────────
            ('6',     'المصروفات',                     'expense',   'debit',  None,    False, False),
            ('61',    'مصروفات إدارية وعمومية',         'expense',   'debit',  '6',     False, False),
            ('611',   'رواتب وأجور إدارية',             'expense',   'debit',  '61',    True,  False),
            ('612',   'إيجارات',                        'expense',   'debit',  '61',    True,  False),
            ('613',   'كهرباء ومياه',                   'expense',   'debit',  '61',    True,  False),
            ('614',   'اتصالات وإنترنت',               'expense',   'debit',  '61',    True,  False),
            ('615',   'صيانة وإصلاحات',                'expense',   'debit',  '61',    True,  False),
            ('616',   'مصروفات نقل وانتقالات',          'expense',   'debit',  '61',    True,  False),
            ('617',   'أدوات مكتبية',                   'expense',   'debit',  '61',    True,  False),
            ('618',   'إهلاكات',                        'expense',   'debit',  '61',    True,  False),
            ('619',   'مصروفات متنوعة',                'expense',   'debit',  '61',    True,  False),
            ('62',    'مصروفات بيع وتسويق',             'expense',   'debit',  '6',     False, False),
            ('621',   'مصروفات توصيل',                 'expense',   'debit',  '62',    True,  False),
            ('622',   'عمولات بائعين',                  'expense',   'debit',  '62',    True,  False),
            ('623',   'مصروفات تسويق وإعلان',           'expense',   'debit',  '62',    True,  False),
            ('63',    'مصروفات تمويلية',                'expense',   'debit',  '6',     False, False),
            ('631',   'فوائد بنكية',                    'expense',   'debit',  '63',    True,  False),
            ('632',   'عمولات بنكية',                   'expense',   'debit',  '63',    True,  False),
        ]

        created_count = 0
        updated_count = 0

        # المرحلة الأولى: إنشاء كل الحسابات بدون ربط الأب (لتفادي مشاكل الترتيب)
        for code, name, acc_type, nature, parent_code, is_detail, is_system in accounts_data:
            account, created = Account.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'account_type': acc_type,
                    'nature': nature,
                    'is_detail': is_detail,
                    'is_system': is_system,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                # تحديث البيانات لو تغيرت
                changed = False
                if account.name != name:
                    account.name = name
                    changed = True
                if account.account_type != acc_type:
                    account.account_type = acc_type
                    changed = True
                if account.is_detail != is_detail:
                    account.is_detail = is_detail
                    changed = True
                if account.is_system != is_system:
                    account.is_system = is_system
                    changed = True
                if changed:
                    account.save()
                    updated_count += 1

        # المرحلة الثانية: ربط الآباء
        for code, name, acc_type, nature, parent_code, is_detail, is_system in accounts_data:
            if parent_code:
                try:
                    account = Account.objects.get(code=code)
                    parent = Account.objects.get(code=parent_code)
                    if account.parent != parent:
                        account.parent = parent
                        account.save(update_fields=['parent'])
                except Account.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'تحذير: حساب {code} أو أبوه {parent_code} غير موجود'))

        self.stdout.write(self.style.SUCCESS(
            f'✅ الحسابات: {created_count} جديد، {updated_count} محدَّث'
        ))

    def _create_fiscal_year(self):
        """إنشاء السنة المالية الافتراضية 2026"""
        fiscal_year, created = FiscalYear.objects.get_or_create(
            name='2026',
            defaults={
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_active': True,
                'is_closed': False,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✅ تم إنشاء السنة المالية 2026'))
        else:
            self.stdout.write('السنة المالية 2026 موجودة مسبقاً')
