import pycountry
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Country, State


class Command(BaseCommand):
    help = "Import countries and their subdivisions (states) from pycountry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing states before import (countries stay intact).",
        )

    def handle(self, *args, **options):
        reset_states = options.get("reset", False)
        created_countries = 0
        updated_countries = 0
        created_states = 0
        skipped_states = 0

        with transaction.atomic():
            countries_map = {}
            for country in pycountry.countries:
                defaults = {
                    "name": country.name[:100],
                    "name_en": getattr(country, "name", "")[:100],
                    "phone_code": getattr(country, "country_code", "")[:10],
                }
                obj, created = Country.objects.get_or_create(
                    code=country.alpha_2,
                    defaults=defaults,
                )
                if created:
                    created_countries += 1
                else:
                    changed = False
                    if obj.name != defaults["name"]:
                        obj.name = defaults["name"]
                        changed = True
                    if obj.name_en != defaults["name_en"]:
                        obj.name_en = defaults["name_en"]
                        changed = True
                    if defaults["phone_code"] and obj.phone_code != defaults["phone_code"]:
                        obj.phone_code = defaults["phone_code"]
                        changed = True
                    if changed:
                        obj.save(update_fields=["name", "name_en", "phone_code"])
                        updated_countries += 1
                countries_map[country.alpha_2] = obj

            if reset_states:
                State.objects.all().delete()

            existing_pairs = set(
                State.objects.values_list("country__code", "name")
            )
            bulk_states = []
            for subdivision in pycountry.subdivisions:
                country_obj = countries_map.get(subdivision.country_code)
                if not country_obj:
                    continue

                state_name = subdivision.name[:100]
                key = (subdivision.country_code, state_name)
                if key in existing_pairs:
                    skipped_states += 1
                    continue

                state_code = subdivision.code.split("-")[-1][:10]
                bulk_states.append(
                    State(
                        country=country_obj,
                        name=state_name,
                        name_en=subdivision.name[:100],
                        code=state_code,
                        is_active=True,
                    )
                )

            if bulk_states:
                State.objects.bulk_create(bulk_states, ignore_conflicts=True, batch_size=500)
                created_states = len(bulk_states)

        self.stdout.write(
            self.style.SUCCESS(
                "Countries: +%d new, %d updated. States added: %d, skipped (existing): %d." % (
                    created_countries,
                    updated_countries,
                    created_states,
                    skipped_states,
                )
            )
        )
