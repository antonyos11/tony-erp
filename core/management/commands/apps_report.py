"""
أمر لعرض تقرير حالة جميع تطبيقات Tony ERP

الاستخدام:
    python manage.py apps_report
    python manage.py apps_report --json
"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'عرض تقرير حالة جميع تطبيقات Tony ERP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='إخراج بصيغة JSON',
        )

    def handle(self, *args, **options):
        from accountant_pro.apps_registry import get_apps_status, print_apps_report

        if options['json']:
            status = get_apps_status()
            self.stdout.write(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print_apps_report()
