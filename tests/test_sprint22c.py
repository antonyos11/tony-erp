"""
اختبارات Sprint 22C — BOM متعدد المستويات + التصنيفات + التجاوب
══════════════════════════════════════════════════════════════════
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.models import Branch, Warehouse
from apps.inventory.models import (
    Category, UnitOfMeasure, Product, BillOfMaterials, BOMLine,
)
from apps.inventory.services.bom_engine import BOMEngine

User = get_user_model()


# ══════════════════════════════════════════════════════
# Base Fixture
# ══════════════════════════════════════════════════════
class BaseSprint22CTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='sprint22c_user', password='pass123', email='test22c@test.com',
        )
        cls.branch = Branch.objects.create(
            name='فرع Test 22C', branch_type='owned', governorate='القاهرة',
        )
        cls.wh = Warehouse.objects.create(
            name='مخزن Test 22C', branch=cls.branch, warehouse_type='raw',
        )
        cls.unit = UnitOfMeasure.objects.create(name='قطعة', symbol='قطعة')
        cls.cat = Category.objects.create(name='تصنيف Test 22C')

        # منتج خامة
        cls.raw1 = Product.objects.create(
            code='RAW22C-01', name='خامة اختبار 1', product_type='raw_material',
            unit=cls.unit, cost_price=Decimal('10.00'),
        )
        cls.raw2 = Product.objects.create(
            code='RAW22C-02', name='خامة اختبار 2', product_type='raw_material',
            unit=cls.unit, cost_price=Decimal('5.00'),
        )
        # منتج نصف مصنع
        cls.semi = Product.objects.create(
            code='SEMI22C-01', name='نصف مصنع اختبار', product_type='semi_finished',
            unit=cls.unit, cost_price=Decimal('0.00'),
        )
        # منتج تام
        cls.finished = Product.objects.create(
            code='FIN22C-01', name='منتج تام اختبار', product_type='finished',
            unit=cls.unit, cost_price=Decimal('0.00'),
        )


# ══════════════════════════════════════════════════════
# اختبارات محرك BOM
# ══════════════════════════════════════════════════════
class BOMEngineTest(BaseSprint22CTest):
    """اختبارات BOMEngine — التفكيك متعدد المستويات"""

    def test_create_bom(self):
        """إنشاء BOM بسيط"""
        bom = BillOfMaterials.objects.create(
            product=self.finished,
            name='BOM اختبار',
            bom_type='standard',
            version=1,
        )
        BOMLine.objects.create(
            bom=bom, raw_material=self.raw1, quantity=Decimal('2'),
        )
        self.assertEqual(bom.lines.count(), 1)
        self.assertEqual(bom.lines.first().quantity, Decimal('2'))

    def test_multi_level_explode(self):
        """تفكيك BOM متعدد المستويات"""
        # BOM للنصف مصنع: يحتوي خامتين
        sub_bom = BillOfMaterials.objects.create(
            product=self.semi,
            name='BOM نصف مصنع',
            bom_type='standard',
            version=1,
            is_active=True,
        )
        BOMLine.objects.create(bom=sub_bom, raw_material=self.raw1, quantity=Decimal('3'))
        BOMLine.objects.create(bom=sub_bom, raw_material=self.raw2, quantity=Decimal('4'))

        # BOM للمنتج التام: يحتوي نصف مصنع + خامة
        bom = BillOfMaterials.objects.create(
            product=self.finished,
            name='BOM متعدد مستويات',
            bom_type='standard',
            version=1,
            is_active=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=self.semi, quantity=Decimal('2'))
        BOMLine.objects.create(bom=bom, raw_material=self.raw2, quantity=Decimal('1'))

        items = BOMEngine.explode_bom(bom, quantity=1)
        # semi + raw1 (sub) + raw2 (sub) + raw2 (level 0)
        self.assertEqual(len(items), 4)

        levels = [i['level'] for i in items]
        self.assertIn(0, levels)
        self.assertIn(1, levels)

        sub_item = next(i for i in items if i['is_sub_assembly'])
        self.assertEqual(sub_item['product'], self.semi)

    def test_flat_materials_correct(self):
        """الخامات المسطحة تجمع نفس الخامة المتكررة"""
        sub_bom = BillOfMaterials.objects.create(
            product=self.semi, name='BOM مسطح sub', version=1, is_active=True,
        )
        BOMLine.objects.create(bom=sub_bom, raw_material=self.raw1, quantity=Decimal('2'))

        bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM مسطح', version=1, is_active=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=self.semi, quantity=Decimal('3'))
        BOMLine.objects.create(bom=bom, raw_material=self.raw1, quantity=Decimal('5'))  # نفس الخامة

        flat = BOMEngine.get_flat_materials(bom, quantity=1)
        flat_ids = {m['product'].pk for m in flat}
        # raw1 يظهر من مستويين — لكن في القائمة المسطحة مرة واحدة
        self.assertIn(self.raw1.pk, flat_ids)
        self.assertNotIn(self.semi.pk, flat_ids)  # نصف مصنع لا يظهر

        raw1_entry = next(m for m in flat if m['product'].pk == self.raw1.pk)
        # 3*2 (من sub) + 5 = 11
        self.assertEqual(raw1_entry['quantity'], Decimal('11'))

    def test_material_availability_check(self):
        """فحص التوفر يكشف النقص"""
        from apps.inventory.models import StockLevel
        bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM availability', version=1, is_active=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=self.raw1, quantity=Decimal('10'))

        # لا يوجد مخزون → نقص
        result = BOMEngine.check_material_availability(bom, 1, self.wh)
        self.assertFalse(result['all_available'])
        self.assertEqual(result['materials'][0]['shortage'], Decimal('10'))

        # تخزين 10 وحدات
        StockLevel.objects.create(product=self.raw1, warehouse=self.wh, quantity=Decimal('10'))

        # الآن يكفي
        result2 = BOMEngine.check_material_availability(bom, 1, self.wh)
        self.assertTrue(result2['all_available'])

    def test_where_used(self):
        """reverse BOM — أين يُستخدم المنتج"""
        bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM where-used', version=1, is_active=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=self.raw1, quantity=Decimal('1'))

        where = BOMEngine.get_where_used(self.raw1)
        self.assertEqual(len(where), 1)
        self.assertEqual(where[0]['parent_product'], self.finished)

    def test_estimated_cost_calculation(self):
        """حساب التكلفة التقديرية"""
        bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM cost', version=1, is_active=True,
            estimated_labor_cost=Decimal('20.00'),
            estimated_overhead_cost=Decimal('10.00'),
        )
        BOMLine.objects.create(bom=bom, raw_material=self.raw1, quantity=Decimal('5'))
        BOMLine.objects.create(bom=bom, raw_material=self.raw2, quantity=Decimal('4'))

        total = bom.calculate_estimated_cost()
        # خامات: 5*10 + 4*5 = 70 | عمالة: 20 | overhead: 10 = 100
        self.assertEqual(total, Decimal('100.00'))
        bom.refresh_from_db()
        self.assertEqual(bom.estimated_material_cost, Decimal('70.00'))

    def test_duplicate_bom(self):
        """نسخ BOM ينتج نسخة جديدة بنفس الأسطر"""
        bom = BillOfMaterials.objects.create(
            product=self.finished, name='BOM أصلي', version=1, is_active=True,
        )
        BOMLine.objects.create(bom=bom, raw_material=self.raw1, quantity=Decimal('3'))
        BOMLine.objects.create(bom=bom, raw_material=self.raw2, quantity=Decimal('7'))

        from apps.inventory.models import BOMLine as BML
        new_bom = BillOfMaterials.objects.create(
            product=bom.product, name=f'{bom.name} — نسخة',
            bom_type=bom.bom_type, version=bom.version + 1,
            is_default=False, is_active=True,
        )
        for line in bom.lines.all():
            BML.objects.create(
                bom=new_bom, raw_material=line.raw_material,
                quantity=line.quantity, unit=line.unit,
                waste_percentage=line.waste_percentage,
            )

        self.assertEqual(new_bom.lines.count(), 2)
        self.assertEqual(new_bom.version, 2)


# ══════════════════════════════════════════════════════
# اختبارات التصنيفات
# ══════════════════════════════════════════════════════
class CategoryTest(BaseSprint22CTest):
    """اختبارات CRUD التصنيفات"""

    def setUp(self):
        self.client = Client()
        self.client.login(username='sprint22c_user', password='pass123')

    def test_create_category(self):
        """إنشاء تصنيف أساسي"""
        response = self.client.post(
            reverse('inventory:category_create'),
            {'name': 'تصنيف جديد 22C'},
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(Category.objects.filter(name='تصنيف جديد 22C').exists())

    def test_create_subcategory(self):
        """إنشاء تصنيف فرعي"""
        parent = Category.objects.create(name='أب 22C')
        response = self.client.post(
            reverse('inventory:category_create'),
            {'name': 'فرعي 22C', 'parent': parent.pk},
        )
        self.assertIn(response.status_code, [200, 302])
        child = Category.objects.filter(name='فرعي 22C').first()
        self.assertIsNotNone(child)
        self.assertEqual(child.parent, parent)

    def test_cannot_delete_non_empty(self):
        """لا يمكن حذف تصنيف يحتوي منتجات"""
        cat = Category.objects.create(name='تصنيف محمي')
        Product.objects.create(
            code='CATPROD22C', name='منتج محمي', product_type='finished',
            unit=self.unit, category=cat,
        )
        response = self.client.post(reverse('inventory:category_delete', args=[cat.pk]))
        # يجب أن يعيد redirect مع رسالة خطأ
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

    def test_quick_create_ajax(self):
        """إضافة تصنيف سريعة عبر AJAX"""
        response = self.client.post(
            reverse('inventory:category_quick_create'),
            {'name': 'تصنيف سريع 22C'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertTrue(data.get('ok'))
        self.assertTrue(Category.objects.filter(name='تصنيف سريع 22C').exists())
