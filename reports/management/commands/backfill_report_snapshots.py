from __future__ import annotations
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from reports.services import create_daily_snapshot


class Command(BaseCommand):
    help = "Backfill missing ReportDailySnapshot rows for a date range (default: last 30 days). Idempotent."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument('--days', type=int, default=30, help='Number of trailing days to ensure snapshots for.')
        parser.add_argument('--start', type=str, help='Explicit start date (YYYY-MM-DD).')
        parser.add_argument('--end', type=str, help='Explicit end date (YYYY-MM-DD).')

    def handle(self, *args, **opts):  # type: ignore[override]
        days = opts.get('days') or 30
        start_str = opts.get('start')
        end_str = opts.get('end')
        def parse(d: str):
            from datetime import datetime
            for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
                try:
                    return datetime.strptime(d, fmt).date()
                except Exception:
                    continue
            raise ValueError(f'Invalid date format: {d}')
        if start_str and end_str:
            start = parse(start_str)
            end = parse(end_str)
        else:
            end = date.today()
            start = end - timedelta(days=days-1)
        if end < start:
            self.stderr.write('End date must be >= start date')
            return
        cur = start
        created = 0
        while cur <= end:
            snap = create_daily_snapshot(cur)
            created += 1
            self.stdout.write(f"Ensured snapshot {snap.date}")
            cur += timedelta(days=1)
        self.stdout.write(self.style.SUCCESS(f"Backfill complete for {created} day(s) {start} -> {end}"))
