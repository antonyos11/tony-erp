from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.http import HttpResponse
from .models import UserRole, UserProfile, ModulePermission, ResourcePermission
from .permissions import require_module_perm, require_resource_perm


class PermissionDecoratorsTests(TestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.user = User.objects.create_user(username='u1', password='p1')
		role = UserRole.objects.create(name='r1', display_name='R1')
		profile, _ = UserProfile.objects.get_or_create(user=self.user)
		profile.role = role
		profile.is_approved = True
		profile.save()
		ModulePermission.objects.create(role=role, module='sales', action='view', is_allowed=True)
		ResourcePermission.objects.create(role=role, module='sales', resource='invoice_create', action='add', is_allowed=True)

	def test_require_module_perm_allows(self):
		@require_module_perm('sales', 'view')
		def v(request):
			return HttpResponse('OK')

		req = self.factory.get('/sales/'); req.user = self.user
		resp = v(req)
		self.assertEqual(resp.status_code, 200)

	def test_require_resource_perm_allows(self):
		@require_resource_perm('sales', 'invoice_create', 'add')
		def v(request):
			return HttpResponse('OK')

		req = self.factory.get('/sales/invoice/create/'); req.user = self.user
		resp = v(req)
		self.assertEqual(resp.status_code, 200)
