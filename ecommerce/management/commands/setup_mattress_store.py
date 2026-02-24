"""
أمر لإنشاء متجر المراتب والمفروشات
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ecommerce.models import EcommerceSettings, ProductCategory, OnlineProduct
from inventory.models import Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'إنشاء متجر المراتب والمفروشات'

    def handle(self, *args, **options):
        self.stdout.write('جاري إعداد متجر المراتب والمفروشات...')
        
        # تحديث إعدادات المتجر
        settings, created = EcommerceSettings.objects.update_or_create(
            pk=1,
            defaults={
                'store_name': 'متجر المراتب والمفروشات',
                'store_description': 'أفضل المراتب الطبية والمفروشات عالية الجودة - راحتك أولويتنا',
                'currency': 'ج.م',
                'products_per_page': 12,
                'show_out_of_stock': True,
                'enable_reviews': True,
                'enable_wishlist': True,
                'free_shipping_threshold': Decimal('2000'),
                'default_shipping_cost': Decimal('100'),
                'contact_email': 'info@mattress-store.com',
                'contact_phone': '+201000000000',
                'whatsapp_number': '+201000000000',
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ تم تحديث إعدادات المتجر'))
        
        # حذف الفئات القديمة
        ProductCategory.objects.all().delete()
        self.stdout.write('  ✓ تم حذف الفئات القديمة')
        
        # إنشاء الفئات الجديدة
        categories_data = [
            {
                'name': 'المراتب الطبية',
                'slug': 'medical-mattresses',
                'description': 'مراتب طبية بأحدث التقنيات لراحة ظهرك وجسمك',
                'children': [
                    {'name': 'مراتب سوست منفصلة', 'slug': 'pocket-spring', 'description': 'مراتب بسوست منفصلة لدعم أفضل'},
                    {'name': 'مراتب سوست متصلة', 'slug': 'bonnell-spring', 'description': 'مراتب كلاسيكية بسوست متصلة'},
                    {'name': 'مراتب ميموري فوم', 'slug': 'memory-foam', 'description': 'مراتب ميموري فوم للراحة القصوى'},
                    {'name': 'مراتب لاتكس', 'slug': 'latex', 'description': 'مراتب لاتكس طبيعي'},
                    {'name': 'مراتب هايبرد', 'slug': 'hybrid', 'description': 'مراتب تجمع بين السوست والفوم'},
                ]
            },
            {
                'name': 'المراتب حسب المقاس',
                'slug': 'mattress-sizes',
                'description': 'اختر المقاس المناسب لسريرك',
                'children': [
                    {'name': 'مراتب مفردة (90×190)', 'slug': 'single-90', 'description': 'مراتب مفردة'},
                    {'name': 'مراتب مفردة كبيرة (100×200)', 'slug': 'single-100', 'description': 'مراتب مفردة كبيرة'},
                    {'name': 'مراتب مزدوجة (140×190)', 'slug': 'double-140', 'description': 'مراتب مزدوجة'},
                    {'name': 'مراتب كوين (160×200)', 'slug': 'queen-160', 'description': 'مراتب كوين سايز'},
                    {'name': 'مراتب كينج (180×200)', 'slug': 'king-180', 'description': 'مراتب كينج سايز'},
                    {'name': 'مراتب سوبر كينج (200×200)', 'slug': 'super-king-200', 'description': 'مراتب سوبر كينج'},
                ]
            },
            {
                'name': 'الوسائد',
                'slug': 'pillows',
                'description': 'وسائد طبية ومريحة لنوم هادئ',
                'children': [
                    {'name': 'وسائد ميموري فوم', 'slug': 'memory-foam-pillows', 'description': 'وسائد ميموري فوم'},
                    {'name': 'وسائد فايبر', 'slug': 'fiber-pillows', 'description': 'وسائد فايبر ناعمة'},
                    {'name': 'وسائد ريش', 'slug': 'feather-pillows', 'description': 'وسائد ريش طبيعي'},
                    {'name': 'وسائد طبية للرقبة', 'slug': 'orthopedic-pillows', 'description': 'وسائد طبية للرقبة'},
                    {'name': 'وسائد جل', 'slug': 'gel-pillows', 'description': 'وسائد جل باردة'},
                ]
            },
            {
                'name': 'اللحاف والبطاطين',
                'slug': 'duvets-blankets',
                'description': 'لحاف فايبر وبطاطين دافئة',
                'children': [
                    {'name': 'لحاف فايبر', 'slug': 'fiber-duvet', 'description': 'لحاف فايبر خفيف ودافئ'},
                    {'name': 'لحاف سيليكون', 'slug': 'silicone-duvet', 'description': 'لحاف سيليكون فاخر'},
                    {'name': 'بطاطين صوف', 'slug': 'wool-blankets', 'description': 'بطاطين صوف دافئة'},
                    {'name': 'بطاطين فرو', 'slug': 'fur-blankets', 'description': 'بطاطين فرو ناعمة'},
                    {'name': 'مفارش صيفية', 'slug': 'summer-covers', 'description': 'مفارش خفيفة للصيف'},
                ]
            },
            {
                'name': 'أغطية المراتب',
                'slug': 'mattress-protectors',
                'description': 'حماية مراتبك وإطالة عمرها',
                'children': [
                    {'name': 'أغطية ضد الماء', 'slug': 'waterproof-protectors', 'description': 'حماية من السوائل'},
                    {'name': 'أغطية قطنية', 'slug': 'cotton-protectors', 'description': 'أغطية قطن طبيعي'},
                    {'name': 'توبر ميموري فوم', 'slug': 'memory-foam-topper', 'description': 'طبقة إضافية للراحة'},
                    {'name': 'أغطية مبطنة', 'slug': 'quilted-protectors', 'description': 'أغطية مبطنة فاخرة'},
                ]
            },
            {
                'name': 'ملايات وأطقم',
                'slug': 'bed-sheets',
                'description': 'ملايات قطنية وأطقم سرير كاملة',
                'children': [
                    {'name': 'ملايات قطن 100%', 'slug': 'cotton-sheets', 'description': 'ملايات قطن مصري'},
                    {'name': 'ملايات ساتان', 'slug': 'satin-sheets', 'description': 'ملايات ساتان فاخرة'},
                    {'name': 'أطقم سرير كاملة', 'slug': 'complete-bedding-sets', 'description': 'أطقم سرير متكاملة'},
                    {'name': 'ملايات بأستك', 'slug': 'fitted-sheets', 'description': 'ملايات بأستك محيط'},
                    {'name': 'أكياس وسادات', 'slug': 'pillowcases', 'description': 'أكياس وسائد'},
                ]
            },
            {
                'name': 'مراتب الأطفال',
                'slug': 'kids-mattresses',
                'description': 'مراتب مخصصة للأطفال والرضع',
                'children': [
                    {'name': 'مراتب سرير أطفال', 'slug': 'crib-mattresses', 'description': 'مراتب للرضع'},
                    {'name': 'مراتب أطفال صغيرة', 'slug': 'toddler-mattresses', 'description': 'للأطفال الصغار'},
                    {'name': 'مراتب أطفال مفردة', 'slug': 'kids-single', 'description': 'مراتب أطفال مفردة'},
                    {'name': 'وسائد أطفال', 'slug': 'kids-pillows', 'description': 'وسائد مخصصة للأطفال'},
                ]
            },
            {
                'name': 'إكسسوارات النوم',
                'slug': 'sleep-accessories',
                'description': 'كل ما تحتاجه لنوم مريح',
                'children': [
                    {'name': 'وسائد ديكور', 'slug': 'decorative-pillows', 'description': 'وسائد ديكور للسرير'},
                    {'name': 'مساند ظهر', 'slug': 'back-supports', 'description': 'مساند للظهر والرقبة'},
                    {'name': 'أقنعة النوم', 'slug': 'sleep-masks', 'description': 'أقنعة نوم مريحة'},
                    {'name': 'قواعد سرير', 'slug': 'bed-bases', 'description': 'قواعد سرير معدنية وخشبية'},
                ]
            },
        ]
        
        categories = {}
        for cat_data in categories_data:
            # إنشاء الفئة الرئيسية
            parent_cat = ProductCategory.objects.create(
                name=cat_data['name'],
                slug=cat_data['slug'],
                description=cat_data['description'],
                is_active=True,
            )
            categories[cat_data['slug']] = parent_cat
            self.stdout.write(f'  ✓ فئة رئيسية: {parent_cat.name}')
            
            # إنشاء الفئات الفرعية
            for child_data in cat_data.get('children', []):
                child_cat = ProductCategory.objects.create(
                    name=child_data['name'],
                    slug=child_data['slug'],
                    description=child_data['description'],
                    parent=parent_cat,
                    is_active=True,
                )
                categories[child_data['slug']] = child_cat
        
        # حذف المنتجات القديمة من المتجر
        OnlineProduct.objects.all().delete()
        
        # ربط منتجات المخزون الموجودة
        inventory_products = Product.objects.all()
        
        # تصنيف المنتجات تلقائياً حسب الاسم
        category_mapping = {
            'مرتبة': 'medical-mattresses',
            'وسادة': 'pillows',
            'لحاف': 'fiber-duvet',
            'بطانية': 'wool-blankets',
            'غطاء': 'mattress-protectors',
            'ملاية': 'cotton-sheets',
            'طقم': 'complete-bedding-sets',
            'إسفنج': 'memory-foam',
            'قماش': 'cotton-sheets',
            'خيوط': 'sleep-accessories',
            'سحاب': 'sleep-accessories',
            'أزرار': 'sleep-accessories',
        }
        
        for inv_product in inventory_products:
            # تحديد الفئة
            assigned_category = None
            product_name_lower = inv_product.name.lower()
            
            for keyword, cat_slug in category_mapping.items():
                if keyword in inv_product.name:
                    assigned_category = categories.get(cat_slug)
                    break
            
            if not assigned_category:
                assigned_category = categories.get('sleep-accessories')
            
            # إنشاء المنتج في المتجر
            try:
                online_product = OnlineProduct.objects.create(
                    inventory_item=inv_product,
                    display_name=inv_product.name,
                    short_description=f'{inv_product.name} - جودة عالية وضمان',
                    full_description=f'''
{inv_product.name}

✅ جودة عالية مضمونة
✅ ضمان سنة كاملة
✅ توصيل لجميع المحافظات
✅ إمكانية التقسيط

المواصفات:
- منتج أصلي 100%
- صناعة محلية فاخرة
- خامات عالية الجودة

للاستفسار: تواصل معنا عبر الواتساب
                    '''.strip(),
                    category=assigned_category,
                    is_active=True,
                    is_featured=inv_product.price > 1000,
                    is_new=True,
                )
                self.stdout.write(f'  ✓ منتج: {inv_product.name}')
            except Exception as e:
                self.stdout.write(f'  ⚠ تخطي منتج {inv_product.name}: {e}')
        
        # عرض الإحصائيات
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🛏️ تم إعداد متجر المراتب والمفروشات بنجاح!'))
        self.stdout.write(f'  - عدد الفئات الرئيسية: {ProductCategory.objects.filter(parent=None).count()}')
        self.stdout.write(f'  - عدد الفئات الفرعية: {ProductCategory.objects.filter(parent__isnull=False).count()}')
        self.stdout.write(f'  - عدد المنتجات: {OnlineProduct.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('زيارة المتجر: http://127.0.0.1:8000/ecommerce/')
