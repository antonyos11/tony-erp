from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from inventory.models import Location, Product, Stock
from showrooms.models import Showroom, ShowroomEmployee


SESSION_KEY = 'ACTIVE_SHOWROOM_ID'


class ShowroomIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='u1', password='pass')
        self.user2 = User.objects.create_user(username='u2', password='pass')
        # create two locations
        loc1 = Location.objects.create(name='L1', code='L1')
        loc2 = Location.objects.create(name='L2', code='L2')
        self.s1 = Showroom.objects.create(code='S1', name='S1', location=loc1)
        self.s2 = Showroom.objects.create(code='S2', name='S2', location=loc2)
        ShowroomEmployee.objects.create(showroom=self.s1, user=self.user, role='sales', active=True)
        ShowroomEmployee.objects.create(showroom=self.s2, user=self.user2, role='sales', active=True)
        # sample product & stock
        p = Product.objects.create(sku='P1', name='Prod1')
        Stock.objects.create(product=p, location=loc1, quantity=5)
        Stock.objects.create(product=p, location=loc2, quantity=9)
        self.client = APIClient()

    def _auth(self):
        self.client.force_authenticate(user=self.user)

    def _set_active(self, showroom):
        session = self.client.session
        session[SESSION_KEY] = showroom.id
        session.save()

    def test_product_list_scoped(self):
        self._auth()
        self._set_active(self.s1)
        resp = self.client.get('/api/products/')
        self.assertEqual(resp.status_code, 200)
        # Baseline: products not directly showroom-bound; ensure listing still works
        Product.objects.create(sku='P2', name='Prod2')
        self.assertTrue(len(resp.data) >= 1)

    def _extract_results(self, resp):
        payload = resp.data
        if isinstance(payload, dict):
            if 'results' in payload and isinstance(payload['results'], list):
                return payload['results']
            for v in payload.values():
                if isinstance(v, list):
                    return v
            return []
        if isinstance(payload, list):
            return payload
        return []

    def test_location_list_scoped(self):
        self._auth()
        # بدون تحديد معرض يجب أن تكون النتيجة فارغة الآن
        resp0 = self.client.get('/api/locations/')
        self.assertEqual(resp0.status_code, 200)
        self.assertEqual(len(self._extract_results(resp0)), 0)
        # بعد التعيين لمعرض s1
        self._set_active(self.s1)
        resp = self.client.get('/api/locations/')
        self.assertEqual(resp.status_code, 200)
        results = self._extract_results(resp)
        returned_codes = {r.get('code') for r in results if isinstance(r, dict)}
        self.assertSetEqual(returned_codes, {'L1'})

    def test_cross_access_denied_without_flag(self):
        self._auth()
        self._set_active(self.s2)  # ليس معين له
        resp = self.client.get('/api/locations/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self._extract_results(resp)), 0)

    def test_cross_access_employee_can_switch(self):
        # امنح user صلاحية على المعرضين + can_cross_access
        from showrooms.models import ShowroomEmployee
        se1 = ShowroomEmployee.objects.get(showroom=self.s1, user=self.user)
        se1.can_cross_access = True
        se1.save(update_fields=['can_cross_access'])
        ShowroomEmployee.objects.create(showroom=self.s2, user=self.user, role='sales', active=True, can_cross_access=True)
        self._auth()
        # اختر s1
        self._set_active(self.s1)
        r1 = self.client.get('/api/locations/')
        self.assertEqual({x.get('code') for x in self._extract_results(r1)}, {'L1'})
        # تبديل إلى s2
        self._set_active(self.s2)
        r2 = self.client.get('/api/locations/')
        self.assertEqual({x.get('code') for x in self._extract_results(r2)}, {'L2'})

    def test_stock_list_scoped(self):
        self._auth()
        # بدون معرض => فارغ
        resp0 = self.client.get('/api/stock/')
        self.assertEqual(resp0.status_code, 200)
        self.assertEqual(len(self._extract_results(resp0)), 0)
        # set showroom s1 => يجب أن نرى فقط قيود الموقع L1 (كمية 5)
        self._set_active(self.s1)
        r1 = self.client.get('/api/stock/')
        self.assertEqual(r1.status_code, 200)
        codes1 = {(row.get('location'), row.get('product')) for row in self._extract_results(r1)}
        # العدد 1 (منتج واحد في موقع واحد)
        self.assertEqual(len(codes1), 1)
        # تبديل إلى s2 => قيود الموقع L2 فقط
        self._set_active(self.s2)
        r2 = self.client.get('/api/stock/')
        self.assertEqual(r2.status_code, 200)
        codes2 = {(row.get('location'), row.get('product')) for row in self._extract_results(r2)}
        self.assertEqual(len(codes2), 1)
