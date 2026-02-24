"""
Journal Number Generation Service
==================================
Thread-safe, retry-safe journal number generator backed by PostgreSQL
row-level locking via core.sequence_utils.next_sequence (select_for_update).

WHY THIS EXISTS
---------------
The old model.save() logic used COUNT()+1 to pick the next number:

    count = JournalEntry.objects.filter(number__startswith=f'JE-{year}').count() + 1
    self.number = f'JE-{year}-{count:06d}'

Under concurrent load two transactions can both read the same COUNT, producing
duplicate numbers that either silently corrupt data or crash with an IntegrityError.

HOW THIS WORKS
--------------
- `next_sequence(key)` grabs a `select_for_update()` row lock on a named
  Sequence row, increments it atomically, and returns the new value.
- Each year gets its own sequence row, so sequences never reset mid-year.
- An optional branch_id isolates sequences per branch (multi-branch setups).
- A retry loop handles the unlikely edge case where a number was already
  inserted by a competing transaction before the DB constraint fires.

USAGE
-----
    from accounting.journal_number_service import generate_journal_number

    # global (no branch)
    number = generate_journal_number()                    # e.g. JE-2026-000042

    # per-branch
    number = generate_journal_number(branch_id=3)         # e.g. JE-BR3-2026-000001
"""

import logging

from django.db import transaction, IntegrityError

from core.sequence_utils import next_sequence

logger = logging.getLogger(__name__)

# Maximum retry attempts before abandoning — should never be reached in normal ops
_MAX_RETRIES = 10


def generate_journal_number(branch_id=None, year: int = None) -> str:
    """
    Generate a unique, concurrency-safe journal entry number.

    Number format
    -------------
    - No branch:   JE-{YEAR}-{SEQ:06}      e.g.  JE-2026-000001
    - With branch: JE-BR{ID}-{YEAR}-{SEQ:06}  e.g.  JE-BR3-2026-000001

    The sequence is persisted in the `core_sequence` table, isolated by year
    (and optionally by branch).

    Parameters
    ----------
    branch_id:
        Optional branch identifier. When provided the sequence is isolated to
        that branch so different branches do not share counter values.
    year:
        Calendar year for the sequence key (defaults to current year).

    Returns
    -------
    str
        A unique journal entry number guaranteed by the DB-level unique
        constraint on ``JournalEntry.number``.

    Raises
    ------
    RuntimeError
        If ``_MAX_RETRIES`` consecutive collision attempts occur, which
        indicates a data integrity problem that needs manual investigation.
    """
    from django.utils import timezone

    if year is None:
        year = timezone.now().year

    if branch_id is not None:
        seq_key = f"JOURNAL_ENTRY_BR{branch_id}_{year}"
        prefix = f"JE-BR{branch_id}-{year}"
    else:
        seq_key = f"JOURNAL_ENTRY_{year}"
        prefix = f"JE-{year}"

    for attempt in range(_MAX_RETRIES):
        try:
            with transaction.atomic():
                seq = next_sequence(seq_key)
                number = f"{prefix}-{str(seq).zfill(6)}"

                # Fast path: check before the DB constraint fires to avoid
                # a round-trip IntegrityError on the happy path.
                from accounting.models import JournalEntry
                if not JournalEntry.objects.filter(number=number).exists():
                    logger.debug("Generated journal number %s (attempt %d)", number, attempt + 1)
                    return number

                logger.warning(
                    "Journal number collision on attempt %d: %s — retrying",
                    attempt + 1,
                    number,
                )
                # Loop → next_sequence will return a higher value on next call
                continue

        except IntegrityError as exc:
            err = str(exc).lower()
            if "unique" in err or "duplicate" in err:
                logger.warning(
                    "IntegrityError collision on journal number attempt %d: %s — retrying",
                    attempt + 1,
                    exc,
                )
                continue
            raise  # re-raise unexpected IntegrityErrors

    raise RuntimeError(
        f"Failed to generate a unique journal number after {_MAX_RETRIES} attempts "
        f"(branch_id={branch_id}, year={year}). "
        "This indicates sequence drift or an unexpected data integrity issue. "
        "Run: python manage.py shell < scripts/maintenance/fix_duplicate_journal_numbers.py"
    )
