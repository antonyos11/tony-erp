from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta

from hr.models import Department, JobPosition, Employee, HSEIncident


class Command(BaseCommand):
    help = "Seed HSE incidents for the current month to test safety threshold and dashboards."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=4, help="Number of incidents to create in current month")

    def handle(self, *args, **options):
        count = max(int(options.get("count", 4) or 4), 1)

        # Ensure a Safety department
        dept, _ = Department.objects.get_or_create(code="HSE", defaults={"name": "السلامة"})

        # Ensure a job position (fallback if none exists)
        pos = JobPosition.objects.order_by("id").first()
        if not pos:
            pos = JobPosition.objects.create(
                title="HSE Officer",
                code="HSE-OFF",
                department=dept,
                description="Auto-created for seeding",
                requirements="",
                min_salary=0,
                max_salary=0,
                is_active=True,
            )

        # Ensure a bot user/employee
        user, _ = User.objects.get_or_create(username="safety.bot", defaults={"email": "hse-bot@example.com"})
        emp, _ = Employee.objects.get_or_create(
            user=user,
            defaults={
                "employee_id": "E999",
                "first_name": "Safety",
                "last_name": "Bot",
                "arabic_name": "بوت السلامة",
                "national_id": "9999999999",
                "gender": "M",
                "birth_date": date(1990, 1, 1),
                "marital_status": "single",
                "phone": "000",
                "email": "hse-bot@example.com",
                "address": "N/A",
                "emergency_contact_name": "N/A",
                "emergency_contact_phone": "000",
                "department": dept,
                "position": pos,
                "hire_date": date(2020, 1, 1),
                "basic_salary": 0,
            },
        )

        start = date.today().replace(day=1)
        created = 0
        for i in range(count):
            obj, was_created = HSEIncident.objects.get_or_create(
                date=start + timedelta(days=i),
                description=f"Seeded incident {i+1}",
                defaults={"employee": emp, "department": dept, "status": "open"},
            )
            if was_created:
                created += 1

        total = HSEIncident.objects.filter(date__gte=start).count()
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} incidents. Current month total: {total}"))
