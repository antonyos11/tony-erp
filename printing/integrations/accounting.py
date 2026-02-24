"""
Accounting module integration:
  - One-click print for Journal Entries
  - Trial Balance report printing
تكامل المحاسبة:
  - طباعة بنقرة واحدة للقيود المحاسبية
  - طباعة تقرير ميزان المراجعة
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def print_journal_entry(journal_entry, user=None) -> Tuple[bool, str]:
    """Print a journal entry document."""
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string

    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    html = render_to_string('printing/journal_entry_print.html', {
        'entry': journal_entry,
        'items': journal_entry.items.select_related('account').all(),
        'company': company,
    })

    pdf_bytes = _try_pdf(html)
    if pdf_bytes:
        return PrintDispatcher.print_pdf(
            document_type='journal_entry',
            pdf_bytes=pdf_bytes,
            title=f"قيد محاسبي #{journal_entry.number}",
            user=user,
            source_app='accounting',
            source_model='JournalEntry',
            source_id=str(journal_entry.pk),
        )[:2]
    else:
        return PrintDispatcher.print_html(
            document_type='journal_entry',
            html=html,
            title=f"قيد محاسبي #{journal_entry.number}",
            user=user,
            source_app='accounting',
            source_model='JournalEntry',
            source_id=str(journal_entry.pk),
        )[:2]


def print_trial_balance(date_from, date_to, user=None) -> Tuple[bool, str]:
    """Print a trial balance report for a date range."""
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string
    from django.db.models import Sum, Q, DecimalField
    from django.db.models.functions import Coalesce
    from decimal import Decimal

    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    from accounting.models import Account, JournalEntryItem

    accounts = Account.objects.filter(is_active=True).annotate(
        total_debit=Coalesce(
            Sum(
                'journal_entries__amount',
                filter=Q(
                    journal_entries__type='debit',
                    journal_entries__journal_entry__date__gte=date_from,
                    journal_entries__journal_entry__date__lte=date_to,
                    journal_entries__journal_entry__is_posted=True,
                )
            ),
            Decimal('0'),
            output_field=DecimalField(),
        ),
        total_credit=Coalesce(
            Sum(
                'journal_entries__amount',
                filter=Q(
                    journal_entries__type='credit',
                    journal_entries__journal_entry__date__gte=date_from,
                    journal_entries__journal_entry__date__lte=date_to,
                    journal_entries__journal_entry__is_posted=True,
                )
            ),
            Decimal('0'),
            output_field=DecimalField(),
        ),
    ).filter(
        Q(total_debit__gt=0) | Q(total_credit__gt=0)
    ).order_by('code')

    html = render_to_string('printing/trial_balance_print.html', {
        'accounts': accounts,
        'date_from': date_from,
        'date_to': date_to,
        'company': company,
    })

    pdf_bytes = _try_pdf(html)
    if pdf_bytes:
        return PrintDispatcher.print_pdf(
            document_type='trial_balance',
            pdf_bytes=pdf_bytes,
            title=f"ميزان المراجعة {date_from} - {date_to}",
            user=user,
            source_app='accounting',
            source_model='TrialBalance',
            source_id=f"{date_from}_{date_to}",
        )[:2]
    else:
        return PrintDispatcher.print_html(
            document_type='trial_balance',
            html=html,
            title=f"ميزان المراجعة {date_from} - {date_to}",
            user=user,
            source_app='accounting',
            source_model='TrialBalance',
            source_id=f"{date_from}_{date_to}",
        )[:2]


def _try_pdf(html: str):
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:
        return None
