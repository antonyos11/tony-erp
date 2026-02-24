"""اختبارات تطبيق تصميم المراتب - Mattress Builder Tests"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class MattressSizeModelTest(TestCase):
    """اختبارات نموذج مقاسات المراتب"""

    def test_size_creation(self):
        """اختبار إنشاء مقاس مرتبة"""
        from mattress_builder.models import MattressSize
        size = MattressSize.objects.create(
            name='سينغل',
            width=90,
            length=190,
            base_price=Decimal('500.00'),
        )
        self.assertEqual(size.name, 'سينغل')
        # area property returns square meters (width * length / 10000)
        self.assertAlmostEqual(size.area, 90 * 190 / 10000, places=2)

    def test_size_display_dimensions(self):
        """اختبار عرض الأبعاد"""
        from mattress_builder.models import MattressSize
        size = MattressSize.objects.create(
            name='كوين',
            width=160,
            length=200,
            base_price=Decimal('900.00'),
        )
        display = size.display_dimensions
        self.assertIn('160', display)
        self.assertIn('200', display)


class MattressComponentModelTest(TestCase):
    """اختبارات نموذج مكونات المرتبة"""

    def test_component_category_creation(self):
        """اختبار إنشاء فئة مكون"""
        from mattress_builder.models import MattressComponentCategory
        category = MattressComponentCategory.objects.create(
            name='أقمشة',
        )
        self.assertIsNotNone(category.pk)

    def test_component_creation(self):
        """اختبار إنشاء مكون"""
        from mattress_builder.models import MattressComponent, MattressComponentCategory
        category = MattressComponentCategory.objects.create(name='إسفنج')
        component = MattressComponent.objects.create(
            name='إسفنج ميموري فوم',
            category=category,
            base_price=Decimal('200.00'),
        )
        self.assertEqual(component.name, 'إسفنج ميموري فوم')


class CustomMattressDesignModelTest(TestCase):
    """اختبارات نموذج التصميم المخصص"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='designer',
            password='testpass123',
        )

    def test_design_creation(self):
        """اختبار إنشاء تصميم مرتبة"""
        from mattress_builder.models import CustomMattressDesign, MattressSize
        size = MattressSize.objects.create(
            name='كينغ',
            width=180,
            length=200,
            base_price=Decimal('1200.00'),
        )
        design = CustomMattressDesign.objects.create(
            customer=self.user,
            mattress_size=size,
            design_name='تصميم مخصص 1',
        )
        self.assertIsNotNone(design.pk)
        self.assertEqual(design.customer, self.user)
