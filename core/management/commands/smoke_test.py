from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import resolve
from django.conf import settings
from django.contrib.auth import get_user_model


PAGES_PUBLIC = [
    '/',
    '/accounts/login/',
]

PAGES_AUTH = [
    '/inventory/',
    '/sales/',
    '/purchases/',
    '/reports/',
    '/hr/',
]


class Command(BaseCommand):
    help = 'تشغيل اختبار تدخين سريع على أهم الصفحات (وجود + حالة HTTP)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--fast', action='store_true', help='تقليل عدد الصفحات')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        fast = options['fast']
        client = Client()

        results = []
        # Public pages
        for url in PAGES_PUBLIC:
            try:
                resp = client.get(url)
                results.append((url, resp.status_code))
            except Exception as e:
                results.append((url, f'ERR:{e}'))

        # Login
        login_ok = client.post('/accounts/login/', {'username': username, 'password': password}).status_code in (302, 200)
        results.append(('LOGIN', 'OK' if login_ok else 'FAIL'))
        if not login_ok:
            self.stdout.write(self.style.ERROR('فشل تسجيل الدخول - تحقق من بيانات الاعتماد'))
            return

        auth_pages = PAGES_AUTH[:2] if fast else PAGES_AUTH
        for url in auth_pages:
            try:
                resp = client.get(url)
                results.append((url, resp.status_code))
            except Exception as e:
                results.append((url, f'ERR:{e}'))

        # Summary
        ok_count = sum(1 for _, code in results if isinstance(code, int) and code < 400 or code == 'OK')
        self.stdout.write('نتائج Smoke Test:')
        for url, code in results:
            mark = '✓' if (isinstance(code, int) and code < 400) or code == 'OK' else '✗'
            self.stdout.write(f' {mark} {url} -> {code}')
        self.stdout.write(f'المجموع الناجح: {ok_count}/{len(results)}')
