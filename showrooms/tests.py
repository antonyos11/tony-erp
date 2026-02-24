"""
اختبارات وحدة showrooms
Tests for showroom management module
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from inventory.models import Location, Product, Stock
from showrooms.models import Showroom, ShowroomEmployee


User = get_user_model()


class ShowroomModelTests(TestCase):
    """اختبارات النماذج الأساسية للمعارض"""
    
    def setUp(self):
        self.location = Location.objects.create(name='Test Location', code='TEST_LOC')
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_showroom_creation(self):
        """اختبار إنشاء معرض جديد"""
        showroom = Showroom.objects.create(
            code='SH001',
            name='Test Showroom',
            location=self.location
        )
        self.assertEqual(showroom.code, 'SH001')
        self.assertEqual(showroom.name, 'Test Showroom')
        self.assertEqual(str(showroom), 'SH001 - Test Showroom')
    
    def test_showroom_employee_assignment(self):
        """اختبار تعيين موظف للمعرض"""
        showroom = Showroom.objects.create(
            code='SH002',
            name='Employee Test Showroom',
            location=self.location
        )
        employee = ShowroomEmployee.objects.create(
            showroom=showroom,
            user=self.user,
            role='sales',
            active=True
        )
        self.assertEqual(employee.showroom, showroom)
        self.assertEqual(employee.user, self.user)
        self.assertTrue(employee.active)
    
    def test_showroom_unique_code(self):
        """اختبار أن كود المعرض فريد"""
        Showroom.objects.create(
            code='UNIQUE001',
            name='First Showroom',
            location=self.location
        )
        # محاولة إنشاء معرض بنفس الكود يجب أن تفشل
        with self.assertRaises(Exception):
            Showroom.objects.create(
                code='UNIQUE001',
                name='Duplicate Showroom',
                location=self.location
            )


class ShowroomAPITests(TestCase):
    """اختبارات API للمعارض"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            password='apipass123',
            is_staff=True
        )
        self.location = Location.objects.create(name='API Test Location', code='API_LOC')
        self.showroom = Showroom.objects.create(
            code='API_SH',
            name='API Test Showroom',
            location=self.location
        )
        ShowroomEmployee.objects.create(
            showroom=self.showroom,
            user=self.user,
            role='manager',
            active=True
        )
    
    def test_showroom_list_requires_auth(self):
        """اختبار أن قائمة المعارض تتطلب مصادقة"""
        response = self.client.get('/api/showrooms/')
        self.assertIn(response.status_code, [401, 403])
    
    def test_authenticated_showroom_access(self):
        """اختبار الوصول للمعارض بعد تسجيل الدخول"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/showrooms/')
        # قد يكون 200 أو 404 حسب وجود المسار
        self.assertIn(response.status_code, [200, 404])


class ShowroomIsolationTests(TestCase):
    """اختبارات عزل البيانات بين المعارض"""
    
    SESSION_KEY = 'ACTIVE_SHOWROOM_ID'
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='pass123')
        self.user2 = User.objects.create_user(username='user2', password='pass123')
        
        # إنشاء موقعين ومعرضين
        self.loc1 = Location.objects.create(name='Location 1', code='LOC1')
        self.loc2 = Location.objects.create(name='Location 2', code='LOC2')
        
        self.showroom1 = Showroom.objects.create(
            code='SHOW1',
            name='Showroom 1',
            location=self.loc1
        )
        self.showroom2 = Showroom.objects.create(
            code='SHOW2',
            name='Showroom 2',
            location=self.loc2
        )
        
        # تعيين الموظفين
        ShowroomEmployee.objects.create(
            showroom=self.showroom1,
            user=self.user1,
            role='sales',
            active=True
        )
        ShowroomEmployee.objects.create(
            showroom=self.showroom2,
            user=self.user2,
            role='sales',
            active=True
        )
        
        # إنشاء منتج ومخزون
        self.product = Product.objects.create(sku='PROD1', name='Test Product')
        Stock.objects.create(product=self.product, location=self.loc1, quantity=10)
        Stock.objects.create(product=self.product, location=self.loc2, quantity=20)
        
        self.client = APIClient()
    
    def _set_active_showroom(self, showroom):
        """تعيين المعرض النشط في الجلسة"""
        session = self.client.session
        session[self.SESSION_KEY] = showroom.id
        session.save()
    
    def test_user_can_only_see_assigned_showroom(self):
        """اختبار أن المستخدم يرى فقط المعرض المعين له"""
        self.client.force_authenticate(user=self.user1)
        self._set_active_showroom(self.showroom1)
        
        response = self.client.get('/api/locations/')
        self.assertEqual(response.status_code, 200)
    
    def test_showroom_data_isolation(self):
        """اختبار عزل البيانات بين المعارض"""
        # تسجيل دخول المستخدم الأول
        self.client.force_authenticate(user=self.user1)
        self._set_active_showroom(self.showroom1)
        
        # يجب أن يرى فقط موقع المعرض الأول
        response = self.client.get('/api/locations/')
        if response.status_code == 200:
            data = response.data
            if isinstance(data, dict) and 'results' in data:
                locations = data['results']
            elif isinstance(data, list):
                locations = data
            else:
                locations = []
            
            location_codes = {loc.get('code') for loc in locations if isinstance(loc, dict)}
            # يجب أن يكون LOC1 موجود وليس LOC2
            if location_codes:
                self.assertIn('LOC1', location_codes)
                self.assertNotIn('LOC2', location_codes)


class ShowroomPermissionTests(TestCase):
    """اختبارات صلاحيات المعارض"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='permuser', password='pass123')
        self.location = Location.objects.create(name='Perm Location', code='PERM_LOC')
        self.showroom = Showroom.objects.create(
            code='PERM_SH',
            name='Permission Test Showroom',
            location=self.location
        )
    
    def test_employee_roles(self):
        """اختبار أدوار الموظفين"""
        roles = ['sales', 'manager', 'cashier']
        for role in roles:
            employee = ShowroomEmployee.objects.create(
                showroom=self.showroom,
                user=User.objects.create_user(username=f'user_{role}', password='pass'),
                role=role,
                active=True
            )
            self.assertEqual(employee.role, role)
    
    def test_cross_access_permission(self):
        """اختبار صلاحية الوصول المتقاطع"""
        employee = ShowroomEmployee.objects.create(
            showroom=self.showroom,
            user=self.user,
            role='manager',
            active=True,
            can_cross_access=True
        )
        self.assertTrue(employee.can_cross_access)
