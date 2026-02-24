"""
أمر لإنشاء بيانات تجريبية للمتجر الإلكتروني
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ecommerce.models import EcommerceSettings, ProductCategory, OnlineProduct
from inventory.models import Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للمتجر الإلكتروني'

    def handle(self, *args, **options):
        self.stdout.write('جاري إنشاء بيانات المتجر الإلكتروني...')
        
        # إنشاء إعدادات المتجر
        settings, created = EcommerceSettings.objects.get_or_create(
            pk=1,
            defaults={
                'store_name': 'متجر الشامل الإلكتروني',
                'store_description': 'أفضل المنتجات بأفضل الأسعار - تسوق الآن واستمتع بخدمة التوصيل السريع',
                'currency': 'ر.س',
                'products_per_page': 12,
                'show_out_of_stock': True,
                'enable_reviews': True,
                'enable_wishlist': True,
                'free_shipping_threshold': Decimal('200'),
                'default_shipping_cost': Decimal('25'),
                'contact_email': 'info@alshamel.com',
                'contact_phone': '+966500000000',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ تم إنشاء إعدادات المتجر'))
        
        # إنشاء الفئات
        categories_data = [
            {'name': 'الإلكترونيات', 'slug': 'electronics', 'description': 'أحدث الأجهزة الإلكترونية والهواتف الذكية'},
            {'name': 'الملابس', 'slug': 'clothing', 'description': 'أزياء رجالية ونسائية عصرية'},
            {'name': 'الأثاث', 'slug': 'furniture', 'description': 'أثاث منزلي ومكتبي عالي الجودة'},
            {'name': 'الأدوات المنزلية', 'slug': 'home-tools', 'description': 'كل ما تحتاجه لمنزلك'},
            {'name': 'الكتب والقرطاسية', 'slug': 'books', 'description': 'كتب ومستلزمات مكتبية'},
            {'name': 'الرياضة', 'slug': 'sports', 'description': 'معدات وملابس رياضية'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = ProductCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'is_active': True,
                }
            )
            categories[cat_data['slug']] = cat
            if created:
                self.stdout.write(f'  ✓ تم إنشاء فئة: {cat.name}')
        
        # الحصول على منتجات المخزون وربطها بالمتجر
        inventory_products = Product.objects.all()[:20]
        
        if inventory_products.exists():
            category_list = list(categories.values())
            for i, inv_product in enumerate(inventory_products):
                # تحقق إذا كان المنتج مربوط بالفعل
                if not hasattr(inv_product, 'online_product') or not OnlineProduct.objects.filter(inventory_item=inv_product).exists():
                    category = category_list[i % len(category_list)]
                    online_product = OnlineProduct.objects.create(
                        inventory_item=inv_product,
                        display_name=inv_product.name,
                        short_description=f'منتج عالي الجودة - {inv_product.name}',
                        full_description=f'وصف تفصيلي للمنتج: {inv_product.name}\n\nمنتج أصلي بضمان الجودة.',
                        category=category,
                        is_active=True,
                        is_featured=i < 4,  # أول 4 منتجات مميزة
                        is_new=i >= 4 and i < 8,  # 4 منتجات جديدة
                    )
                    self.stdout.write(f'  ✓ تم ربط منتج: {inv_product.name}')
        else:
            self.stdout.write(self.style.WARNING('  ⚠ لا توجد منتجات في المخزون لربطها'))
        
        # عرض الإحصائيات
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('تم إعداد المتجر الإلكتروني بنجاح!'))
        self.stdout.write(f'  - عدد الفئات: {ProductCategory.objects.count()}')
        self.stdout.write(f'  - عدد المنتجات: {OnlineProduct.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('يمكنك الآن زيارة المتجر على: http://127.0.0.1:8000/ecommerce/')
