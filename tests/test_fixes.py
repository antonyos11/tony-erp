"""
Tony ERP - اختبارات الإصلاحات (heartbeat, dashboard stats, connection)
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class HeartbeatTests(TestCase):
    """Heartbeat endpoint tests"""

    def setUp(self):
        self.c = Client()

    def test_heartbeat_returns_200(self):
        """GET /heartbeat/ returns 200"""
        r = self.c.get('/heartbeat/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['status'], 'connected')
        self.assertIn('ts', d)

    def test_heartbeat_no_auth_required(self):
        """Heartbeat does not require authentication"""
        r = self.c.get('/heartbeat/')
        self.assertNotIn(r.status_code, [401, 403])

    def test_api_heartbeat(self):
        """GET /api/heartbeat/ returns 200"""
        r = self.c.get('/api/heartbeat/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['status'], 'connected')

    def test_connection_status(self):
        """GET /api/connection/ returns 200"""
        r = self.c.get('/api/connection/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['status'], 'online')
        self.assertIn('user', d)
        self.assertIn('db', d)

    def test_connection_db_check(self):
        """Connection status includes DB check"""
        r = self.c.get('/api/connection/')
        d = r.json()
        self.assertEqual(d['db']['status'], 'ok')
        self.assertIn('ms', d['db'])

    def test_server_time(self):
        """GET /api/server-time/ returns time info"""
        r = self.c.get('/api/server-time/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertIn('iso', d)
        self.assertIn('unix', d)
        self.assertIn('date', d)
        self.assertIn('time', d)


class DashboardStatsAPITests(TestCase):
    """Dashboard Stats API tests"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='dash_test_user',
            password='TestP@ss123!',
        )

    def setUp(self):
        self.c = Client()

    def test_dashboard_stats_requires_auth(self):
        """GET /api/dashboard/stats/ requires authentication"""
        r = self.c.get('/api/dashboard/stats/')
        # Should redirect to login (302) since it uses @login_required
        self.assertIn(r.status_code, [302, 401, 403])

    def test_dashboard_stats_authenticated(self):
        """Authenticated user can access dashboard stats"""
        self.c.login(username='dash_test_user', password='TestP@ss123!')
        r = self.c.get('/api/dashboard/stats/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertIn('today', d)
        self.assertIn('month', d)
        self.assertIn('generated_at', d)

    def test_dashboard_stats_structure(self):
        """Dashboard stats has correct structure"""
        self.c.login(username='dash_test_user', password='TestP@ss123!')
        r = self.c.get('/api/dashboard/stats/')
        d = r.json()
        today = d['today']
        self.assertIn('sales', today)
        self.assertIn('purchases', today)
        self.assertIn('collections', today)
        self.assertIn('expenses', today)
        self.assertIn('net', today)
        self.assertIn('total', today['sales'])
        self.assertIn('count', today['sales'])

    def test_dashboard_stats_numeric_values(self):
        """Dashboard stats returns numeric values"""
        self.c.login(username='dash_test_user', password='TestP@ss123!')
        r = self.c.get('/api/dashboard/stats/')
        d = r.json()
        # All values should be numeric (int or float)
        self.assertIsInstance(d['today']['sales']['total'], (int, float))
        self.assertIsInstance(d['today']['purchases']['total'], (int, float))
        self.assertIsInstance(d['today']['net'], (int, float))
        self.assertIsInstance(d['today']['collections'], (int, float))
        self.assertIsInstance(d['today']['expenses'], (int, float))


class DashboardDataServiceTests(TestCase):
    """Unit tests for DashboardDataService"""

    def test_service_instantiation(self):
        """DashboardDataService can be created"""
        from core.fixes.dashboard_fix import DashboardDataService
        svc = DashboardDataService()
        self.assertIsNotNone(svc)

    def test_get_all_stats_returns_dict(self):
        """get_all_stats returns a proper dict"""
        from core.fixes.dashboard_fix import DashboardDataService
        svc = DashboardDataService()
        stats = svc.get_all_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('today', stats)
        self.assertIn('month', stats)

    def test_get_dashboard_context_shortcut(self):
        """get_dashboard_context convenience function works"""
        from core.fixes.dashboard_fix import get_dashboard_context
        ctx = get_dashboard_context()
        self.assertIsInstance(ctx, dict)
        self.assertIn('today', ctx)

    def test_net_calculation(self):
        """Net = sales - purchases"""
        from core.fixes.dashboard_fix import DashboardDataService
        svc = DashboardDataService()
        stats = svc.get_all_stats()
        expected_net = stats['today']['sales']['total'] - stats['today']['purchases']['total']
        self.assertAlmostEqual(stats['today']['net'], expected_net, places=2)
