from django.core.management.base import BaseCommand
from datetime import date
from reports.services import create_daily_snapshot


class Command(BaseCommand):
    help = "Create or refresh daily report snapshot for today or given --date (YYYY-MM-DD)."

    def add_arguments(self, parser):
        parser.add_argument('--date', dest='date_str', help='Date (YYYY-MM-DD); default today')

    def handle(self, *args, **options):
        d = None
        ds = options.get('date_str')
        if ds:
            try:
                d = date.fromisoformat(ds)
            except Exception:
                self.stderr.write('Invalid date format, expected YYYY-MM-DD')
                return 1
        snap = create_daily_snapshot(d)
        self.stdout.write(self.style.SUCCESS(f"Snapshot stored for {snap.date}"))
        return 0
