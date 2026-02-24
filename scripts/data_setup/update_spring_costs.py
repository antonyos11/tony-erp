"""
تحديث أسعار السلك الحديد والسوست

استخدم هذا السكريبت لتحديث الأسعار الحقيقية حسب السوق

الاستخدام:
    1. عدّل الأسعار في هذا الملف
    2. شغل: python manage.py shell < update_spring_costs.py
"""

from django.db import transaction
from decimal import Decimal
from inventory.models import Product
from production.models import BillOfMaterials, BOMItem

print("=" * 80)
print("💰 تحديث أسعار السلك الحديد والسوست")
print("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════
# 🔧 عدّل الأسعار هنا حسب السوق الحقيقي
# ═══════════════════════════════════════════════════════════════════════════

# 1️⃣ أسعار السلك الحديد (ج/كجم)
WIRE_PRICES = {
    'WIRE-1.5': Decimal('18.00'),  # عدّل السعر هنا
    'WIRE-1.8': Decimal('19.00'),  # عدّل السعر هنا
    'WIRE-2.0': Decimal('20.00'),  # عدّل السعر هنا ← الأكثر استخداماً
    'WIRE-2.2': Decimal('21.00'),  # عدّل السعر هنا
    'WIRE-2.4': Decimal('22.00'),  # عدّل السعر هنا
    'WIRE-2.5': Decimal('22.50'),  # عدّل السعر هنا
    'WIRE-3.0': Decimal('24.00'),  # عدّل السعر هنا
}

# 2️⃣ أوزان السلك في كل سوست (كجم)
SPRING_WIRE_WEIGHTS = {
    'SPR-BNL-S90': Decimal('0.015'),   # عدّل الوزن هنا (اوزن السوست الفعلية!)
    'SPR-BNL-S100': Decimal('0.018'),  # عدّل الوزن هنا
    'SPR-BNL-S120': Decimal('0.022'),  # عدّل الوزن هنا
    'SPR-CNT-001': Decimal('0.012'),   # عدّل الوزن هنا
    'SPR-CNT-002': Decimal('0.015'),   # عدّل الوزن هنا
    'SPR-PKT-S': Decimal('0.020'),     # عدّل الوزن هنا
    'SPR-PKT-M': Decimal('0.025'),     # عدّل الوزن هنا
    'SPR-PKT-L': Decimal('0.030'),     # عدّل الوزن هنا
}

# 3️⃣ تكلفة العمالة لكل سوست (ج/وحدة)
LABOR_COSTS = {
    'SPR-BNL-S90': Decimal('0.30'),   # عدّل التكلفة هنا
    'SPR-BNL-S100': Decimal('0.35'),  # عدّل التكلفة هنا
    'SPR-BNL-S120': Decimal('0.40'),  # عدّل التكلفة هنا
    'SPR-CNT-001': Decimal('0.25'),   # عدّل التكلفة هنا
    'SPR-CNT-002': Decimal('0.30'),   # عدّل التكلفة هنا
    'SPR-PKT-S': Decimal('0.60'),     # عدّل التكلفة هنا
    'SPR-PKT-M': Decimal('0.70'),     # عدّل التكلفة هنا
    'SPR-PKT-L': Decimal('0.80'),     # عدّل التكلفة هنا
}

# 4️⃣ تكلفة القماش للسوست المنفصلة (ج/وحدة)
FABRIC_COSTS = {
    'SPR-PKT-S': Decimal('0.50'),  # عدّل التكلفة هنا
    'SPR-PKT-M': Decimal('0.60'),  # عدّل التكلفة هنا
    'SPR-PKT-L': Decimal('0.70'),  # عدّل التكلفة هنا
}

# ═══════════════════════════════════════════════════════════════════════════
# لا تعدل شيء تحت هذا الخط
# ═══════════════════════════════════════════════════════════════════════════


def update_wire_prices():
    """تحديث أسعار السلك الحديد"""
    print("\n🔩 تحديث أسعار السلك الحديد...")
    print("-" * 80)
    
    for sku, price in WIRE_PRICES.items():
        try:
            wire = Product.objects.get(sku=sku)
            old_price = wire.cost
            wire.cost = price
            wire.price = price * Decimal('1.2')  # سعر البيع = التكلفة + 20%
            wire.save()
            
            change = ((price - old_price) / old_price * 100) if old_price > 0 else 0
            print(f"   ✅ {wire.name}")
            print(f"      السعر القديم: {old_price:.2f} ج/كجم")
            print(f"      السعر الجديد: {price:.2f} ج/كجم")
            if change != 0:
                print(f"      التغيير: {change:+.1f}%")
        except Product.DoesNotExist:
            print(f"   ⚠️  {sku} غير موجود!")


def update_spring_costs():
    """تحديث تكلفة السوست"""
    print("\n⚙️ تحديث تكلفة السوست...")
    print("-" * 80)
    
    # ربط كل سوست بالسلك المستخدم
    spring_wire_map = {
        'SPR-BNL-S90': 'WIRE-2.0',
        'SPR-BNL-S100': 'WIRE-2.2',
        'SPR-BNL-S120': 'WIRE-2.4',
        'SPR-CNT-001': 'WIRE-1.8',
        'SPR-CNT-002': 'WIRE-2.0',
        'SPR-PKT-S': 'WIRE-1.8',
        'SPR-PKT-M': 'WIRE-2.0',
        'SPR-PKT-L': 'WIRE-2.2',
    }
    
    for spring_sku, wire_sku in spring_wire_map.items():
        try:
            spring = Product.objects.get(sku=spring_sku)
            wire = Product.objects.get(sku=wire_sku)
            
            # حساب التكلفة
            wire_weight = SPRING_WIRE_WEIGHTS.get(spring_sku, Decimal('0'))
            wire_cost = wire_weight * wire.cost
            labor_cost = LABOR_COSTS.get(spring_sku, Decimal('0'))
            fabric_cost = FABRIC_COSTS.get(spring_sku, Decimal('0'))
            
            total_cost = wire_cost + labor_cost + fabric_cost
            old_cost = spring.cost
            
            spring.cost = total_cost
            spring.price = total_cost * Decimal('1.3')  # سعر البيع = التكلفة + 30%
            spring.save()
            
            print(f"   ✅ {spring.name}")
            print(f"      التكلفة القديمة: {old_cost:.2f} ج")
            print(f"      التكلفة الجديدة: {total_cost:.2f} ج")
            print(f"         ├─ السلك ({wire_weight} كجم × {wire.cost} ج): {wire_cost:.2f} ج")
            print(f"         ├─ العمالة: {labor_cost:.2f} ج")
            if fabric_cost > 0:
                print(f"         └─ القماش: {fabric_cost:.2f} ج")
            
        except Product.DoesNotExist as e:
            print(f"   ⚠️  {spring_sku} أو {wire_sku} غير موجود!")


def show_summary():
    """عرض ملخص الأسعار"""
    print("\n" + "=" * 80)
    print("📊 ملخص الأسعار الحالية")
    print("=" * 80)
    
    print("\n🔩 السلك الحديد:")
    for sku in WIRE_PRICES.keys():
        try:
            wire = Product.objects.get(sku=sku)
            print(f"   {wire.name}: {wire.cost:.2f} ج/كجم")
        except:
            pass
    
    print("\n⚙️ السوست:")
    spring_wire_map = {
        'SPR-BNL-S90': 'WIRE-2.0',
        'SPR-BNL-S100': 'WIRE-2.2',
        'SPR-BNL-S120': 'WIRE-2.4',
        'SPR-CNT-001': 'WIRE-1.8',
        'SPR-CNT-002': 'WIRE-2.0',
        'SPR-PKT-S': 'WIRE-1.8',
        'SPR-PKT-M': 'WIRE-2.0',
        'SPR-PKT-L': 'WIRE-2.2',
    }
    
    for spring_sku in spring_wire_map.keys():
        try:
            spring = Product.objects.get(sku=spring_sku)
            print(f"   {spring.name}: {spring.cost:.2f} ج/وحدة")
        except:
            pass


# تنفيذ
with transaction.atomic():
    update_wire_prices()
    update_spring_costs()
    show_summary()

print("\n" + "=" * 80)
print("✅ تم تحديث الأسعار بنجاح!")
print("=" * 80)
print("\n💡 نصيحة: راجع الأسعار في النظام وتأكد من صحتها")
print("   افتح: http://72.62.176.249/inventory/products/")

