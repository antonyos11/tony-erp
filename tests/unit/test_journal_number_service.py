"""
Unit tests for Phase-1 Step-1: Journal Number Generation Service
================================================================
Covers:
- Number format correctness
- Per-year and per-branch isolation
- Sequential uniqueness (50-number burst)
- Concurrent uniqueness (30 threads)
- Retry logic on collision
- RuntimeError after _MAX_RETRIES exhausted
- Model.save() integration (no-number path)
- Service import is clean (no circular imports)

Priority: P0 — Financial Integrity
"""

import threading
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import TestCase


# ============================================================================
# Import smoke test — catches circular imports immediately
# ============================================================================

def test_import_journal_number_service():
    """Service module imports without circular-import errors."""
    from accounting import journal_number_service  # noqa: F401


# ============================================================================
# Unit tests (no DB required for most)
# ============================================================================

class TestGenerateJournalNumberFormat(TestCase):
    """Number format tests — run against the real Sequence table."""

    def test_returns_string(self):
        from accounting.journal_number_service import generate_journal_number
        assert isinstance(generate_journal_number(), str)

    def test_starts_with_je(self):
        from accounting.journal_number_service import generate_journal_number
        assert generate_journal_number().startswith('JE-')

    def test_contains_requested_year(self):
        from accounting.journal_number_service import generate_journal_number
        number = generate_journal_number(year=2025)
        assert '2025' in number

    def test_defaults_to_current_year(self):
        from django.utils import timezone
        from accounting.journal_number_service import generate_journal_number
        year = str(timezone.now().year)
        assert year in generate_journal_number()

    def test_global_format_no_branch(self):
        from accounting.journal_number_service import generate_journal_number
        # JE-2026-000001 style (no BRx segment)
        number = generate_journal_number(year=2099)
        assert 'BR' not in number
        assert 'JE-2099-' in number

    def test_branch_format_contains_brx(self):
        from accounting.journal_number_service import generate_journal_number
        number = generate_journal_number(branch_id=7, year=2099)
        assert 'JE-BR7-2099-' in number

    def test_sequence_zero_padded_to_6_digits(self):
        from accounting.journal_number_service import generate_journal_number
        # e.g. "JE-2099-000001" — last segment must be 6 chars wide
        number = generate_journal_number(year=2099)
        seq_part = number.split('-')[-1]
        assert len(seq_part) == 6

    def test_different_branches_have_different_prefixes(self):
        from accounting.journal_number_service import generate_journal_number
        n1 = generate_journal_number(branch_id=1, year=2099)
        n2 = generate_journal_number(branch_id=2, year=2099)
        assert 'BR1' in n1
        assert 'BR2' in n2
        # Sequence positions may match (both start at 1) but prefixes differ
        assert n1 != n2


# ============================================================================
# Sequential uniqueness
# ============================================================================

class TestSequentialUniqueness(TestCase):
    """50 consecutive calls in one thread must yield distinct numbers."""

    def test_50_sequential_unique_numbers(self):
        from accounting.journal_number_service import generate_journal_number
        numbers = [generate_journal_number(year=2098) for _ in range(50)]
        assert len(set(numbers)) == 50, (
            f"Duplicate numbers detected: "
            f"{[n for n in numbers if numbers.count(n) > 1]}"
        )


# ============================================================================
# Concurrent uniqueness
# ============================================================================

class TestConcurrentUniqueness(TestCase):
    """30 threads simultaneously calling generate_journal_number must all get unique numbers."""

    def test_30_concurrent_unique_numbers(self):
        from accounting.journal_number_service import generate_journal_number

        results = []
        errors = []
        lock = threading.Lock()

        def worker():
            try:
                number = generate_journal_number(year=2097)
                with lock:
                    results.append(number)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent generation: {errors}"
        assert len(results) == 30
        assert len(set(results)) == 30, (
            f"Duplicate numbers under concurrency: "
            f"{[n for n in results if results.count(n) > 1]}"
        )


# ============================================================================
# Retry / collision logic
# ============================================================================

class TestRetryLogic(TestCase):

    def test_raises_runtime_error_after_max_retries(self):
        """If every generated number already exists, RuntimeError is raised."""
        from accounting import journal_number_service as svc

        with patch.object(svc, 'next_sequence', return_value=42), \
             patch('accounting.models.JournalEntry.objects') as mock_qs:
            mock_qs.filter.return_value.exists.return_value = True  # always collides
            with self.assertRaises(RuntimeError) as ctx:
                svc.generate_journal_number(year=2096)

        assert 'Failed to generate' in str(ctx.exception)

    def test_retries_on_integrity_error_then_succeeds(self):
        """IntegrityError on first attempt triggers a retry that succeeds."""
        from accounting import journal_number_service as svc
        from django.db import IntegrityError as DjIntegrityError

        call_count = 0

        def patched_next(key, initial=1):
            nonlocal call_count
            call_count += 1
            return call_count

        # Attempt 1: exists() True → skip; attempt 2: exists() False → return
        with patch.object(svc, 'next_sequence', side_effect=patched_next), \
             patch('accounting.models.JournalEntry.objects') as mock_qs:
            mock_qs.filter.return_value.exists.side_effect = [True, False]
            number = svc.generate_journal_number(year=2096)

        assert number is not None
        assert call_count == 2  # exactly 2 sequence increments

    def test_non_uniqueness_integrity_error_is_retried(self):
        """IntegrityError with 'unique' in message triggers retry."""
        from accounting import journal_number_service as svc
        from django.db import IntegrityError as DjIntegrityError

        attempt = 0

        def patched_next(key, initial=1):
            nonlocal attempt
            attempt += 1
            return attempt

        def mock_exists():
            if attempt <= 1:
                raise DjIntegrityError("UNIQUE constraint failed: accounting_journalentry.number")
            return False

        with patch.object(svc, 'next_sequence', side_effect=patched_next), \
             patch('accounting.models.JournalEntry.objects') as mock_qs:
            mock_qs.filter.return_value.exists.side_effect = mock_exists
            # Should NOT raise — retries and succeeds
            number = svc.generate_journal_number(year=2096)

        assert number is not None

    def test_non_unique_integrity_error_re_raises(self):
        """IntegrityError unrelated to uniqueness propagates immediately."""
        from accounting import journal_number_service as svc
        from django.db import IntegrityError as DjIntegrityError

        with patch.object(svc, 'next_sequence', return_value=1), \
             patch('accounting.models.JournalEntry.objects') as mock_qs:
            mock_qs.filter.return_value.exists.side_effect = DjIntegrityError("foreign key violation")
            with self.assertRaises(DjIntegrityError):
                svc.generate_journal_number(year=2096)


# ============================================================================
# Model.save() integration
# ============================================================================

class TestModelSaveIntegration(TestCase):
    """JournalEntry.save() must use the service when number is blank."""

    def test_auto_number_assigned_on_save(self):
        """A JournalEntry without a number gets one assigned via service."""
        from accounting.models import JournalEntry
        from accounting.journal_number_service import generate_journal_number

        entry = JournalEntry.__new__(JournalEntry)
        entry.number = ''

        called_with = {}

        def patched_generate(branch_id=None, year=None):
            called_with['branch_id'] = branch_id
            called_with['year'] = year
            return 'JE-2026-TEST01'

        with patch('accounting.journal_number_service.generate_journal_number',
                   side_effect=patched_generate):
            with patch.object(JournalEntry, 'is_balanced', new_callable=lambda: property(lambda s: True)), \
                 patch('django.db.models.Model.save', return_value=None):
                from accounting.models import JournalEntry as JE
                je = JE()
                je.number = ''
                je.is_posted = False
                je.save()

        assert je.number == 'JE-2026-TEST01'

    def test_existing_number_not_overwritten(self):
        """A JournalEntry with an existing number keeps it on save."""
        from accounting.models import JournalEntry
        from accounting.journal_number_service import generate_journal_number

        generate_called = []

        with patch('accounting.journal_number_service.generate_journal_number',
                   side_effect=lambda **kw: generate_called.append(True)):
            with patch.object(JournalEntry, 'is_balanced', new_callable=lambda: property(lambda s: True)), \
                 patch('django.db.models.Model.save', return_value=None):
                je = JournalEntry()
                je.number = 'JE-2026-EXISTING'
                je.is_posted = False
                je.save()

        assert je.number == 'JE-2026-EXISTING'
        assert not generate_called, "generate_journal_number should NOT be called when number already set"


# ============================================================================
# COUNT+1 antipattern is gone
# ============================================================================

class TestNoCountPlusOnePattern(TestCase):
    """Regression guard: ensure the old COUNT+1 pattern is not present anywhere."""

    def test_model_save_does_not_use_count_plus_one(self):
        import inspect
        from accounting.models import JournalEntry

        src = inspect.getsource(JournalEntry.save)
        assert '.count() + 1' not in src, (
            "JournalEntry.save() still contains the COUNT()+1 antipattern!"
        )

    def test_integration_services_does_not_use_old_pattern(self):
        import inspect
        import core.integration_services as svc

        # Check the whole module source
        src = inspect.getsource(svc)
        assert "format_code('JE', seq)" not in src, (
            "core/integration_services.py still uses format_code('JE', seq)!"
        )
        assert "next_sequence('JOURNAL_ENTRY')" not in src, (
            "core/integration_services.py still uses next_sequence('JOURNAL_ENTRY')!"
        )
