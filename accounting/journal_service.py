from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Iterable, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import JournalEntry, JournalEntryItem, Account, CostCenter
from .services import post_journal_entry as svc_post

User = get_user_model()

@dataclass
class JournalItemData:
    account_id: int
    type: str  # 'debit' or 'credit'
    amount: Decimal
    description: str = ''
    cost_center_id: Optional[int] = None
    master_account: str = ''
    analytics: str = ''
    analytics_2: str = ''
    analytics_3: str = ''

class JournalService:
    """طبقة خدمة موحدة لإنشاء وترحيل القيود.

    المزايا:
    - تحقق من التوازن قبل الإنشاء.
    - تعامل ذري داخل معاملة.
    - خيار الترحيل التلقائي.
    """

    @staticmethod
    def create_journal(description: str, entry_type: str, date, items: Iterable[JournalItemData], reference: str = '', user: Optional[Any] = None, auto_post: bool = True) -> JournalEntry:
        items_list: List[JournalItemData] = list(items)
        if len(items_list) < 2:
            raise ValidationError('يجب توفير بندين على الأقل')
        total_debit = Decimal('0'); total_credit = Decimal('0')
        for it in items_list:
            if it.type not in ('debit','credit'):
                raise ValidationError('نوع بند غير صالح')
            if it.amount <= 0:
                raise ValidationError('مبلغ بند غير صالح')
            if it.type == 'debit':
                total_debit += it.amount
            else:
                total_credit += it.amount
        if total_debit == 0 or total_credit == 0 or total_debit != total_credit:
            raise ValidationError('القيد غير متوازن')
        with transaction.atomic():
            je = JournalEntry.objects.create(
                description=description.strip() or 'قيد محاسبي',
                entry_type=entry_type or 'manual',
                reference=reference.strip(),
                date=date,
                created_by=user if user and getattr(user, 'is_authenticated', False) else None,
                is_posted=False,
            )
            objs = []
            for it in items_list:
                objs.append(JournalEntryItem(
                    journal_entry=je,
                    account_id=it.account.id,
                    type=it.type,
                    amount=it.amount,
                    description=(it.description or description)[:255],
                    cost_center_id=it.cost_center_id,
                    master_account=it.master_account[:200],
                    analytics=it.analytics[:200],
                    analytics_2=it.analytics_2[:200],
                    analytics_3=it.analytics_3[:200],
                ))
            # enforce clean on each (ensures cost center requirements)
            for o in objs:
                o.full_clean()
            JournalEntryItem.objects.bulk_create(objs)
            if auto_post:
                svc_post(je, force=False)
        return je

    @staticmethod
    def reverse(entry: JournalEntry, user: Optional[Any] = None, date_override=None, auto_post: bool = True) -> JournalEntry:
        """إنشاء قيد عكسي بالكامل (يعكس المدين والدائن) مع ربط مرجعي.

        لا يحذف القيد الأصلي؛ يُستخدم في حالات التصحيح المحاسبي وفق المعايير.
        """
        if not entry.is_posted:
            raise ValidationError('لا يمكن عكس قيد غير مرحل')
        rev_date = date_override or entry.date
        items: list[JournalItemData] = []
        for it in entry.items.all():  # type: ignore[attr-defined]
            opposite_type = 'credit' if it.type == 'debit' else 'debit'
            items.append(JournalItemData(
                account_id=it.account.id,
                type=opposite_type,
                amount=it.amount,
                description=f"عكس: {it.description[:200]}",
                cost_center_id=getattr(it, 'cost_center_id', None),
                master_account=getattr(it, 'master_account', ''),
                analytics=getattr(it, 'analytics', ''),
                analytics_2=getattr(it, 'analytics_2', ''),
                analytics_3=getattr(it, 'analytics_3', ''),
            ))
        ref = f"REV-{entry.number}" if getattr(entry, 'number', None) else f"REV-{entry.pk}"  # type: ignore
        desc = f"قيد عكسي للقيد {entry.number or entry.pk}"  # type: ignore
        rev_entry = JournalService.create_journal(
            description=desc,
            entry_type='reversal',
            date=rev_date,
            items=items,
            reference=ref,
            user=user,
            auto_post=auto_post,
        )
        return rev_entry

__all__ = ["JournalService", "JournalItemData"]
