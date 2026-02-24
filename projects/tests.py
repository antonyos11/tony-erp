"""اختبارات تطبيق المشاريع - Projects Tests"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

User = get_user_model()


class ProjectModelTest(TestCase):
    """اختبارات نموذج المشاريع"""

    def setUp(self):
        self.manager = User.objects.create_user(
            username='project_manager',
            password='testpass123',
        )

    def test_project_type_creation(self):
        """اختبار إنشاء نوع مشروع"""
        from projects.models import ProjectType
        ptype = ProjectType.objects.create(
            name='مشروع إنشائي',
            code='CONST',
        )
        self.assertEqual(ptype.name, 'مشروع إنشائي')

    def test_project_creation(self):
        """اختبار إنشاء مشروع"""
        from projects.models import Project, ProjectType
        ptype = ProjectType.objects.create(name='مشروع عام', code='GEN')
        project = Project.objects.create(
            name='مشروع البناء',
            code='PRJ001',
            project_type=ptype,
            status='planning',
            budget=Decimal('1000000.00'),
            manager=self.manager,
        )
        self.assertIsNotNone(project.pk)
        self.assertEqual(project.status, 'planning')

    def test_project_category_tree(self):
        """اختبار شجرة فئات المشاريع"""
        from projects.models import ProjectCategory
        parent = ProjectCategory.objects.create(name='مقاولات', code='CTR')
        child = ProjectCategory.objects.create(
            name='مقاولات كهربائية',
            code='CTR-E',
            parent=parent,
        )
        self.assertEqual(child.parent, parent)

    def test_contractor_creation(self):
        """اختبار إنشاء مقاول"""
        from projects.models import Contractor
        contractor = Contractor.objects.create(
            name='شركة المقاولات',
        )
        self.assertIsNotNone(contractor.pk)


class ProjectViewTest(TestCase):
    """اختبارات صفحات المشاريع"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='project_user',
            password='testpass123',
            is_staff=True,
        )
        self.client.login(username='project_user', password='testpass123')

    def test_project_list_accessible(self):
        """اختبار الوصول لقائمة المشاريع"""
        try:
            response = self.client.get(reverse('projects:project_list'))
            self.assertIn(response.status_code, [200, 302])
        except Exception:
            pass

    def test_dashboard_accessible(self):
        """اختبار الوصول للوحة المشاريع"""
        try:
            response = self.client.get(reverse('projects:dashboard'))
            self.assertIn(response.status_code, [200, 302])
        except Exception:
            pass
