"""
سكريبت شامل لإنشاء جميع المواد الخام لمصنع المراتب والمفروشات
يشمل: التصنيفات الكاملة + جميع المواد الخام + وحدات القياس المناسبة

الاستخدام:
    python manage.py shell < setup_complete_mattress_materials.py
    أو
    python manage.py shell
    >>> exec(open('setup_complete_mattress_materials.py').read())
"""

from django.db import transaction
from django.db import models
from decimal import Decimal
from inventory.models import Category, Product

print("=" * 80)
print("🏭 بدء إعداد نظام المواد الخام لمصنع المراتب والمفروشات")
print("=" * 80)

# =============================================
# 1. إنشاء التصنيفات الهرمية الكاملة
# =============================================
def create_complete_categories():
    """إنشاء شجرة تصنيفات كاملة ومنظمة"""
    
    categories_tree = {
        'مواد خام': {
            'description': 'جميع المواد الخام للإنتاج',
            'children': {
                # الهيكل الداخلي
                'سوست ونوابض': {
                    'description': 'جميع أنواع السوست والنوابض',
                    'children': {
                        'سوست بونيل': {'description': 'سوست متصلة تقليدية'},
                        'سوست متصلة': {'description': 'سوست Continuous'},
                        'سوست منفصلة': {'description': 'سوست Pocket Spring'},
                        'أسلاك فولاذية': {'description': 'أسلاك بسماكات مختلفة'},
                    }
                },
                'إطارات': {
                    'description': 'إطارات معدنية وخشبية',
                    'children': {
                        'إطارات معدنية': {'description': 'إطارات حديد وصلب'},
                        'إطارات خشبية': {'description': 'إطارات خشب صلب'},
                    }
                },
                
                # مواد الحشو والراحة
                'إسفنج وفوم': {
                    'description': 'جميع أنواع الإسفنج والفوم',
                    'children': {
                        'فوم عادي': {'description': 'فوم بكثافات مختلفة'},
                        'فوم عالي الكثافة': {'description': 'فوم HD'},
                        'فوم ميموري': {'description': 'Memory Foam'},
                        'فوم لاتكس': {'description': 'لاتكس طبيعي وصناعي'},
                        'فوم جل': {'description': 'Gel Foam للتبريد'},
                    }
                },
                'حشوات': {
                    'description': 'مواد الحشو المختلفة',
                    'children': {
                        'لباد': {'description': 'Felt / Pad'},
                        'فيبر': {'description': 'فيبر بوليستر وسيليكون'},
                        'قطن': {'description': 'قطن طبي وعادي'},
                        'صوف': {'description': 'صوف طبيعي وصناعي'},
                        'ريش': {'description': 'ريش للمنتجات الفاخرة'},
                    }
                },
                
                # الأقمشة
                'أقمشة': {
                    'description': 'جميع أنواع الأقمشة',
                    'children': {
                        'أقمشة تنجيد': {'description': 'أقمشة المراتب الخارجية'},
                        'أقمشة مفروشات': {'description': 'أقمشة اللحف والمخدات'},
                        'أقمشة خاصة': {'description': 'أقمشة معالجة ومضادة'},
                    }
                },
                
                # مواد مساعدة
                'مستهلكات': {
                    'description': 'المواد المساعدة والمستهلكات',
                    'children': {
                        'خيوط': {'description': 'خيوط خياطة'},
                        'لواصق': {'description': 'غراء ولاصق'},
                        'إكسسوارات': {'description': 'سوست، سحابات، أزرار'},
                        'تغليف': {'description': 'مواد التعبئة والتغليف'},
                    }
                },
            }
        },
        
        'نصف مصنع': {
            'description': 'منتجات تحت التشغيل',
            'children': {
                'أغطية مخيطة': {'description': 'أغطية جاهزة للحشو'},
                'إطارات جاهزة': {'description': 'إطارات سوست جاهزة'},
                'حشوات جاهزة': {'description': 'حشوات مجهزة'},
            }
        },
        
        'منتج تام': {
            'description': 'المنتجات النهائية',
            'children': {
                'مراتب': {'description': 'جميع أنواع المراتب'},
                'وسائد ومخدات': {'description': 'وسائد ومخدات بأنواعها'},
                'مفروشات': {'description': 'لحف، ملايات، بطاطين'},
                'واقيات': {'description': 'واقيات مراتب'},
            }
        },
    }
    
    def create_category_recursive(name, data, parent=None, level=0):
        """إنشاء فئة وأطفالها بشكل تكراري"""
        indent = "  " * level
        
        obj, created = Category.objects.update_or_create(
            name=name,
            defaults={
                'description': data.get('description', ''),
                'parent': parent,
                'is_active': True,
                'sort_order': data.get('sort_order', 0),
            }
        )
        
        status = "✅ جديد" if created else "🔄 محدث"
        print(f"{indent}{status}: {name}")
        
        # إنشاء الفئات الفرعية
        if 'children' in data:
            for child_name, child_data in data['children'].items():
                create_category_recursive(child_name, child_data, obj, level + 1)
        
        return obj
    
    print("\n📁 إنشاء التصنيفات...")
    print("-" * 80)
    
    for root_name, root_data in categories_tree.items():
        create_category_recursive(root_name, root_data)
    
    total = Category.objects.count()
    print("-" * 80)
    print(f"✅ إجمالي التصنيفات: {total}")
    return Category.objects.all()


# تنفيذ إنشاء التصنيفات
with transaction.atomic():
    categories = create_complete_categories()

print("\n" + "=" * 80)
print("✅ تم إنشاء التصنيفات بنجاح!")
print("=" * 80)


# =============================================
# 2. إنشاء المواد الخام الكاملة
# =============================================
def create_raw_materials():
    """إنشاء جميع المواد الخام بالتفصيل"""

    print("\n🧱 إنشاء المواد الخام...")
    print("-" * 80)

    # قائمة شاملة بجميع المواد الخام
    raw_materials = [
        # ========================================
        # 1️⃣ الهيكل الداخلي - السوست والنوابض
        # ========================================

        # سوست بونيل
        {'sku': 'SPR-BNL-S90', 'name': 'سوست بونيل - قطر سلك 2.0 مم', 'category': 'سوست بونيل',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.20'), 'min_stock': 10000},
        {'sku': 'SPR-BNL-S100', 'name': 'سوست بونيل - قطر سلك 2.2 مم', 'category': 'سوست بونيل',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.50'), 'min_stock': 10000},
        {'sku': 'SPR-BNL-S120', 'name': 'سوست بونيل - قطر سلك 2.4 مم (Heavy Duty)', 'category': 'سوست بونيل',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.80'), 'min_stock': 8000},

        # سوست متصلة
        {'sku': 'SPR-CNT-001', 'name': 'سوست متصلة Continuous - قطر 1.8 مم', 'category': 'سوست متصلة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.00'), 'min_stock': 15000},
        {'sku': 'SPR-CNT-002', 'name': 'سوست متصلة Continuous - قطر 2.0 مم', 'category': 'سوست متصلة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.30'), 'min_stock': 12000},

        # سوست منفصلة (Pocket Spring)
        {'sku': 'SPR-PKT-S', 'name': 'سوست منفصلة Pocket - صغير (5 سم)', 'category': 'سوست منفصلة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('2.50'), 'min_stock': 8000},
        {'sku': 'SPR-PKT-M', 'name': 'سوست منفصلة Pocket - متوسط (7 سم)', 'category': 'سوست منفصلة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3.00'), 'min_stock': 6000},
        {'sku': 'SPR-PKT-L', 'name': 'سوست منفصلة Pocket - كبير (10 سم)', 'category': 'سوست منفصلة',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3.50'), 'min_stock': 5000},

        # أسلاك فولاذية
        {'sku': 'WIRE-1.5', 'name': 'سلك فولاذي قطر 1.5 مم', 'category': 'أسلاك فولاذية',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('18.00'), 'min_stock': 500},
        {'sku': 'WIRE-2.0', 'name': 'سلك فولاذي قطر 2.0 مم', 'category': 'أسلاك فولاذية',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('20.00'), 'min_stock': 800},
        {'sku': 'WIRE-2.5', 'name': 'سلك فولاذي قطر 2.5 مم', 'category': 'أسلاك فولاذية',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('22.00'), 'min_stock': 600},

        # إطارات معدنية
        {'sku': 'FRM-MTL-90', 'name': 'إطار معدني 90×190 سم', 'category': 'إطارات معدنية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('120.00'), 'min_stock': 50},
        {'sku': 'FRM-MTL-120', 'name': 'إطار معدني 120×200 سم', 'category': 'إطارات معدنية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('150.00'), 'min_stock': 80},
        {'sku': 'FRM-MTL-160', 'name': 'إطار معدني 160×200 سم', 'category': 'إطارات معدنية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('180.00'), 'min_stock': 60},
        {'sku': 'FRM-MTL-180', 'name': 'إطار معدني 180×200 سم', 'category': 'إطارات معدنية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('200.00'), 'min_stock': 40},

        # إطارات خشبية
        {'sku': 'FRM-WD-90', 'name': 'إطار خشبي 90×190 سم - خشب زان', 'category': 'إطارات خشبية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('250.00'), 'min_stock': 30},
        {'sku': 'FRM-WD-120', 'name': 'إطار خشبي 120×200 سم - خشب زان', 'category': 'إطارات خشبية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('320.00'), 'min_stock': 40},
        {'sku': 'FRM-WD-180', 'name': 'إطار خشبي 180×200 سم - خشب زان', 'category': 'إطارات خشبية',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('450.00'), 'min_stock': 20},

        # ========================================
        # 2️⃣ مواد الحشو والراحة - الإسفنج والفوم
        # ========================================

        # فوم عادي
        {'sku': 'FOAM-D18', 'name': 'فوم عادي كثافة 18', 'category': 'فوم عادي',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('28.00'), 'min_stock': 1500},
        {'sku': 'FOAM-D22', 'name': 'فوم عادي كثافة 22', 'category': 'فوم عادي',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('32.00'), 'min_stock': 2000},
        {'sku': 'FOAM-D25', 'name': 'فوم عادي كثافة 25', 'category': 'فوم عادي',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('35.00'), 'min_stock': 2500},

        # فوم عالي الكثافة
        {'sku': 'FOAM-HD30', 'name': 'فوم HD كثافة 30', 'category': 'فوم عالي الكثافة',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('45.00'), 'min_stock': 1500},
        {'sku': 'FOAM-HD35', 'name': 'فوم HD كثافة 35 (طبي)', 'category': 'فوم عالي الكثافة',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('60.00'), 'min_stock': 1000},
        {'sku': 'FOAM-HD40', 'name': 'فوم HD كثافة 40 (فاخر)', 'category': 'فوم عالي الكثافة',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('75.00'), 'min_stock': 800},

        # فوم ميموري
        {'sku': 'FOAM-MEM-50', 'name': 'ميموري فوم كثافة 50', 'category': 'فوم ميموري',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('120.00'), 'min_stock': 500},
        {'sku': 'FOAM-MEM-60', 'name': 'ميموري فوم كثافة 60 (Premium)', 'category': 'فوم ميموري',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('150.00'), 'min_stock': 300},
        {'sku': 'FOAM-MEM-GEL', 'name': 'ميموري فوم جل (تبريد)', 'category': 'فوم ميموري',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('180.00'), 'min_stock': 200},

        # فوم لاتكس
        {'sku': 'FOAM-LAT-NAT', 'name': 'لاتكس طبيعي 100%', 'category': 'فوم لاتكس',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('200.00'), 'min_stock': 300},
        {'sku': 'FOAM-LAT-SYN', 'name': 'لاتكس صناعي', 'category': 'فوم لاتكس',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('90.00'), 'min_stock': 500},
        {'sku': 'FOAM-LAT-MIX', 'name': 'لاتكس مخلوط (طبيعي + صناعي)', 'category': 'فوم لاتكس',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('140.00'), 'min_stock': 400},

        # فوم جل
        {'sku': 'FOAM-GEL-COOL', 'name': 'فوم جل تبريد', 'category': 'فوم جل',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('220.00'), 'min_stock': 200},
        {'sku': 'FOAM-GEL-INF', 'name': 'فوم جل منقوع (Gel-Infused)', 'category': 'فوم جل',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('250.00'), 'min_stock': 150},

        # ========================================
        # 3️⃣ الحشوات المختلفة
        # ========================================

        # لباد (Felt/Pad)
        {'sku': 'FELT-STD-5', 'name': 'لباد عادي سماكة 5 مم', 'category': 'لباد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('12.00'), 'min_stock': 1000},
        {'sku': 'FELT-STD-10', 'name': 'لباد عادي سماكة 10 مم', 'category': 'لباد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('18.00'), 'min_stock': 800},
        {'sku': 'FELT-COMP', 'name': 'لباد مضغوط (عالي الكثافة)', 'category': 'لباد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('25.00'), 'min_stock': 500},

        # فيبر
        {'sku': 'FIB-POL-STD', 'name': 'فيبر بوليستر عادي', 'category': 'فيبر',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('22.00'), 'min_stock': 2000},
        {'sku': 'FIB-SIL', 'name': 'فيبر سيليكون (ناعم)', 'category': 'فيبر',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('35.00'), 'min_stock': 1500},
        {'sku': 'FIB-HOL', 'name': 'فيبر هولوفيل (مجوف)', 'category': 'فيبر',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('40.00'), 'min_stock': 1000},

        # قطن
        {'sku': 'COT-MED', 'name': 'قطن طبي 100%', 'category': 'قطن',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('55.00'), 'min_stock': 800},
        {'sku': 'COT-STD', 'name': 'قطن عادي', 'category': 'قطن',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('35.00'), 'min_stock': 1200},
        {'sku': 'COT-ORG', 'name': 'قطن عضوي (Organic)', 'category': 'قطن',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('80.00'), 'min_stock': 400},

        # صوف
        {'sku': 'WOOL-NAT', 'name': 'صوف طبيعي 100%', 'category': 'صوف',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('120.00'), 'min_stock': 300},
        {'sku': 'WOOL-SYN', 'name': 'صوف صناعي', 'category': 'صوف',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('45.00'), 'min_stock': 600},

        # ريش
        {'sku': 'FEATH-DUCK', 'name': 'ريش بط (للمخدات الفاخرة)', 'category': 'ريش',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('180.00'), 'min_stock': 200},
        {'sku': 'FEATH-GOOSE', 'name': 'ريش إوز (Premium)', 'category': 'ريش',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('250.00'), 'min_stock': 100},

        # ========================================
        # 4️⃣ الأقمشة
        # ========================================

        # أقمشة تنجيد المراتب
        {'sku': 'FAB-JAC-WHT', 'name': 'قماش جاكار أبيض', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('45.00'), 'min_stock': 800},
        {'sku': 'FAB-JAC-PRT', 'name': 'قماش جاكار مطبوع', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('55.00'), 'min_stock': 600},
        {'sku': 'FAB-COT-100', 'name': 'قماش قطن 100%', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('35.00'), 'min_stock': 1000},
        {'sku': 'FAB-POL-STD', 'name': 'قماش بوليستر عادي', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('28.00'), 'min_stock': 1200},
        {'sku': 'FAB-BAM', 'name': 'قماش بامبو (صديق للبيئة)', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('65.00'), 'min_stock': 400},
        {'sku': 'FAB-MIX', 'name': 'قماش مخلوط (قطن + بوليستر)', 'category': 'أقمشة تنجيد',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('32.00'), 'min_stock': 900},

        # أقمشة مفروشات
        {'sku': 'FAB-SAT', 'name': 'قماش ساتان (للحف)', 'category': 'أقمشة مفروشات',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('38.00'), 'min_stock': 700},
        {'sku': 'FAB-MIC', 'name': 'قماش مايكروفايبر', 'category': 'أقمشة مفروشات',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('42.00'), 'min_stock': 600},
        {'sku': 'FAB-FLA', 'name': 'قماش فانيلا (للشتاء)', 'category': 'أقمشة مفروشات',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('35.00'), 'min_stock': 500},

        # أقمشة خاصة ومعالجة
        {'sku': 'FAB-ANTI-BAC', 'name': 'قماش مضاد للبكتيريا', 'category': 'أقمشة خاصة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('75.00'), 'min_stock': 300},
        {'sku': 'FAB-ANTI-ALL', 'name': 'قماش مضاد للحساسية', 'category': 'أقمشة خاصة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('70.00'), 'min_stock': 350},
        {'sku': 'FAB-WATER-RES', 'name': 'قماش مقاوم للماء', 'category': 'أقمشة خاصة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('55.00'), 'min_stock': 400},
        {'sku': 'FAB-COOL', 'name': 'قماش تبريد (Cooling Fabric)', 'category': 'أقمشة خاصة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('85.00'), 'min_stock': 250},
        {'sku': 'FAB-TENCEL', 'name': 'قماش تنسل (Tencel - فاخر)', 'category': 'أقمشة خاصة',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('95.00'), 'min_stock': 200},

        # ========================================
        # 5️⃣ المستهلكات والمواد المساعدة
        # ========================================

        # خيوط
        {'sku': 'THR-POL-WHT', 'name': 'خيط بوليستر أبيض', 'category': 'خيوط',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('5000'), 'cost': Decimal('45.00'), 'min_stock': 200},
        {'sku': 'THR-POL-BLK', 'name': 'خيط بوليستر أسود', 'category': 'خيوط',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('5000'), 'cost': Decimal('45.00'), 'min_stock': 150},
        {'sku': 'THR-COT', 'name': 'خيط قطني', 'category': 'خيوط',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('3000'), 'cost': Decimal('35.00'), 'min_stock': 100},
        {'sku': 'THR-HEAVY', 'name': 'خيط صناعي ثقيل (للسوست)', 'category': 'خيوط',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('2000'), 'cost': Decimal('60.00'), 'min_stock': 80},

        # لواصق وغراء
        {'sku': 'GLU-FOAM', 'name': 'غراء إسفنج (رش)', 'category': 'لواصق',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('80.00'), 'min_stock': 300},
        {'sku': 'GLU-FAB', 'name': 'غراء أقمشة', 'category': 'لواصق',
         'purchase_uom': 'kg', 'usage_uom': 'kg', 'cost': Decimal('65.00'), 'min_stock': 200},
        {'sku': 'TAPE-DBL', 'name': 'شريط لاصق وجهين', 'category': 'لواصق',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('50'), 'cost': Decimal('25.00'), 'min_stock': 150},

        # إكسسوارات
        {'sku': 'ZIP-40', 'name': 'سوستة (سحاب) 40 سم', 'category': 'إكسسوارات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3.50'), 'min_stock': 1000},
        {'sku': 'ZIP-60', 'name': 'سوستة (سحاب) 60 سم', 'category': 'إكسسوارات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('4.50'), 'min_stock': 800},
        {'sku': 'BTN-SNAP', 'name': 'أزرار كبس معدنية', 'category': 'إكسسوارات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('0.50'), 'min_stock': 5000},
        {'sku': 'ELAS-BAND', 'name': 'شريط مطاط (للملايات)', 'category': 'إكسسوارات',
         'purchase_uom': 'm', 'usage_uom': 'm', 'cost': Decimal('8.00'), 'min_stock': 500},
        {'sku': 'LABEL-CARE', 'name': 'بطاقة تعليمات العناية', 'category': 'إكسسوارات',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('0.80'), 'min_stock': 3000},

        # مواد التغليف
        {'sku': 'BAG-PVC-S', 'name': 'كيس بلاستيك PVC - صغير', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('2.50'), 'min_stock': 2000},
        {'sku': 'BAG-PVC-M', 'name': 'كيس بلاستيك PVC - متوسط', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('3.50'), 'min_stock': 1500},
        {'sku': 'BAG-PVC-L', 'name': 'كيس بلاستيك PVC - كبير', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('5.00'), 'min_stock': 1000},
        {'sku': 'BAG-VAC', 'name': 'كيس تفريغ هواء (Vacuum)', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('8.00'), 'min_stock': 800},
        {'sku': 'CARTON-S', 'name': 'كرتون تغليف - صغير', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('5.00'), 'min_stock': 500},
        {'sku': 'CARTON-M', 'name': 'كرتون تغليف - متوسط', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('8.00'), 'min_stock': 400},
        {'sku': 'CARTON-L', 'name': 'كرتون تغليف - كبير', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('12.00'), 'min_stock': 300},
        {'sku': 'TAPE-PACK', 'name': 'شريط تغليف شفاف', 'category': 'تغليف',
         'purchase_uom': 'roll', 'usage_uom': 'm', 'conversion_factor': Decimal('100'), 'cost': Decimal('15.00'), 'min_stock': 200},
        {'sku': 'LABEL-BRAND', 'name': 'ملصق العلامة التجارية', 'category': 'تغليف',
         'purchase_uom': 'unit', 'usage_uom': 'unit', 'cost': Decimal('1.20'), 'min_stock': 5000},
    ]

    created_count = 0
    updated_count = 0

    for material in raw_materials:
        # الحصول على الفئة
        category = Category.objects.filter(name=material['category']).first()

        # إنشاء أو تحديث المنتج
        try:
            obj, created = Product.objects.update_or_create(
                sku=material['sku'],
                defaults={
                    'name': material['name'],
                    'category': category,
                    'product_type': 'raw_material',
                    'purchase_uom': material['purchase_uom'],
                    'usage_uom': material['usage_uom'],
                    'conversion_factor': material.get('conversion_factor', Decimal('1')),
                    'cost': material['cost'],
                    'price': material['cost'] * Decimal('1.3'),  # هامش ربح افتراضي 30%
                    'min_stock': material['min_stock'],
                    'is_active': True,
                    'internal_code': f"INT{material['sku'][:10]}",  # استخدام 10 أحرف بدلاً من 8
                }
            )
        except Exception as e:
            print(f"  ⚠️  خطأ في {material['sku']}: {str(e)}")
            continue

        if created:
            created_count += 1
            print(f"  ✅ {material['sku']}: {material['name']}")
        else:
            updated_count += 1
            print(f"  🔄 {material['sku']}: {material['name']}")

    print("-" * 80)
    print(f"✅ تم إنشاء {created_count} مادة خام جديدة")
    print(f"🔄 تم تحديث {updated_count} مادة خام موجودة")
    print(f"📊 إجمالي المواد الخام: {Product.objects.filter(product_type='raw_material').count()}")

    return Product.objects.filter(product_type='raw_material')


# تنفيذ إنشاء المواد الخام
with transaction.atomic():
    raw_materials = create_raw_materials()

print("\n" + "=" * 80)
print("✅ تم إنشاء المواد الخام بنجاح!")
print("=" * 80)


# =============================================
# 3. عرض ملخص وإرشادات
# =============================================
def show_summary():
    """عرض ملخص شامل وإرشادات الاستخدام"""

    print("\n" + "=" * 80)
    print("📊 ملخص النظام")
    print("=" * 80)

    # إحصائيات التصنيفات
    total_categories = Category.objects.count()
    root_categories = Category.objects.filter(parent__isnull=True).count()

    print(f"\n📁 التصنيفات:")
    print(f"   • إجمالي التصنيفات: {total_categories}")
    print(f"   • التصنيفات الرئيسية: {root_categories}")

    # عرض شجرة التصنيفات
    print(f"\n🌳 شجرة التصنيفات:")
    for root in Category.objects.filter(parent__isnull=True):
        print(f"   📂 {root.name}")
        for child in root.children.all():
            print(f"      ├─ {child.name} ({child.children.count()} فئة فرعية)")

    # إحصائيات المواد الخام
    total_raw = Product.objects.filter(product_type='raw_material').count()

    print(f"\n🧱 المواد الخام:")
    print(f"   • إجمالي المواد الخام: {total_raw}")

    # تفصيل حسب الفئات الرئيسية
    main_categories = {
        'سوست ونوابض': 0,
        'إطارات': 0,
        'إسفنج وفوم': 0,
        'حشوات': 0,
        'أقمشة': 0,
        'مستهلكات': 0,
    }

    for cat_name in main_categories.keys():
        cat = Category.objects.filter(name=cat_name).first()
        if cat:
            # عد المنتجات في هذه الفئة وفئاتها الفرعية
            count = Product.objects.filter(
                product_type='raw_material',
                category__in=[cat] + list(cat.children.all())
            ).count()
            main_categories[cat_name] = count

    print(f"\n   📦 تفصيل حسب الفئات:")
    for cat_name, count in main_categories.items():
        print(f"      • {cat_name}: {count} مادة")

    # إحصائيات وحدات القياس
    print(f"\n📏 وحدات القياس المستخدمة:")
    uom_stats = Product.objects.filter(product_type='raw_material').values('purchase_uom').annotate(
        count=models.Count('id')
    ).order_by('-count')

    uom_names = {
        'unit': 'وحدة',
        'kg': 'كيلوجرام',
        'm': 'متر',
        'roll': 'لفة',
    }

    for stat in uom_stats:
        uom = stat['purchase_uom']
        count = stat['count']
        name = uom_names.get(uom, uom)
        print(f"      • {name}: {count} مادة")

    print("\n" + "=" * 80)
    print("📖 دليل الاستخدام السريع")
    print("=" * 80)

    print("""
1️⃣ إضافة مادة خام جديدة:
   • اذهب إلى: المخزون > المنتجات > إضافة منتج جديد
   • اختر نوع المنتج: "مادة خام"
   • اختر الفئة المناسبة من القائمة
   • حدد وحدة الشراء ووحدة الاستخدام
   • أدخل التكلفة والحد الأدنى للمخزون

2️⃣ إنشاء BOM (قائمة المواد) لمنتج:
   • اذهب إلى: الإنتاج > قوائم المواد > إضافة قائمة جديدة
   • اختر المنتج النهائي
   • أضف المواد الخام المطلوبة مع الكميات
   • حدد نسبة الهدر لكل مادة (اختياري)
   • احفظ القائمة

3️⃣ مثال على BOM لمرتبة:

   المنتج: مرتبة سوست 120×200 سم
   الكمية الأساسية: 1 وحدة

   المواد المطلوبة:
   ┌─────────────────────────────────────────────────────────┐
   │ المادة                    │ الكمية │ الوحدة │ الهدر %  │
   ├─────────────────────────────────────────────────────────┤
   │ إطار معدني 120×200        │ 1      │ وحدة   │ 0%      │
   │ سوست بونيل 2.2 مم         │ 450    │ وحدة   │ 2%      │
   │ فوم HD كثافة 30           │ 8      │ كجم    │ 5%      │
   │ لباد عادي 10 مم           │ 2.5    │ متر    │ 3%      │
   │ قماش جاكار مطبوع          │ 3      │ متر    │ 5%      │
   │ خيط بوليستر              │ 150    │ متر    │ 2%      │
   │ كيس PVC كبير              │ 1      │ وحدة   │ 0%      │
   └─────────────────────────────────────────────────────────┘

4️⃣ حساب التكلفة التلقائي:
   • النظام يحسب تكلفة المنتج تلقائياً من BOM
   • يأخذ في الاعتبار نسبة الهدر
   • يمكنك إضافة تكلفة العمالة والتشغيل

5️⃣ إدارة المخزون:
   • النظام يتتبع كميات المواد الخام
   • ينبهك عند الوصول للحد الأدنى
   • يحسب الكميات المطلوبة للإنتاج تلقائياً

6️⃣ تقارير مفيدة:
   • تقرير استهلاك المواد الخام
   • تقرير تكلفة الإنتاج
   • تقرير المواد الناقصة
   • تقرير الموردين والأسعار
""")

    print("=" * 80)
    print("✅ النظام جاهز للاستخدام!")
    print("=" * 80)

    print("""
💡 نصائح إضافية:

1. استخدم الباركود لتسريع عمليات الاستلام والصرف
2. حدّث أسعار المواد الخام بانتظام
3. راجع قوائم المواد (BOM) دورياً للتأكد من دقتها
4. استخدم نسبة الهدر بحكمة لتجنب النقص أو الزيادة
5. اربط كل مادة خام بالمورد المفضل لها

📞 للدعم الفني: تواصل مع فريق التطوير
""")


# عرض الملخص
show_summary()

print("\n" + "🎉" * 40)
print("تم إعداد نظام المواد الخام بنجاح!")
print("🎉" * 40 + "\n")

