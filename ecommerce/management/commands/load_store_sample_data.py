"""
أمر إدارة Django لتحميل بيانات تجريبية للمتجر الإلكتروني
يشمل: بوابات الدفع، شركات الشحن، التواصل الاجتماعي، التصنيفات، المنتجات، البانرات، محتوى الصفحات
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
import random

from ecommerce.models import (
    PaymentGateway, ShippingCompany, SocialMediaIntegration,
    ProductCategory, OnlineProduct, StoreBanner, StorePageContent,
    EcommerceSettings, Coupon
)


class Command(BaseCommand):
    help = 'تحميل بيانات تجريبية للمتجر الإلكتروني'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='حذف البيانات الموجودة قبل الإضافة',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('🗑️  حذف البيانات الموجودة...')
            PaymentGateway.objects.all().delete()
            ShippingCompany.objects.all().delete()
            SocialMediaIntegration.objects.all().delete()
            ProductCategory.objects.all().delete()
            OnlineProduct.objects.all().delete()
            StoreBanner.objects.all().delete()
            StorePageContent.objects.all().delete()
            Coupon.objects.all().delete()

        self.stdout.write('\n' + '='*60)
        self.stdout.write('🏪 تحميل بيانات المتجر التجريبية')
        self.stdout.write('='*60 + '\n')

        self.create_payment_gateways()
        self.create_shipping_companies()
        self.create_social_media()
        self.create_categories()
        self.create_products()
        self.create_banners()
        self.create_page_content()
        self.create_coupons()
        self.update_settings()

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ تم تحميل جميع البيانات التجريبية بنجاح!'))
        self.stdout.write('='*60 + '\n')

    def create_payment_gateways(self):
        """إنشاء بوابات الدفع"""
        self.stdout.write('\n💳 إنشاء بوابات الدفع...')
        
        gateways = [
            {
                'gateway_type': 'stripe',
                'name': 'Stripe',
                'description': 'بوابة دفع عالمية تدعم جميع البطاقات البنكية',
                'api_key': 'sk_live_xxxxxxxxxxxx',
                'sandbox_api_key': 'sk_test_xxxxxxxxxxxx',
                'is_sandbox': True,
                'is_active': True,
                'sort_order': 1,
            },
            {
                'gateway_type': 'paypal',
                'name': 'PayPal',
                'description': 'الدفع عبر PayPal - الأكثر أماناً',
                'api_key': 'paypal_client_id_xxx',
                'api_secret': 'paypal_secret_xxx',
                'is_sandbox': True,
                'is_active': True,
                'sort_order': 2,
            },
            {
                'gateway_type': 'tap',
                'name': 'Tap Payments',
                'description': 'بوابة دفع للشرق الأوسط - تدعم مدى وكي نت',
                'api_key': 'sk_live_tap_xxxxx',
                'sandbox_api_key': 'sk_test_tap_xxxxx',
                'is_sandbox': True,
                'is_active': True,
                'sort_order': 3,
            },
            {
                'gateway_type': 'moyasar',
                'name': 'Moyasar',
                'description': 'بوابة دفع سعودية - تدعم مدى و Apple Pay',
                'api_key': 'sk_live_moyasar_xxx',
                'sandbox_api_key': 'sk_test_moyasar_xxx',
                'is_sandbox': True,
                'is_active': True,
                'sort_order': 4,
            },
            {
                'gateway_type': 'hyperpay',
                'name': 'HyperPay',
                'description': 'بوابة دفع إقليمية للشرق الأوسط',
                'api_key': 'hyperpay_entity_id',
                'api_secret': 'hyperpay_access_token',
                'is_sandbox': True,
                'is_active': False,
                'sort_order': 5,
            },
            {
                'gateway_type': 'cod',
                'name': 'الدفع عند الاستلام',
                'description': 'ادفع نقداً عند استلام طلبك',
                'is_sandbox': False,
                'is_active': True,
                'sort_order': 10,
            },
            {
                'gateway_type': 'bank_transfer',
                'name': 'تحويل بنكي',
                'description': 'حول المبلغ مباشرة لحسابنا البنكي',
                'is_sandbox': False,
                'is_active': True,
                'extra_settings': {
                    'bank_name': 'البنك الأهلي السعودي',
                    'account_number': 'SA0000000000000000000000',
                    'iban': 'SA0000000000000000000000',
                    'swift_code': 'NCBKSAJE',
                },
                'sort_order': 11,
            },
        ]

        for gateway_data in gateways:
            gateway, created = PaymentGateway.objects.get_or_create(
                gateway_type=gateway_data['gateway_type'],
                defaults=gateway_data
            )
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {gateway.name}')

    def create_shipping_companies(self):
        """إنشاء شركات الشحن"""
        self.stdout.write('\n🚚 إنشاء شركات الشحن...')
        
        companies = [
            {
                'company_type': 'aramex',
                'name': 'أرامكس',
                'description': 'شحن سريع لجميع أنحاء العالم',
                'api_key': 'aramex_account_xxx',
                'api_secret': 'aramex_password_xxx',
                'account_number': '12345678',
                'is_sandbox': True,
                'is_active': True,
                'calculation_type': 'weight',
                'flat_rate': Decimal('25.00'),
                'weight_rate': Decimal('5.00'),
                'free_shipping_threshold': Decimal('500.00'),
                'sort_order': 1,
            },
            {
                'company_type': 'dhl',
                'name': 'DHL Express',
                'description': 'شحن دولي سريع وموثوق',
                'api_key': 'dhl_api_key_xxx',
                'api_secret': 'dhl_api_secret_xxx',
                'account_number': 'DHL123456',
                'is_sandbox': True,
                'is_active': True,
                'calculation_type': 'weight',
                'flat_rate': Decimal('45.00'),
                'weight_rate': Decimal('10.00'),
                'free_shipping_threshold': Decimal('1000.00'),
                'sort_order': 2,
            },
            {
                'company_type': 'smsa',
                'name': 'SMSA Express',
                'description': 'شحن محلي سريع داخل المملكة',
                'api_key': 'smsa_passkey_xxx',
                'account_number': 'SMSA123',
                'is_sandbox': True,
                'is_active': True,
                'calculation_type': 'flat',
                'flat_rate': Decimal('18.00'),
                'weight_rate': Decimal('3.00'),
                'free_shipping_threshold': Decimal('300.00'),
                'sort_order': 3,
            },
            {
                'company_type': 'fedex',
                'name': 'FedEx',
                'description': 'خدمات شحن عالمية متميزة',
                'api_key': 'fedex_api_key_xxx',
                'api_secret': 'fedex_secret_xxx',
                'account_number': 'FEDEX789',
                'is_sandbox': True,
                'is_active': False,
                'calculation_type': 'weight',
                'flat_rate': Decimal('50.00'),
                'weight_rate': Decimal('12.00'),
                'free_shipping_threshold': Decimal('1500.00'),
                'sort_order': 4,
            },
            {
                'company_type': 'custom',
                'name': 'توصيل محلي',
                'description': 'توصيل مجاني داخل المدينة',
                'is_sandbox': False,
                'is_active': True,
                'calculation_type': 'flat',
                'flat_rate': Decimal('0.00'),
                'weight_rate': Decimal('0.00'),
                'free_shipping_threshold': Decimal('0.00'),
                'sort_order': 10,
            },
        ]

        for company_data in companies:
            company, created = ShippingCompany.objects.get_or_create(
                company_type=company_data['company_type'],
                name=company_data['name'],
                defaults=company_data
            )
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {company.name}')

    def create_social_media(self):
        """إنشاء حسابات التواصل الاجتماعي"""
        self.stdout.write('\n📱 إنشاء حسابات التواصل الاجتماعي...')
        
        socials = [
            {
                'platform': 'facebook',
                'profile_url': 'https://facebook.com/mystore',
                'app_id': '123456789',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': True,
                'sort_order': 1,
            },
            {
                'platform': 'instagram',
                'profile_url': 'https://instagram.com/mystore',
                'username': '@mystore',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': True,
                'sort_order': 2,
            },
            {
                'platform': 'twitter',
                'profile_url': 'https://twitter.com/mystore',
                'username': '@mystore',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': True,
                'sort_order': 3,
            },
            {
                'platform': 'whatsapp',
                'profile_url': 'https://wa.me/966501234567',
                'username': '+966501234567',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': True,
                'sort_order': 4,
            },
            {
                'platform': 'youtube',
                'profile_url': 'https://youtube.com/c/mystore',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': False,
                'sort_order': 5,
            },
            {
                'platform': 'tiktok',
                'profile_url': 'https://tiktok.com/@mystore',
                'username': '@mystore',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': False,
                'sort_order': 6,
            },
            {
                'platform': 'snapchat',
                'profile_url': 'https://snapchat.com/add/mystore',
                'username': 'mystore',
                'is_active': True,
                'show_in_footer': True,
                'enable_sharing': False,
                'sort_order': 7,
            },
        ]

        for social_data in socials:
            social, created = SocialMediaIntegration.objects.get_or_create(
                platform=social_data['platform'],
                defaults=social_data
            )
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {social.get_platform_display()}')

    def create_categories(self):
        """إنشاء التصنيفات"""
        self.stdout.write('\n📁 إنشاء التصنيفات...')
        
        categories = [
            {
                'name': 'الإلكترونيات',
                'slug': 'electronics',
                'description': 'أحدث الأجهزة الإلكترونية والذكية',
                'is_active': True,
            },
            {
                'name': 'الأزياء والملابس',
                'slug': 'fashion',
                'description': 'أحدث صيحات الموضة والأزياء',
                'is_active': True,
            },
            {
                'name': 'المنزل والحديقة',
                'slug': 'home-garden',
                'description': 'كل ما يخص المنزل والحديقة',
                'is_active': True,
            },
            {
                'name': 'الجمال والعناية',
                'slug': 'beauty',
                'description': 'منتجات التجميل والعناية الشخصية',
                'is_active': True,
            },
            {
                'name': 'الرياضة واللياقة',
                'slug': 'sports',
                'description': 'معدات رياضية وملابس لياقة',
                'is_active': True,
            },
            {
                'name': 'الكتب والقرطاسية',
                'slug': 'books',
                'description': 'كتب ومستلزمات مكتبية',
                'is_active': True,
            },
            {
                'name': 'الألعاب والهوايات',
                'slug': 'toys-hobbies',
                'description': 'ألعاب للأطفال ومستلزمات الهوايات',
                'is_active': True,
            },
            {
                'name': 'الطعام والمشروبات',
                'slug': 'food-drinks',
                'description': 'أطعمة ومشروبات متنوعة',
                'is_active': True,
            },
        ]

        created_categories = {}
        for cat_data in categories:
            category, created = ProductCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            created_categories[cat_data['slug']] = category
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {category.name}')
        
        return created_categories

    def create_products(self):
        """إنشاء المنتجات"""
        self.stdout.write('\n📦 إنشاء المنتجات...')
        
        # Import inventory Product model
        from inventory.models import Product as InventoryProduct
        
        # الحصول على التصنيفات
        categories = {cat.slug: cat for cat in ProductCategory.objects.all()}
        
        products_data = [
            # إلكترونيات
            {
                'sku': 'ELEC-001',
                'name': 'آيفون 15 برو ماكس',
                'category_slug': 'electronics',
                'short_description': 'أحدث هاتف من أبل بمعالج A17 Pro',
                'full_description': '''<h4>آيفون 15 برو ماكس</h4>
                <p>استمتع بأقوى آيفون على الإطلاق مع معالج A17 Pro الثوري وكاميرا 48 ميجابكسل.</p>
                <ul>
                    <li>شاشة Super Retina XDR مقاس 6.7 بوصة</li>
                    <li>معالج A17 Pro الأسرع على الإطلاق</li>
                    <li>نظام كاميرا Pro بدقة 48 ميجابكسل</li>
                    <li>إطار من التيتانيوم</li>
                </ul>''',
                'price': Decimal('4999.00'),
                'cost': Decimal('4200.00'),
                'custom_price': Decimal('4799.00'),
                'is_featured': True,
            },
            {
                'sku': 'ELEC-002',
                'name': 'سامسونج جالاكسي S24 الترا',
                'category_slug': 'electronics',
                'short_description': 'هاتف ذكي بتقنية Galaxy AI',
                'full_description': '''<h4>سامسونج جالاكسي S24 الترا</h4>
                <p>اكتشف قوة الذكاء الاصطناعي مع Galaxy AI.</p>''',
                'price': Decimal('4599.00'),
                'cost': Decimal('3900.00'),
                'is_featured': True,
            },
            {
                'sku': 'ELEC-003',
                'name': 'ماك بوك برو 14 بوصة',
                'category_slug': 'electronics',
                'short_description': 'لابتوب احترافي بشريحة M3 Pro',
                'full_description': '''<h4>ماك بوك برو 14 بوصة</h4>
                <p>قوة خارقة للمحترفين مع شريحة M3 Pro.</p>''',
                'price': Decimal('8499.00'),
                'cost': Decimal('7200.00'),
                'custom_price': Decimal('7999.00'),
                'is_featured': True,
            },
            {
                'sku': 'ELEC-004',
                'name': 'سماعات AirPods Pro 2',
                'category_slug': 'electronics',
                'short_description': 'سماعات لاسلكية مع إلغاء الضوضاء',
                'full_description': 'سماعات AirPods Pro الجيل الثاني مع إلغاء ضوضاء نشط محسّن.',
                'price': Decimal('999.00'),
                'cost': Decimal('750.00'),
                'is_featured': False,
            },
            # أزياء
            {
                'sku': 'FASH-001',
                'name': 'ثوب رجالي فاخر',
                'category_slug': 'fashion',
                'short_description': 'ثوب رجالي من القطن الفاخر',
                'full_description': 'ثوب رجالي مصنوع من أجود أنواع القطن المصري.',
                'price': Decimal('450.00'),
                'cost': Decimal('250.00'),
                'custom_price': Decimal('399.00'),
                'is_featured': True,
            },
            {
                'sku': 'FASH-002',
                'name': 'عباية نسائية مطرزة',
                'category_slug': 'fashion',
                'short_description': 'عباية أنيقة بتطريز يدوي',
                'full_description': 'عباية نسائية فاخرة بتطريز يدوي راقي.',
                'price': Decimal('850.00'),
                'cost': Decimal('500.00'),
                'is_featured': True,
            },
            {
                'sku': 'FASH-003',
                'name': 'حذاء رياضي Nike Air Max',
                'category_slug': 'fashion',
                'short_description': 'حذاء رياضي مريح للغاية',
                'full_description': 'حذاء Nike Air Max للراحة القصوى أثناء المشي والرياضة.',
                'price': Decimal('599.00'),
                'cost': Decimal('350.00'),
                'custom_price': Decimal('499.00'),
                'is_featured': False,
            },
            # منزل
            {
                'sku': 'HOME-001',
                'name': 'طقم كنب فاخر 7 مقاعد',
                'category_slug': 'home-garden',
                'short_description': 'طقم كنب عصري بتصميم أنيق',
                'full_description': 'طقم كنب فاخر من 7 مقاعد بتصميم عصري وخامات عالية الجودة.',
                'price': Decimal('12500.00'),
                'cost': Decimal('8000.00'),
                'custom_price': Decimal('10999.00'),
                'is_featured': True,
            },
            {
                'sku': 'HOME-002',
                'name': 'مكنسة روبوت ذكية',
                'category_slug': 'home-garden',
                'short_description': 'مكنسة ذكية تنظف تلقائياً',
                'full_description': 'مكنسة روبوت ذكية مع خاصية الشفط والمسح معاً.',
                'price': Decimal('1299.00'),
                'cost': Decimal('900.00'),
                'is_featured': False,
            },
            # جمال
            {
                'sku': 'BEAU-001',
                'name': 'مجموعة العناية بالبشرة الكورية',
                'category_slug': 'beauty',
                'short_description': 'روتين كامل للعناية بالبشرة',
                'full_description': 'مجموعة كاملة من 10 منتجات للعناية بالبشرة على الطريقة الكورية.',
                'price': Decimal('799.00'),
                'cost': Decimal('400.00'),
                'custom_price': Decimal('649.00'),
                'is_featured': True,
            },
            {
                'sku': 'BEAU-002',
                'name': 'عطر فاخر للرجال',
                'category_slug': 'beauty',
                'short_description': 'عطر فرنسي فاخر للرجال',
                'full_description': 'عطر فرنسي أصلي برائحة خشبية مميزة تدوم طوال اليوم.',
                'price': Decimal('450.00'),
                'cost': Decimal('280.00'),
                'is_featured': False,
            },
            # رياضة
            {
                'sku': 'SPRT-001',
                'name': 'جهاز مشي كهربائي',
                'category_slug': 'sports',
                'short_description': 'جهاز مشي منزلي احترافي',
                'full_description': 'جهاز مشي كهربائي قابل للطي مع شاشة LED وبرامج تدريب متنوعة.',
                'price': Decimal('2999.00'),
                'cost': Decimal('1800.00'),
                'custom_price': Decimal('2499.00'),
                'is_featured': True,
            },
            {
                'sku': 'SPRT-002',
                'name': 'دمبل قابل للتعديل 24 كجم',
                'category_slug': 'sports',
                'short_description': 'دمبل يعوض عن 15 دمبل',
                'full_description': 'دمبل قابل للتعديل من 2.5 إلى 24 كجم - يغنيك عن شراء مجموعة كاملة.',
                'price': Decimal('899.00'),
                'cost': Decimal('600.00'),
                'is_featured': False,
            },
        ]

        for prod_data in products_data:
            category_slug = prod_data.pop('category_slug')
            category = categories.get(category_slug)
            
            # بيانات منتج المخزون
            inv_defaults = {
                'name': prod_data['name'],
                'description': prod_data.get('full_description', ''),
                'price': prod_data['price'],
                'cost': prod_data.get('cost', Decimal('0')),
            }
            
            # إنشاء أو الحصول على منتج المخزون
            inv_product, inv_created = InventoryProduct.objects.get_or_create(
                sku=prod_data['sku'],
                defaults=inv_defaults
            )
            
            # بيانات المنتج الإلكتروني
            online_defaults = {
                'display_name': prod_data['name'],
                'short_description': prod_data.get('short_description', ''),
                'full_description': prod_data.get('full_description', ''),
                'category': category,
                'custom_price': prod_data.get('custom_price'),
                'is_featured': prod_data.get('is_featured', False),
                'is_active': True,
            }
            
            # إنشاء أو الحصول على المنتج الإلكتروني
            online_product, online_created = OnlineProduct.objects.get_or_create(
                inventory_item=inv_product,
                defaults=online_defaults
            )
            
            if online_created:
                status = '✓ جديد'
            elif inv_created:
                status = '↺ محدث'
            else:
                status = '↺ موجود'
            
            self.stdout.write(f'  {status}: {online_product.name}')

    def create_banners(self):
        """إنشاء البانرات"""
        self.stdout.write('\n🖼️  إنشاء البانرات...')
        self.stdout.write('  ⚠️ تم تخطي البانرات (تحتاج صور)')
        self.stdout.write('  ℹ️ يمكنك إضافة البانرات من لوحة التحكم مع رفع الصور')

    def create_page_content(self):
        """إنشاء محتوى الصفحات"""
        self.stdout.write('\n📝 إنشاء محتوى الصفحات...')
        
        pages = [
            {
                'page': 'about',
                'title': 'من نحن',
                'content': '''
                <div class="about-content">
                    <h2>مرحباً بكم في متجرنا</h2>
                    <p class="lead">نحن متجر إلكتروني رائد نقدم أفضل المنتجات بأفضل الأسعار.</p>
                    
                    <h3>رؤيتنا</h3>
                    <p>أن نكون الوجهة الأولى للتسوق الإلكتروني في المنطقة.</p>
                    
                    <h3>مهمتنا</h3>
                    <p>توفير تجربة تسوق استثنائية مع منتجات عالية الجودة وخدمة عملاء متميزة.</p>
                    
                    <h3>قيمنا</h3>
                    <ul>
                        <li><strong>الجودة:</strong> نختار منتجاتنا بعناية فائقة</li>
                        <li><strong>الثقة:</strong> نضمن رضا عملائنا</li>
                        <li><strong>السرعة:</strong> توصيل سريع وآمن</li>
                        <li><strong>الدعم:</strong> خدمة عملاء على مدار الساعة</li>
                    </ul>
                </div>
                ''',
                'meta_title': 'من نحن - تعرف علينا',
                'meta_description': 'تعرف على قصتنا ورؤيتنا ومهمتنا في تقديم أفضل تجربة تسوق إلكتروني',
                'is_active': True,
            },
            {
                'page': 'contact',
                'title': 'اتصل بنا',
                'content': '''
                <div class="contact-content">
                    <h2>تواصل معنا</h2>
                    <p>نسعد بتواصلكم معنا في أي وقت</p>
                    
                    <div class="row">
                        <div class="col-md-4">
                            <h4><i class="fas fa-phone"></i> الهاتف</h4>
                            <p>+966 50 123 4567</p>
                        </div>
                        <div class="col-md-4">
                            <h4><i class="fas fa-envelope"></i> البريد الإلكتروني</h4>
                            <p>support@mystore.com</p>
                        </div>
                        <div class="col-md-4">
                            <h4><i class="fas fa-map-marker-alt"></i> العنوان</h4>
                            <p>الرياض، المملكة العربية مصر</p>
                        </div>
                    </div>
                    
                    <h3>ساعات العمل</h3>
                    <p>الأحد - الخميس: 9 صباحاً - 9 مساءً</p>
                    <p>الجمعة - السبت: 2 ظهراً - 9 مساءً</p>
                </div>
                ''',
                'meta_title': 'اتصل بنا - تواصل معنا',
                'meta_description': 'تواصل معنا للاستفسارات والدعم الفني - خدمة عملاء على مدار الساعة',
                'is_active': True,
            },
            {
                'page': 'faq',
                'title': 'الأسئلة الشائعة',
                'content': '''
                <div class="faq-content">
                    <div class="accordion" id="faqAccordion">
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">
                                    كيف يمكنني تتبع طلبي؟
                                </button>
                            </h2>
                            <div id="faq1" class="accordion-collapse collapse show">
                                <div class="accordion-body">
                                    يمكنك تتبع طلبك من خلال صفحة "طلباتي" بعد تسجيل الدخول، أو من خلال رابط التتبع المرسل على بريدك الإلكتروني.
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">
                                    ما هي سياسة الإرجاع؟
                                </button>
                            </h2>
                            <div id="faq2" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    يمكنك إرجاع المنتج خلال 14 يوماً من الاستلام بشرط أن يكون في حالته الأصلية مع العبوة الأصلية.
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">
                                    ما هي طرق الدفع المتاحة؟
                                </button>
                            </h2>
                            <div id="faq3" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    نقبل الدفع بالبطاقات البنكية (فيزا، ماستركارد، مدى)، Apple Pay، تحويل بنكي، والدفع عند الاستلام.
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq4">
                                    كم تستغرق مدة التوصيل؟
                                </button>
                            </h2>
                            <div id="faq4" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    داخل الرياض: 1-2 أيام عمل<br>
                                    باقي مناطق المملكة: 3-5 أيام عمل<br>
                                    التوصيل الدولي: 7-14 يوم عمل
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                'meta_title': 'الأسئلة الشائعة',
                'meta_description': 'إجابات على الأسئلة الأكثر شيوعاً حول الشراء والدفع والشحن والإرجاع',
                'is_active': True,
            },
            {
                'page': 'privacy',
                'title': 'سياسة الخصوصية',
                'content': '''
                <div class="privacy-content">
                    <h2>سياسة الخصوصية</h2>
                    <p>آخر تحديث: ديسمبر 2024</p>
                    
                    <h3>جمع المعلومات</h3>
                    <p>نجمع المعلومات التي تقدمها لنا مباشرة عند إنشاء حساب أو إجراء عملية شراء.</p>
                    
                    <h3>استخدام المعلومات</h3>
                    <p>نستخدم معلوماتك لمعالجة طلباتك وتحسين خدماتنا والتواصل معك.</p>
                    
                    <h3>حماية المعلومات</h3>
                    <p>نستخدم أحدث تقنيات التشفير والأمان لحماية بياناتك.</p>
                    
                    <h3>مشاركة المعلومات</h3>
                    <p>لا نشارك معلوماتك مع أطراف ثالثة إلا لأغراض الشحن والدفع.</p>
                </div>
                ''',
                'meta_title': 'سياسة الخصوصية',
                'meta_description': 'تعرف على كيفية جمع واستخدام وحماية معلوماتك الشخصية',
                'is_active': True,
            },
            {
                'page': 'terms',
                'title': 'الشروط والأحكام',
                'content': '''
                <div class="terms-content">
                    <h2>الشروط والأحكام</h2>
                    <p>باستخدامك لهذا الموقع، فإنك توافق على الشروط والأحكام التالية.</p>
                    
                    <h3>1. القبول بالشروط</h3>
                    <p>باستخدام موقعنا، فإنك توافق على الالتزام بهذه الشروط.</p>
                    
                    <h3>2. الأسعار والدفع</h3>
                    <p>جميع الأسعار بالج.م السعودي وتشمل ضريبة القيمة المضافة.</p>
                    
                    <h3>3. الشحن والتوصيل</h3>
                    <p>نلتزم بتوصيل طلبك في الوقت المحدد. في حالة التأخير، سنتواصل معك.</p>
                    
                    <h3>4. الإرجاع والاستبدال</h3>
                    <p>يمكنك إرجاع المنتج خلال 14 يوماً وفقاً لسياسة الإرجاع.</p>
                    
                    <h3>5. الملكية الفكرية</h3>
                    <p>جميع المحتويات على الموقع محمية بحقوق الملكية الفكرية.</p>
                </div>
                ''',
                'meta_title': 'الشروط والأحكام',
                'meta_description': 'الشروط والأحكام الخاصة باستخدام موقعنا وإجراء عمليات الشراء',
                'is_active': True,
            },
            {
                'page': 'shipping',
                'title': 'سياسة الشحن',
                'content': '''
                <div class="shipping-content">
                    <h2>سياسة الشحن والتوصيل</h2>
                    
                    <h3>مناطق التوصيل</h3>
                    <p>نوصل لجميع مناطق المملكة العربية مصر ودول الخليج.</p>
                    
                    <h3>أوقات التوصيل</h3>
                    <table class="table">
                        <tr><td>الرياض</td><td>1-2 أيام عمل</td></tr>
                        <tr><td>المدن الرئيسية</td><td>2-3 أيام عمل</td></tr>
                        <tr><td>باقي المناطق</td><td>3-5 أيام عمل</td></tr>
                        <tr><td>دول الخليج</td><td>5-7 أيام عمل</td></tr>
                    </table>
                    
                    <h3>تكلفة الشحن</h3>
                    <ul>
                        <li>شحن مجاني للطلبات فوق 300 ر.س</li>
                        <li>25 ر.س للطلبات أقل من 300 ر.س</li>
                        <li>الشحن الدولي يحسب حسب الوزن والوجهة</li>
                    </ul>
                    
                    <h3>تتبع الشحنة</h3>
                    <p>ستحصل على رقم تتبع فور شحن طلبك لمتابعة حالة التوصيل.</p>
                </div>
                ''',
                'meta_title': 'سياسة الشحن والتوصيل',
                'meta_description': 'معلومات عن الشحن ومناطق التوصيل والتكلفة وأوقات التوصيل',
                'is_active': True,
            },
            {
                'page': 'returns',
                'title': 'سياسة الإرجاع',
                'content': '''
                <div class="returns-content">
                    <h2>سياسة الإرجاع والاستبدال</h2>
                    
                    <h3>شروط الإرجاع</h3>
                    <ul>
                        <li>الإرجاع خلال 14 يوماً من تاريخ الاستلام</li>
                        <li>المنتج في حالته الأصلية مع العبوة الأصلية</li>
                        <li>عدم استخدام المنتج أو إتلافه</li>
                        <li>إرفاق فاتورة الشراء</li>
                    </ul>
                    
                    <h3>المنتجات غير القابلة للإرجاع</h3>
                    <ul>
                        <li>المنتجات الشخصية والملابس الداخلية</li>
                        <li>مستحضرات التجميل المفتوحة</li>
                        <li>المنتجات الرقمية</li>
                        <li>المنتجات المخصصة حسب الطلب</li>
                    </ul>
                    
                    <h3>خطوات الإرجاع</h3>
                    <ol>
                        <li>تواصل معنا عبر خدمة العملاء</li>
                        <li>احصل على رقم إرجاع (RMA)</li>
                        <li>أرسل المنتج لعنواننا</li>
                        <li>استرد أموالك خلال 5-7 أيام عمل</li>
                    </ol>
                </div>
                ''',
                'meta_title': 'سياسة الإرجاع والاستبدال',
                'meta_description': 'تعرف على شروط وخطوات إرجاع واستبدال المنتجات',
                'is_active': True,
            },
        ]

        for page_data in pages:
            page, created = StorePageContent.objects.get_or_create(
                page=page_data['page'],
                defaults=page_data
            )
            if not created and not page.content:
                # تحديث المحتوى إذا كان فارغاً
                for key, value in page_data.items():
                    setattr(page, key, value)
                page.save()
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {page.title}')

    def create_coupons(self):
        """إنشاء كوبونات الخصم"""
        self.stdout.write('\n🎟️  إنشاء كوبونات الخصم...')
        
        from django.utils import timezone
        from datetime import timedelta
        
        coupons = [
            {
                'code': 'WELCOME10',
                'discount_type': 'percentage',
                'discount_value': Decimal('10.00'),
                'min_order_amount': Decimal('100.00'),
                'max_discount': Decimal('50.00'),
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=365),
                'usage_limit': 1000,
                'is_active': True,
            },
            {
                'code': 'SAVE50',
                'discount_type': 'fixed',
                'discount_value': Decimal('50.00'),
                'min_order_amount': Decimal('300.00'),
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=90),
                'usage_limit': 500,
                'is_active': True,
            },
            {
                'code': 'FREESHIP',
                'discount_type': 'fixed',
                'discount_value': Decimal('30.00'),  # خصم ثابت يعادل الشحن
                'min_order_amount': Decimal('200.00'),
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=60),
                'usage_limit': 200,
                'is_active': True,
            },
            {
                'code': 'VIP25',
                'discount_type': 'percentage',
                'discount_value': Decimal('25.00'),
                'min_order_amount': Decimal('500.00'),
                'max_discount': Decimal('200.00'),
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=30),
                'usage_limit': 100,
                'is_active': True,
            },
        ]

        for coupon_data in coupons:
            coupon, created = Coupon.objects.get_or_create(
                code=coupon_data['code'],
                defaults=coupon_data
            )
            status = '✓ جديد' if created else '↺ موجود'
            self.stdout.write(f'  {status}: {coupon.code}')

    def update_settings(self):
        """تحديث إعدادات المتجر"""
        self.stdout.write('\n⚙️  تحديث إعدادات المتجر...')
        
        settings = EcommerceSettings.get_settings()
        settings.store_name = 'متجري الإلكتروني'
        settings.store_description = 'متجر إلكتروني متكامل لأفضل المنتجات بأفضل الأسعار'
        settings.contact_email = 'info@mystore.com'
        settings.contact_phone = '+966501234567'
        settings.whatsapp_number = '+966501234567'
        settings.currency = 'EGP'
        settings.free_shipping_threshold = Decimal('300.00')
        settings.default_shipping_cost = Decimal('30.00')
        settings.is_active = True
        settings.save()
        
        self.stdout.write('  ✓ تم تحديث إعدادات المتجر')
