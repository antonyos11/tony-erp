import re
from django.test import TestCase, RequestFactory
from django.urls import reverse
from core.context_processors import system_info, user_permissions

class SidebarURLsTest(TestCase):
    def setUp(self):
        from users.models import User
        self.user = User.objects.create_superuser(username='u', password='p', email='u@example.com')
        self.factory = RequestFactory()

    def test_all_named_urls_reverse(self):
        request = self.factory.get('/')
        request.user = self.user
        ctx = user_permissions(request)
        failures = []
        for module_key, module in ctx['user_modules'].items():
            for item in module['items']:
                url_name = item.get('url')
                if not url_name or url_name.startswith('/'):
                    continue
                try:
                    reverse(url_name)
                except Exception as e:  # pragma: no cover - debug help
                    failures.append((url_name, str(e)))
        if failures:
            msgs = '\n'.join(f"{name}: {err}" for name, err in failures)
            self.fail(f"Reverse failed for {len(failures)} names:\n{msgs}")

    def test_unposted_journal_entries_count_in_system_info(self):
        request = self.factory.get('/')
        request.user = self.user
        ctx = system_info(request)
        self.assertIn('unposted_journal_entries_count', ctx)
        self.assertIsInstance(ctx['unposted_journal_entries_count'], int)
