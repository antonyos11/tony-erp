"""
Pre-flight repair: detect and fix duplicate JournalEntry numbers.
=================================================================
Run BEFORE deploying Phase-1 Step-1 changes on a live database.

Usage:
    python manage.py shell < scripts/maintenance/fix_duplicate_journal_numbers.py

What it does:
    1. Finds all JournalEntry numbers that appear more than once.
    2. Keeps the entry with the lowest id (oldest) untouched.
    3. Renames every duplicate to '{original}-DUP{n}' so the unique
       constraint can be applied without losing any data.

Exit codes (when run as a script, not via shell):
    0 — no duplicates found, or all fixed successfully
    1 — an error occurred during repair
"""

import sys
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')

# Only call setup() if Django is not already configured (e.g. running standalone)
try:
    from django.apps import apps
    apps.get_app_config('accounting')
except (LookupError, RuntimeError):
    django.setup()

from django.db import transaction
from django.db.models import Count

from accounting.models import JournalEntry


def find_duplicates():
    """Return a queryset of number values that appear more than once."""
    return (
        JournalEntry.objects
        .values('number')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
        .order_by('-cnt')
    )


def fix_duplicates(dry_run: bool = False) -> int:
    """
    Detect and rename duplicate journal numbers.

    Parameters
    ----------
    dry_run:
        When True, report duplicates but make no changes.

    Returns
    -------
    int
        Number of entries renamed (0 if none found).
    """
    duplicates = list(find_duplicates())

    if not duplicates:
        print("✅  No duplicate journal numbers found — safe to proceed.")
        return 0

    print(f"⚠️   Found {len(duplicates)} number(s) with duplicates:")
    total_fixed = 0

    for dup in duplicates:
        original_number = dup['number']
        entries = list(
            JournalEntry.objects
            .filter(number=original_number)
            .order_by('id')  # keep earliest (lowest id) intact
        )
        print(f"\n  number={original_number!r}  —  {len(entries)} entries (ids: {[e.id for e in entries]})")

        # Skip the first (keep it), rename the rest
        for idx, entry in enumerate(entries[1:], start=1):
            new_number = f"{original_number}-DUP{idx}"
            if dry_run:
                print(f"    [DRY RUN] Would rename id={entry.id}: {original_number!r} → {new_number!r}")
            else:
                with transaction.atomic():
                    entry.number = new_number
                    entry.save(update_fields=['number'])
                print(f"    ✔  Renamed id={entry.id}: {original_number!r} → {new_number!r}")
            total_fixed += 1

    if dry_run:
        print(f"\n⚠️   DRY RUN — {total_fixed} entries would be renamed. Re-run without --dry-run to apply.")
    else:
        print(f"\n✅  Fixed {total_fixed} duplicate entries. Database is now ready for unique constraint.")

    return total_fixed


def verify_uniqueness():
    """Final check: confirm zero duplicates remain."""
    remaining = list(find_duplicates())
    if remaining:
        print(f"\n❌  {len(remaining)} duplicate(s) still exist after repair:")
        for d in remaining:
            print(f"    number={d['number']!r}  count={d['cnt']}")
        return False
    print("\n✅  Uniqueness verified — no duplicate journal numbers.")
    return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Fix duplicate JournalEntry numbers")
    parser.add_argument('--dry-run', action='store_true',
                        help="Report duplicates without making changes")
    args = parser.parse_args()

    changed = fix_duplicates(dry_run=args.dry_run)

    if not args.dry_run:
        ok = verify_uniqueness()
        sys.exit(0 if ok else 1)

    sys.exit(0)
