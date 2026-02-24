"""
أمر Django لإنشاء شجرة الحسابات الافتراضية للنشاط المختلط

الاستخدام:
python manage.py create_default_coa

الخيارات:
--reset: حذف جميع الحسابات الموجودة وإعادة إنشائها
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounting.models import Account, AccountType


class Command(BaseCommand):
    help = 'إنشاء شجرة حسابات افتراضية للنشاط المختلط (تجاري + خدمي + تصنيعي)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='حذف جميع الحسابات الموجودة وإعادة إنشائها',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌳 بدء إنشاء شجرة الحسابات الافتراضية...\n'))
        
        # التحقق من وجود حسابات
        existing_count = Account.objects.count()
        
        if existing_count > 0 and not options['reset']:
            self.stdout.write(self.style.WARNING(
                f'⚠️ يوجد {existing_count} حساب في النظام.\n'
                f'استخدم --reset لحذف الحسابات الموجودة وإعادة الإنشاء.\n'
            ))
            return
        
        if options['reset'] and existing_count > 0:
            self.stdout.write(self.style.WARNING(f'🗑️ حذف {existing_count} حساب موجود...'))
            Account.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ تم حذف الحسابات القديمة\n'))
        
        try:
            with transaction.atomic():
                # إنشاء الحسابات
                created_count = self._create_chart_of_accounts()
                
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ تم إنشاء شجرة الحسابات بنجاح!\n'
                    f'📊 إجمالي الحسابات المنشأة: {created_count}\n'
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ خطأ في إنشاء شجرة الحسابات: {str(e)}\n'))
            raise
    
    def _create_chart_of_accounts(self):
        """إنشاء شجرة الحسابات بالكامل"""
        total_created = 0
        
        # 1. الأصول
        self.stdout.write('📂 إنشاء حسابات الأصول...')
        total_created += self._create_assets()
        
        # 2. الالتزامات
        self.stdout.write('📂 إنشاء حسابات الالتزامات...')
        total_created += self._create_liabilities()
        
        # 3. حقوق الملكية
        self.stdout.write('📂 إنشاء حسابات حقوق الملكية...')
        total_created += self._create_equity()
        
        # 4. الإيرادات
        self.stdout.write('📂 إنشاء حسابات الإيرادات...')
        total_created += self._create_revenue()
        
        # 5. المصروفات
        self.stdout.write('📂 إنشاء حسابات المصروفات...')
        total_created += self._create_expenses()
        
        return total_created
    
    def _create_account(self, code, name, account_type, parent=None, is_group=False, description=''):
        """إنشاء حساب واحد"""
        account = Account.objects.create(
            code=code,
            name=name,
            account_type=account_type,
            parent=parent,
            is_group=is_group,
            can_post=not is_group,
            description=description
        )
        return account
    
    def _create_assets(self):
        """إنشاء حسابات الأصول"""
        count = 0
        
        # 1. الأصول (رئيسي)
        assets = self._create_account('1', 'الأصول', AccountType.ASSET, is_group=True)
        count += 1
        
        # 1.1 الأصول المتداولة
        current_assets = self._create_account('1.1', 'الأصول المتداولة', AccountType.ASSET, assets, is_group=True)
        count += 1
        
        # 1.1.1 النقدية والبنوك
        cash_banks = self._create_account('1.1.1', 'النقدية والبنوك', AccountType.ASSET, current_assets, is_group=True)
        count += 1
        
        cash_accounts = [
            ('1.1.1.001', 'الخزينة الرئيسية'),
            ('1.1.1.002', 'الخزينة الفرعية - المبيعات'),
            ('1.1.1.003', 'الخزينة الفرعية - المشتريات'),
            ('1.1.1.010', 'البنك الأهلي - حساب جاري'),
            ('1.1.1.011', 'بنك مصر - حساب جاري'),
            ('1.1.1.012', 'البنك التجاري - حساب ادخار'),
        ]
        for code, name in cash_accounts:
            self._create_account(code, name, AccountType.ASSET, cash_banks)
            count += 1
        
        # 1.1.2 الذمم المدينة
        receivables = self._create_account('1.1.2', 'الذمم المدينة', AccountType.ASSET, current_assets, is_group=True)
        count += 1
        
        receivables_accounts = [
            ('1.1.2.001', 'عملاء تجاريون - آجل'),
            ('1.1.2.002', 'عملاء خدمات - آجل'),
            ('1.1.2.010', 'أوراق قبض'),
            ('1.1.2.011', 'شيكات تحت التحصيل - عملاء'),
            ('1.1.2.020', 'مدينون متنوعون'),
            ('1.1.2.030', 'سلف وعهد موظفين'),
        ]
        for code, name in receivables_accounts:
            self._create_account(code, name, AccountType.ASSET, receivables)
            count += 1
        
        # 1.1.3 المخزون
        inventory = self._create_account('1.1.3', 'المخزون', AccountType.ASSET, current_assets, is_group=True)
        count += 1
        
        inventory_accounts = [
            ('1.1.3.001', 'مخزون بضاعة تامة - المخزن الرئيسي'),
            ('1.1.3.010', 'مخزون مواد خام'),
            ('1.1.3.020', 'مخزون إنتاج تحت التشغيل (WIP)'),
            ('1.1.3.030', 'مخزون منتجات تامة الصنع'),
            ('1.1.3.040', 'مخزون قطع غيار ومستلزمات'),
        ]
        for code, name in inventory_accounts:
            self._create_account(code, name, AccountType.ASSET, inventory)
            count += 1
        
        # 1.2 الأصول الثابتة
        fixed_assets = self._create_account('1.2', 'الأصول الثابتة', AccountType.ASSET, assets, is_group=True)
        count += 1
        
        # 1.2.2 المباني
        buildings = self._create_account('1.2.2', 'المباني والإنشاءات', AccountType.ASSET, fixed_assets, is_group=True)
        count += 1
        
        building_accounts = [
            ('1.2.2.001', 'مبنى المصنع'),
            ('1.2.2.002', 'مبنى المعرض'),
            ('1.2.2.900', 'مجمع إهلاك المباني'),
        ]
        for code, name in building_accounts:
            self._create_account(code, name, AccountType.ASSET, buildings)
            count += 1
        
        # 1.2.3 الآلات والمعدات
        equipment = self._create_account('1.2.3', 'الآلات والمعدات', AccountType.ASSET, fixed_assets, is_group=True)
        count += 1
        
        equipment_accounts = [
            ('1.2.3.001', 'آلات الإنتاج'),
            ('1.2.3.002', 'خطوط التصنيع'),
            ('1.2.3.900', 'مجمع إهلاك الآلات والمعدات'),
        ]
        for code, name in equipment_accounts:
            self._create_account(code, name, AccountType.ASSET, equipment)
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء {count} حساب أصول'))
        return count
    
    def _create_liabilities(self):
        """إنشاء حسابات الالتزامات"""
        count = 0
        
        # 2. الالتزامات
        liabilities = self._create_account('2', 'الالتزامات', AccountType.LIABILITY, is_group=True)
        count += 1
        
        # 2.1 الالتزامات المتداولة
        current_liabilities = self._create_account('2.1', 'الالتزامات المتداولة', AccountType.LIABILITY, liabilities, is_group=True)
        count += 1
        
        # 2.1.1 الذمم الدائنة
        payables = self._create_account('2.1.1', 'الذمم الدائنة', AccountType.LIABILITY, current_liabilities, is_group=True)
        count += 1
        
        payables_accounts = [
            ('2.1.1.001', 'موردو بضاعة - آجل'),
            ('2.1.1.002', 'موردو مواد خام - آجل'),
            ('2.1.1.010', 'أوراق دفع'),
            ('2.1.1.020', 'دائنون متنوعون'),
        ]
        for code, name in payables_accounts:
            self._create_account(code, name, AccountType.LIABILITY, payables)
            count += 1
        
        # 2.1.4 ضرائب مستحقة
        taxes = self._create_account('2.1.4', 'ضرائب مستحقة', AccountType.LIABILITY, current_liabilities, is_group=True)
        count += 1
        
        tax_accounts = [
            ('2.1.4.001', 'ضريبة القيمة المضافة (VAT)'),
            ('2.1.4.003', 'ضريبة الدخل'),
            ('2.1.4.010', 'تأمينات اجتماعية'),
        ]
        for code, name in tax_accounts:
            self._create_account(code, name, AccountType.LIABILITY, taxes)
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء {count} حساب التزامات'))
        return count
    
    def _create_equity(self):
        """إنشاء حسابات حقوق الملكية"""
        count = 0
        
        # 3. حقوق الملكية
        equity = self._create_account('3', 'حقوق الملكية', AccountType.EQUITY, is_group=True)
        count += 1
        
        # 3.1 رأس المال
        capital = self._create_account('3.1', 'رأس المال', AccountType.EQUITY, equity, is_group=True)
        count += 1
        
        self._create_account('3.1.1.001', 'رأس المال المدفوع', AccountType.EQUITY, capital)
        count += 1
        
        # 3.2 الأرباح المحتجزة
        retained = self._create_account('3.2', 'الأرباح المحتجزة', AccountType.EQUITY, equity, is_group=True)
        count += 1
        
        retained_accounts = [
            ('3.2.1.001', 'أرباح محتجزة من سنوات سابقة'),
            ('3.2.1.002', 'أرباح السنة الحالية'),
        ]
        for code, name in retained_accounts:
            self._create_account(code, name, AccountType.EQUITY, retained)
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء {count} حساب حقوق ملكية'))
        return count
    
    def _create_revenue(self):
        """إنشاء حسابات الإيرادات"""
        count = 0
        
        # 4. الإيرادات
        revenue = self._create_account('4', 'الإيرادات', AccountType.REVENUE, is_group=True)
        count += 1
        
        # 4.1 إيرادات التشغيل
        operating = self._create_account('4.1', 'إيرادات التشغيل الرئيسية', AccountType.REVENUE, revenue, is_group=True)
        count += 1
        
        # 4.1.1 مبيعات تجارية
        sales = self._create_account('4.1.1', 'إيرادات المبيعات - نشاط تجاري', AccountType.REVENUE, operating, is_group=True)
        count += 1
        
        sales_accounts = [
            ('4.1.1.001', 'مبيعات بضاعة - نقدي'),
            ('4.1.1.002', 'مبيعات بضاعة - آجل'),
        ]
        for code, name in sales_accounts:
            self._create_account(code, name, AccountType.REVENUE, sales)
            count += 1
        
        # 4.1.2 إيرادات خدمات
        services = self._create_account('4.1.2', 'إيرادات الخدمات', AccountType.REVENUE, operating, is_group=True)
        count += 1
        
        service_accounts = [
            ('4.1.2.001', 'إيرادات خدمات استشارية'),
            ('4.1.2.002', 'إيرادات خدمات صيانة'),
        ]
        for code, name in service_accounts:
            self._create_account(code, name, AccountType.REVENUE, services)
            count += 1
        
        # 4.1.3 إيرادات تصنيع
        manufacturing = self._create_account('4.1.3', 'إيرادات الإنتاج (التصنيع)', AccountType.REVENUE, operating, is_group=True)
        count += 1
        
        self._create_account('4.1.3.001', 'مبيعات منتجات تامة الصنع', AccountType.REVENUE, manufacturing)
        count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء {count} حساب إيرادات'))
        return count
    
    def _create_expenses(self):
        """إنشاء حسابات المصروفات"""
        count = 0
        
        # 5. المصروفات
        expenses = self._create_account('5', 'المصروفات', AccountType.EXPENSE, is_group=True)
        count += 1
        
        # 5.1 تكلفة المبيعات
        cogs = self._create_account('5.1', 'تكلفة البضاعة المباعة', AccountType.EXPENSE, expenses, is_group=True)
        count += 1
        
        # 5.1.1 تكلفة تجارية
        trade_cogs = self._create_account('5.1.1', 'تكلفة البضاعة - نشاط تجاري', AccountType.EXPENSE, cogs, is_group=True)
        count += 1
        
        trade_accounts = [
            ('5.1.1.001', 'مشتريات بضاعة - نقدي'),
            ('5.1.1.002', 'مشتريات بضاعة - آجل'),
            ('5.1.1.020', 'مصاريف شحن ونقل مشتريات'),
        ]
        for code, name in trade_accounts:
            self._create_account(code, name, AccountType.EXPENSE, trade_cogs)
            count += 1
        
        # 5.1.2 تكلفة تصنيع
        manuf_cogs = self._create_account('5.1.2', 'تكلفة المنتجات - نشاط تصنيعي', AccountType.EXPENSE, cogs, is_group=True)
        count += 1
        
        manuf_accounts = [
            ('5.1.2.001', 'مواد خام مستخدمة'),
            ('5.1.2.002', 'أجور عمال إنتاج مباشرة'),
        ]
        for code, name in manuf_accounts:
            self._create_account(code, name, AccountType.EXPENSE, manuf_cogs)
            count += 1
        
        # 5.2 المصروفات التشغيلية
        operating_exp = self._create_account('5.2', 'المصروفات التشغيلية', AccountType.EXPENSE, expenses, is_group=True)
        count += 1
        
        # 5.2.1 مصروفات بيع وتسويق
        sales_exp = self._create_account('5.2.1', 'مصروفات البيع والتسويق', AccountType.EXPENSE, operating_exp, is_group=True)
        count += 1
        
        sales_exp_accounts = [
            ('5.2.1.001', 'رواتب موظفي المبيعات'),
            ('5.2.1.003', 'مصاريف دعاية وإعلان'),
        ]
        for code, name in sales_exp_accounts:
            self._create_account(code, name, AccountType.EXPENSE, sales_exp)
            count += 1
        
        # 5.2.2 مصروفات إدارية
        admin_exp = self._create_account('5.2.2', 'المصروفات الإدارية والعمومية', AccountType.EXPENSE, operating_exp, is_group=True)
        count += 1
        
        admin_exp_accounts = [
            ('5.2.2.001', 'رواتب موظفي إداريين'),
            ('5.2.2.002', 'إيجار مكاتب ومعارض'),
            ('5.2.2.003', 'كهرباء ومياه - إداري'),
            ('5.2.2.004', 'اتصالات وإنترنت'),
        ]
        for code, name in admin_exp_accounts:
            self._create_account(code, name, AccountType.EXPENSE, admin_exp)
            count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ تم إنشاء {count} حساب مصروفات'))
        return count

