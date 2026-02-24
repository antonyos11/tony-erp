#!/usr/bin/env python3
"""
سكربت لإنشاء مخازن تجريبية للاختبار
يمكن تشغيله من shell Django
"""

from inventory.models import Location

def create_sample_warehouses():
    """إنشاء مخازن تجريبية من جميع الأنواع"""
    
    warehouses = [
        # مخازن المنتجات التامة
        {
            'code': 'FINISHED-01',
            'name': 'مخزن المنتجات الجاهزة - الرئيسي',
            'type': 'finished',
            'address': 'المبنى الرئيسي - الطابق الثاني',
            'is_default': True,
        },
        {
            'code': 'FINISHED-02',
            'name': 'مخزن المنتجات الجاهزة - الفرعي',
            'type': 'finished',
            'address': 'المبنى الفرعي - الطابق الأول',
        },
        
        # مخازن نصف المصنعة
        {
            'code': 'WIP-LINE1',
            'name': 'خط الإنتاج 1 - قيد التصنيع',
            'type': 'wip',
            'address': 'ورشة التصنيع - القسم أ',
        },
        {
            'code': 'WIP-LINE2',
            'name': 'خط الإنتاج 2 - قيد التصنيع',
            'type': 'wip',
            'address': 'ورشة التصنيع - القسم ب',
        },
        
        # مخازن الخامات
        {
            'code': 'RAW-MAIN',
            'name': 'مخزن المواد الخام الرئيسي',
            'type': 'raw',
            'address': 'المستودع الرئيسي - الطابق الأرضي',
        },
        {
            'code': 'RAW-METALS',
            'name': 'مخزن المعادن والخامات الثقيلة',
            'type': 'raw',
            'address': 'المستودع الخارجي',
        },
        {
            'code': 'RAW-CHEMICALS',
            'name': 'مخزن المواد الكيميائية',
            'type': 'raw',
            'address': 'مستودع المواد الخطرة',
        },
        
        # مخازن قطع الغيار
        {
            'code': 'SPARE-MAINT',
            'name': 'مخزن الصيانة وقطع الغيار',
            'type': 'spare',
            'address': 'مكتب الصيانة - الطابق الأول',
        },
        
        # مخازن المعارض
        {
            'code': 'STORE-MAIN',
            'name': 'معرض البيع الرئيسي',
            'type': 'store',
            'address': 'شارع الملك فهد',
        },
        {
            'code': 'STORE-BRANCH1',
            'name': 'معرض الفرع الأول',
            'type': 'store',
            'address': 'حي النسيم',
        },
        {
            'code': 'STORE-BRANCH2',
            'name': 'معرض الفرع الثاني',
            'type': 'store',
            'address': 'حي الروضة',
        },
        
        # مخازن أخرى
        {
            'code': 'OTHER-ARCHIVE',
            'name': 'مخزن الأرشيف',
            'type': 'other',
            'address': 'الطابق السفلي',
        },
        {
            'code': 'OTHER-RETURNS',
            'name': 'مخزن المرتجعات',
            'type': 'other',
            'address': 'القسم الخلفي',
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for warehouse_data in warehouses:
        # التحقق من عدم وجود المخزن مسبقاً
        if Location.objects.filter(code=warehouse_data['code']).exists():
            print(f"⏭️  المخزن {warehouse_data['code']} موجود مسبقاً - تم التخطي")
            skipped_count += 1
            continue
        
        # إنشاء المخزن
        try:
            location = Location.objects.create(**warehouse_data)
            print(f"✅ تم إنشاء المخزن: {location.code} - {location.name}")
            created_count += 1
        except Exception as e:
            print(f"❌ خطأ في إنشاء المخزن {warehouse_data['code']}: {e}")
    
    print("\n" + "="*50)
    print(f"📊 الإحصائيات:")
    print(f"   - تم إنشاء: {created_count} مخزن")
    print(f"   - تم التخطي: {skipped_count} مخزن")
    print(f"   - الإجمالي: {Location.objects.count()} مخزن في النظام")
    print("="*50)
    
    # عرض الإحصائيات حسب النوع
    print("\n📈 المخازن حسب النوع:")
    types = [
        ('finished', 'منتج تام', '🏭'),
        ('wip', 'نصف مصنع', '⚙️'),
        ('raw', 'خامات', '💧'),
        ('spare', 'قطع غيار', '🔧'),
        ('store', 'معرض/متجر', '🏪'),
        ('other', 'أخرى', '📦'),
    ]
    
    for type_code, type_name, icon in types:
        count = Location.objects.filter(type=type_code, is_active=True).count()
        print(f"   {icon} {type_name}: {count} مخزن")
    
    return created_count


if __name__ == '__main__':
    print("="*50)
    print("🚀 إنشاء مخازن تجريبية للاختبار")
    print("="*50 + "\n")
    
    created = create_sample_warehouses()
    
    print("\n✨ تم الانتهاء بنجاح!")
    print(f"يمكنك الآن مشاهدة المخازن على:")
    print("  http://your-domain/inventory/locations/types/")
    print("  http://your-domain/inventory/locations/")
