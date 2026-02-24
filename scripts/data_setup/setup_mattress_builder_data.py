"""
إضافة بيانات تجريبية لنظام بناء المراتب المخصصة
Sample Data Setup for Mattress Builder System
"""
import os
import sys
import django

# Setup Django
sys.path.append('/var/www/tony_erp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
django.setup()

from decimal import Decimal
from mattress_builder.models import (
    MattressSize,
    MattressComponentCategory,
    MattressComponent,
    MattressRecommendationRule,
    MattressTemplate,
    BuilderSettings
)


def create_sizes():
    """إنشاء أحجام المراتب"""
    sizes = [
        {
            'name': 'مفرد',
            'name_en': 'Single',
            'width': Decimal('90'),
            'length': Decimal('190'),
            'base_price': Decimal('800'),
            'price_multiplier': Decimal('1.0'),
            'icon': 'fa-user',
            'sort_order': 1
        },
        {
            'name': 'نفر ونص',
            'name_en': 'Twin',
            'width': Decimal('120'),
            'length': Decimal('190'),
            'base_price': Decimal('1000'),
            'price_multiplier': Decimal('1.2'),
            'icon': 'fa-users',
            'sort_order': 2
        },
        {
            'name': 'مزدوج',
            'name_en': 'Double',
            'width': Decimal('140'),
            'length': Decimal('190'),
            'base_price': Decimal('1200'),
            'price_multiplier': Decimal('1.4'),
            'icon': 'fa-bed',
            'sort_order': 3
        },
        {
            'name': 'كوين',
            'name_en': 'Queen',
            'width': Decimal('160'),
            'length': Decimal('200'),
            'base_price': Decimal('1500'),
            'price_multiplier': Decimal('1.6'),
            'icon': 'fa-bed',
            'sort_order': 4
        },
        {
            'name': 'كينج',
            'name_en': 'King',
            'width': Decimal('180'),
            'length': Decimal('200'),
            'base_price': Decimal('1800'),
            'price_multiplier': Decimal('1.8'),
            'icon': 'fa-crown',
            'sort_order': 5
        },
        {
            'name': 'سوبر كينج',
            'name_en': 'Super King',
            'width': Decimal('200'),
            'length': Decimal('200'),
            'base_price': Decimal('2200'),
            'price_multiplier': Decimal('2.0'),
            'icon': 'fa-crown',
            'sort_order': 6
        },
    ]
    
    for size_data in sizes:
        size, created = MattressSize.objects.get_or_create(
            name=size_data['name'],
            defaults=size_data
        )
        if created:
            print(f"✅ تم إنشاء حجم: {size.name}")
        else:
            print(f"ℹ️  الحجم موجود بالفعل: {size.name}")


def create_categories():
    """إنشاء فئات المكونات"""
    categories = [
        {
            'name': 'السوست',
            'name_en': 'Springs',
            'category_type': 'springs',
            'description': 'أنظمة السوست للدعم',
            'icon': 'fa-arrows-alt-v',
            'color': '#3b82f6',
            'layer_order': 2,
            'is_required': True,
            'max_selections': 1,
            'sort_order': 1
        },
        {
            'name': 'الإسفنج',
            'name_en': 'Foam',
            'category_type': 'foam',
            'description': 'طبقات الإسفنج المريحة',
            'icon': 'fa-layer-group',
            'color': '#10b981',
            'layer_order': 3,
            'is_required': True,
            'max_selections': 3,
            'sort_order': 2
        },
        {
            'name': 'القماش الخارجي',
            'name_en': 'Fabric',
            'category_type': 'fabric',
            'description': 'القماش والتشطيب الخارجي',
            'icon': 'fa-tshirt',
            'color': '#f59e0b',
            'layer_order': 5,
            'is_required': True,
            'max_selections': 1,
            'sort_order': 3
        },
        {
            'name': 'طبقات الراحة',
            'name_en': 'Comfort Layers',
            'category_type': 'comfort',
            'description': 'طبقات إضافية للراحة',
            'icon': 'fa-couch',
            'color': '#8b5cf6',
            'layer_order': 4,
            'is_required': False,
            'max_selections': 2,
            'sort_order': 4
        },
        {
            'name': 'أنظمة التبريد',
            'name_en': 'Cooling',
            'category_type': 'cooling',
            'description': 'تقنيات التبريد والتهوية',
            'icon': 'fa-snowflake',
            'color': '#06b6d4',
            'layer_order': 4,
            'is_required': False,
            'max_selections': 1,
            'sort_order': 5
        },
        {
            'name': 'القاعدة',
            'name_en': 'Base',
            'category_type': 'base',
            'description': 'قاعدة المرتبة',
            'icon': 'fa-align-justify',
            'color': '#6b7280',
            'layer_order': 1,
            'is_required': True,
            'max_selections': 1,
            'sort_order': 6
        },
    ]
    
    created_categories = {}
    for cat_data in categories:
        category, created = MattressComponentCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        created_categories[cat_data['category_type']] = category
        if created:
            print(f"✅ تم إنشاء فئة: {category.name}")
        else:
            print(f"ℹ️  الفئة موجودة بالفعل: {category.name}")
    
    return created_categories


def create_components(categories):
    """إنشاء المكونات"""
    
    # مكونات السوست
    springs = [
        {
            'name': 'سوست جيوب منفصلة - فاخر',
            'name_en': 'Pocket Spring Luxury',
            'description': 'سوست جيوب منفصلة للراحة القصوى',
            'short_description': '1200 سوست منفصل',
            'base_price': Decimal('600'),
            'price_per_sqm': Decimal('0'),
            'pricing_type': 'fixed',
            'quality_level': 'luxury',
            'thickness': Decimal('18'),
            'specifications': {'count': 1200, 'wire_gauge': '2.0mm'},
            'benefits': ['دعم متميز', 'تقليل نقل الحركة', 'عمر أطول'],
            'is_featured': True,
            'is_popular': True,
            'sort_order': 1
        },
        {
            'name': 'سوست متصلة - قياسي',
            'name_en': 'Bonnell Spring Standard',
            'description': 'سوست متصلة تقليدية',
            'short_description': 'سوست متصلة متينة',
            'base_price': Decimal('300'),
            'price_per_sqm': Decimal('0'),
            'pricing_type': 'fixed',
            'quality_level': 'standard',
            'thickness': Decimal('15'),
            'specifications': {'count': 600, 'wire_gauge': '2.4mm'},
            'benefits': ['اقتصادي', 'متين', 'دعم جيد'],
            'is_featured': False,
            'is_popular': True,
            'sort_order': 2
        },
    ]
    
    # مكونات الإسفنج
    foam = [
        {
            'name': 'ميموري فوم - كثافة عالية',
            'name_en': 'Memory Foam High Density',
            'description': 'إسفنج ميموري فوم يتكيف مع شكل الجسم',
            'short_description': 'راحة فائقة',
            'base_price': Decimal('0'),
            'price_per_sqm': Decimal('400'),
            'pricing_type': 'per_sqm',
            'quality_level': 'luxury',
            'thickness': Decimal('5'),
            'density': Decimal('60'),
            'specifications': {'type': 'visco-elastic', 'recovery_time': '5s'},
            'benefits': ['راحة استثنائية', 'تخفيف نقاط الضغط', 'دعم للعمود الفقري'],
            'texture_pattern': 'dots',
            'is_featured': True,
            'is_popular': True,
            'sort_order': 1
        },
        {
            'name': 'إسفنج عالي المرونة',
            'name_en': 'High Resilience Foam',
            'description': 'إسفنج عالي المرونة والتحمل',
            'short_description': 'مرونة عالية',
            'base_price': Decimal('0'),
            'price_per_sqm': Decimal('250'),
            'pricing_type': 'per_sqm',
            'quality_level': 'premium',
            'thickness': Decimal('4'),
            'density': Decimal('40'),
            'specifications': {'type': 'HR foam', 'firmness': 'medium'},
            'benefits': ['مرونة ممتازة', 'تهوية جيدة', 'عمر طويل'],
            'texture_pattern': 'waves',
            'is_featured': True,
            'sort_order': 2
        },
        {
            'name': 'إسفنج قياسي',
            'name_en': 'Standard Foam',
            'description': 'إسفنج بولي يوريثان قياسي',
            'short_description': 'اقتصادي ومريح',
            'base_price': Decimal('0'),
            'price_per_sqm': Decimal('150'),
            'pricing_type': 'per_sqm',
            'quality_level': 'standard',
            'thickness': Decimal('3'),
            'density': Decimal('28'),
            'specifications': {'type': 'PU foam', 'firmness': 'medium-firm'},
            'benefits': ['سعر مناسب', 'مريح', 'خفيف الوزن'],
            'texture_pattern': 'lines',
            'is_popular': True,
            'sort_order': 3
        },
    ]
    
    # مكونات القماش
    fabric = [
        {
            'name': 'قماش مضاد للبكتيريا',
            'name_en': 'Antibacterial Fabric',
            'description': 'قماش معالج ضد البكتيريا والروائح',
            'short_description': 'صحي ونظيف',
            'base_price': Decimal('200'),
            'pricing_type': 'fixed',
            'quality_level': 'premium',
            'specifications': {'treatment': 'silver ion', 'breathable': True},
            'benefits': ['مضاد للبكتيريا', 'قابل للغسل', 'تهوية ممتازة'],
            'is_featured': True,
            'sort_order': 1
        },
        {
            'name': 'قماش قطني فاخر',
            'name_en': 'Luxury Cotton Fabric',
            'description': 'قماش قطني 100% فاخر',
            'short_description': 'قطن طبيعي',
            'base_price': Decimal('150'),
            'pricing_type': 'fixed',
            'quality_level': 'luxury',
            'specifications': {'material': '100% cotton', 'thread_count': 400},
            'benefits': ['طبيعي 100%', 'ملمس ناعم', 'قابل للتنفس'],
            'is_featured': True,
            'is_popular': True,
            'sort_order': 2
        },
    ]
    
    # مكونات التبريد
    cooling = [
        {
            'name': 'جل التبريد',
            'name_en': 'Cooling Gel',
            'description': 'طبقة جل للتبريد',
            'short_description': 'نوم بارد ومريح',
            'base_price': Decimal('300'),
            'pricing_type': 'fixed',
            'quality_level': 'premium',
            'thickness': Decimal('1'),
            'specifications': {'type': 'phase-change gel', 'cooling_effect': 'high'},
            'benefits': ['تبريد فعال', 'راحة في الصيف', 'تقنية متقدمة'],
            'is_featured': True,
            'sort_order': 1
        },
    ]
    
    # مكونات القاعدة
    base = [
        {
            'name': 'قاعدة إسفنج مضغوط',
            'name_en': 'Compressed Foam Base',
            'description': 'قاعدة من الإسفنج المضغوط',
            'short_description': 'قاعدة متينة',
            'base_price': Decimal('250'),
            'pricing_type': 'fixed',
            'quality_level': 'standard',
            'thickness': Decimal('10'),
            'density': Decimal('35'),
            'specifications': {'type': 'compressed PU', 'support': 'firm'},
            'benefits': ['دعم قوي', 'متين', 'مستقر'],
            'is_popular': True,
            'sort_order': 1
        },
    ]
    
    all_components = [
        (categories['springs'], springs),
        (categories['foam'], foam),
        (categories['fabric'], fabric),
        (categories['cooling'], cooling),
        (categories['base'], base),
    ]
    
    for category, components_list in all_components:
        for comp_data in components_list:
            comp_data['category'] = category
            component, created = MattressComponent.objects.get_or_create(
                name=comp_data['name'],
                defaults=comp_data
            )
            if created:
                print(f"✅ تم إنشاء مكون: {component.name}")
            else:
                print(f"ℹ️  المكون موجود بالفعل: {component.name}")


def create_settings():
    """إنشاء إعدادات النظام"""
    settings, created = BuilderSettings.objects.get_or_create(
        pk=1,
        defaults={
            'profit_margin_percent': Decimal('25'),
            'auto_approval_threshold': Decimal('5000'),
            'enable_auto_approval': False,
            'estimated_production_days': 7,
            'max_designs_per_customer': 10,
            'enable_recommendations': True,
            'enable_gamification': True,
            'welcome_message': 'صمم مرتبتك الخاصة خطوة بخطوة! 🛏️'
        }
    )
    
    if created:
        print("✅ تم إنشاء إعدادات النظام")
    else:
        print("ℹ️  إعدادات النظام موجودة بالفعل")


def main():
    """تنفيذ جميع الخطوات"""
    print("=" * 60)
    print("🚀 بدء إضافة البيانات التجريبية لنظام بناء المراتب")
    print("=" * 60)
    
    print("\n📏 إنشاء أحجام المراتب...")
    create_sizes()
    
    print("\n📦 إنشاء فئات المكونات...")
    categories = create_categories()
    
    print("\n🧩 إنشاء المكونات...")
    create_components(categories)
    
    print("\n⚙️  إنشاء إعدادات النظام...")
    create_settings()
    
    print("\n" + "=" * 60)
    print("✅ تم الانتهاء من إضافة البيانات التجريبية بنجاح!")
    print("=" * 60)
    print("\n📋 الخطوات التالية:")
    print("1. تسجيل الدخول للوحة التحكم: /admin/")
    print("2. زيارة صفحة البناء: /mattress-builder/builder/")
    print("3. عرض تصميماتك: /mattress-builder/my-designs/")
    print("\n🎨 استمتع ببناء المراتب المخصصة!")
    print("=" * 60)


if __name__ == '__main__':
    main()
