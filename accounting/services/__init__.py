"""حزمة الخدمات المحاسبية الموحدة.

تم دمج الخدمات السابقة (services.py + accounting.py + cache.py) هنا لتفادي
التعارض بين وجود ملف ومجلد بنفس الاسم.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Dict, Optional

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Sum, Q

from ..models import (
	Account,
	JournalEntry,
	JournalEntryItem,
	AccountingSettings,
)

from datetime import date as _date

if TYPE_CHECKING:  # للاستدلال فقط
	try:
		from purchases.models import PurchaseBill, SupplierPayment  # type: ignore
	except Exception:  # pragma: no cover
		PurchaseBill = None  # type: ignore
		SupplierPayment = None  # type: ignore
	try:
		from partners.models import Supplier  # type: ignore
	except Exception:  # pragma: no cover
		Supplier = None  # type: ignore
else:  # محاولات استيراد مرنة وقت التشغيل
	try:  # pragma: no cover
		from purchases.models import PurchaseBill, SupplierPayment  # type: ignore
	except Exception:  # pragma: no cover
		PurchaseBill = None  # type: ignore
		SupplierPayment = None  # type: ignore
	try:  # pragma: no cover
		from partners.models import Supplier  # type: ignore
	except Exception:  # pragma: no cover
		Supplier = None  # type: ignore


BALANCE_CACHE_KEY = 'acc_balance_{id}'
BALANCE_TIMEOUT = 300  # 5 دقائق


def build_supplier_statement(supplier, date_from=None, date_to=None):
	"""بناء كشف حساب مورد (مبسط)."""
	if not supplier or PurchaseBill is None:
		return {'timeline': [], 'opening_balance': Decimal('0'), 'balance': Decimal('0'), 'aging': {}, 'date_from': date_from, 'date_to': date_to}

	bills_qs = PurchaseBill.objects.filter(supplier=supplier).prefetch_related('items')  # type: ignore[arg-type]
	if date_from:
		opening_bills = bills_qs.filter(date__lt=date_from)
		opening_total = sum((b.total or Decimal('0')) for b in opening_bills)
	else:
		opening_total = Decimal('0')

	if SupplierPayment is not None:
		payments_qs = SupplierPayment.objects.filter(supplier=supplier)  # type: ignore[arg-type]
	else:
		payments_qs = JournalEntryItem.objects.filter(
			journal_entry__entry_type__in=['payment'],
			description__icontains=supplier.name  # type: ignore[union-attr]
		)
	if date_from:
		pays_before = payments_qs.filter(journal_entry__date__lt=date_from)
		pays_before_total = pays_before.aggregate(s=Sum('amount'))['s'] or Decimal('0')
	else:
		pays_before_total = Decimal('0')

	opening_balance = opening_total - pays_before_total

	bills = bills_qs
	pays = payments_qs
	if date_from:
		bills = bills.filter(date__gte=date_from)
		pays = pays.filter(journal_entry__date__gte=date_from)
	if date_to:
		bills = bills.filter(date__lte=date_to)
		pays = pays.filter(journal_entry__date__lte=date_to)
	bills = bills.order_by('date', 'id')
	pays = pays.order_by('journal_entry__date', 'journal_entry_id')

	bill_rows = []
	for b in bills:
		bill_rows.append({'obj': b, 'remaining': (b.total or Decimal('0')), 'allocated': Decimal('0')})
	payment_rows = []
	for it in pays:
		is_payment_model = SupplierPayment is not None and hasattr(it, 'amount') and hasattr(it, 'date') and not hasattr(it, 'journal_entry')
		payment_rows.append({  # type: ignore[arg-type]
			'obj': it,
			'amount': getattr(it, 'amount', getattr(it, 'amount', Decimal('0'))),
			'date': getattr(it, 'date', getattr(it, 'journal_entry', None).date if hasattr(it, 'journal_entry') else None),  # type: ignore[union-attr]
			'is_payment_model': is_payment_model,
		})
	for pay in payment_rows:
		amt = pay['amount']
		for br in bill_rows:
			if amt <= 0:
				break
			if br['remaining'] <= 0:
				continue
			take = min(br['remaining'], amt)
			br['remaining'] -= take
			br['allocated'] += take
			amt -= take
		pay['unallocated'] = amt

	timeline = []
	for br in bill_rows:
		b = br['obj']
		timeline.append({
			'type': 'bill',
			'date': b.date,
			'id': b.id,
			'number': getattr(b, 'number', ''),
			'debit': (b.total or Decimal('0')),
			'credit': None,
			'description': f'فاتورة شراء {getattr(b, "number", "")} ',
			'remaining': br['remaining'],
		})
	for pay in payment_rows:
		it = pay['obj']
		timeline.append({
			'type': 'payment',
			'date': pay['date'],
			'id': getattr(it, 'id', None),
			'number': getattr(it, 'receipt_number', getattr(getattr(it, 'journal_entry', None), 'number', '')),
			'debit': None,
			'credit': pay['amount'],
			'description': getattr(it, 'description', '') or 'دفعة مورد',
		})
	timeline.sort(key=lambda x: (x['date'], x['type'] == 'payment', x['id']))
	balance = opening_balance
	for row in timeline:
		if row['debit']:
			balance += row['debit']
		if row['credit']:
			balance -= row['credit']
		row['balance'] = balance

	cutoff = date_to or _date.today()
	aging = {k: Decimal('0') for k in ['bucket_0_30','bucket_31_60','bucket_61_90','bucket_90_plus']}
	for br in bill_rows:
		b = br['obj']
		if b.date > cutoff:
			continue
		remaining = br['remaining']
		if remaining <= 0:
			continue
		days = (cutoff - b.date).days
		if days <= 30:
			aging['bucket_0_30'] += remaining
		elif days <= 60:
			aging['bucket_31_60'] += remaining
		elif days <= 90:
			aging['bucket_61_90'] += remaining
		else:
			aging['bucket_90_plus'] += remaining
	aging['total'] = Decimal(str(sum(aging.values())))  # type: ignore[assignment]
	return {
		'timeline': timeline,
		'opening_balance': opening_balance,
		'balance': balance,
		'aging': aging,
		'date_from': date_from,
		'date_to': date_to,
	}


def _get_account_by_code_or_name(code: str, name_contains: str = ""):
	try:
		return Account.objects.get(code=code)
	except Account.DoesNotExist:
		if name_contains:
			acc = Account.objects.filter(name__icontains=name_contains, is_active=True).first()
			if acc:
				return acc
	return None


def post_supplier_payment_journal(payment, user=None):
	if SupplierPayment is None:
		raise ValueError("SupplierPayment model not available")
	if not isinstance(payment, SupplierPayment):  # type: ignore[arg-type]
		raise ValueError("payment must be SupplierPayment")
	settings = AccountingSettings.get()
	supplier_ap = getattr(payment.supplier, 'ap_account', None)
	ap_acc = supplier_ap or settings.ap_account or _get_account_by_code_or_name("2001", "المورد")
	cash_acc = settings.cash_account or _get_account_by_code_or_name("1001", "النقد") or _get_account_by_code_or_name("1002", "البنك")
	if not (ap_acc and cash_acc):
		raise ValueError("الحسابات الأساسية غير مكتملة للدفعة (AP أو Cash)")
	with transaction.atomic():
		je = JournalEntry.objects.create(
			date=getattr(payment.date, 'date', lambda: payment.date)() if hasattr(payment, 'date') else timezone.now().date(),
			entry_type='payment',
			description=f"دفعة مورد {payment.supplier.name} {getattr(payment, 'receipt_number', '')}",
			reference=getattr(payment, 'receipt_number', ''),
			purchase_bill=getattr(payment, 'bill', None),
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		JournalEntryItem.objects.create(journal_entry=je, account=ap_acc, type='debit', amount=payment.amount, description='تسوية دفعة')
		JournalEntryItem.objects.create(journal_entry=je, account=cash_acc, type='credit', amount=payment.amount, description='صرف نقدي')
		if je.total_debit == je.total_credit:
			je.is_posted = True
			je.save(update_fields=['is_posted'])
		return je


def post_purchase_bill_journal(bill, user=None):
	if PurchaseBill is None or not isinstance(bill, PurchaseBill):  # type: ignore[arg-type]
		raise ValueError("bill must be PurchaseBill")
	subtotal = sum([getattr(item, 'total', Decimal('0')) for item in bill.items.all()])  # type: ignore[attr-defined]
	net_total = Decimal(subtotal) - Decimal(getattr(bill, 'discount', 0) or 0)
	if net_total <= 0:
		return None
	settings = AccountingSettings.get()
	inv_acc = settings.inventory_account or _get_account_by_code_or_name("1004", "المخزون")
	supplier_ap = getattr(bill.supplier, 'ap_account', None)
	ap_acc = supplier_ap or settings.ap_account or _get_account_by_code_or_name("2001", "المورد")
	cash_acc = settings.cash_account or _get_account_by_code_or_name("1001", "النقدية") or _get_account_by_code_or_name("1002", "البنك")
	vat_input_acc = settings.vat_input_account
	if not (inv_acc and ap_acc):
		raise ValueError("الحسابات الأساسية غير مكتملة")
	with transaction.atomic():
		je = JournalEntry.objects.create(
			date=getattr(bill, 'date', timezone.now().date()) or timezone.now().date(),
			entry_type='purchase',
			description=f"فاتورة مشتريات {getattr(bill, 'number', '')} - {bill.supplier.name}",
			reference=getattr(bill, 'number', ''),
			purchase_bill=bill,  # type: ignore[arg-type]
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		base_amount = net_total
		vat_amount = Decimal('0')
		if settings.enable_vat and settings.default_vat_rate and vat_input_acc:
			vat_amount = (net_total * Decimal(settings.default_vat_rate)) / Decimal('100')
		if base_amount > 0:
			JournalEntryItem.objects.create(journal_entry=je, account=inv_acc, type='debit', amount=base_amount, description='مخزون')
		if vat_amount > 0:
			JournalEntryItem.objects.create(journal_entry=je, account=vat_input_acc, type='debit', amount=vat_amount, description='ضريبة مدخلات')
		ap_total = base_amount + vat_amount - Decimal(getattr(bill, 'paid', 0) or 0)
		if ap_total > 0:
			JournalEntryItem.objects.create(journal_entry=je, account=ap_acc, type='credit', amount=ap_total, description='دائنون')
		paid = Decimal(getattr(bill, 'paid', 0) or 0)
		if paid > 0 and cash_acc:
			JournalEntryItem.objects.create(journal_entry=je, account=ap_acc, type='debit', amount=paid, description='تسوية دفعة')
			JournalEntryItem.objects.create(journal_entry=je, account=cash_acc, type='credit', amount=paid, description='خزينة/بنك')
		if je.total_debit == je.total_credit:
			je.is_posted = True
			je.save(update_fields=["is_posted"])
		return je


def post_journal_entry(journal_entry: JournalEntry, force: bool = False):
	if journal_entry.is_posted:
		return journal_entry
	if not journal_entry.is_balanced and not force:
		raise ValidationError('لا يمكن ترحيل قيد غير متوازن')
	with transaction.atomic():
		journal_entry.is_posted = True
		journal_entry.save(update_fields=['is_posted'])
	return journal_entry


@lru_cache(maxsize=2048)
def _balance_db(account_id: int):
	qs = JournalEntryItem.objects.filter(account_id=account_id, journal_entry__is_posted=True)
	deb = qs.filter(type='debit').aggregate(s=Sum('amount'))['s'] or Decimal('0')
	crd = qs.filter(type='credit').aggregate(s=Sum('amount'))['s'] or Decimal('0')
	acc_type = Account.objects.only('account_type').get(id=account_id).account_type
	return deb - crd if acc_type in ['asset', 'expense'] else crd - deb


def get_account_balance_cached(account_id: int):
	key = BALANCE_CACHE_KEY.format(id=account_id)
	val = cache.get(key)
	if val is not None:
		return val
	val = _balance_db(account_id)
	cache.set(key, val, BALANCE_TIMEOUT)
	return val


def invalidate_account_balance(account_id: int):  # إعادة التعريف هنا أيضاً
	cache.delete(BALANCE_CACHE_KEY.format(id=account_id))
	_balance_db.cache_clear()


@dataclass
class TrialBalanceRow:
	code: str
	name: str
	level: int
	debit: Decimal
	credit: Decimal
	balance: Decimal
	is_group: bool


class AccountService:
	@staticmethod
	def build_tree() -> List[Dict[str, Any]]:
		# بناء الشجرة يدويًا دون الاعتماد على build_tree في المدير (لضمان العمل حتى لو لم يُحقن المدير).
		accounts = list(Account.objects.all().order_by('path', 'code').values(
			'id', 'code', 'name', 'level', 'is_group', 'can_post', 'account_type', 'parent_id'
		))
		nodes: Dict[int, Dict[str, Any]] = {}
		roots: List[Dict[str, Any]] = []
		for acc in accounts:
			acc_node = {
				'id': acc['id'],
				'code': acc['code'],
				'name': acc['name'],
				'level': acc['level'],
				'is_group': acc['is_group'],
				'can_post': acc['can_post'],
				'account_type': acc['account_type'],
				'children': []
			}
			nodes[acc['id']] = acc_node
		for acc in accounts:
			pid = acc['parent_id']
			if pid and pid in nodes:
				nodes[pid]['children'].append(nodes[acc['id']])
			else:
				roots.append(nodes[acc['id']])
		return roots

	@staticmethod
	def recalc_paths():
		for acc in Account.objects.all().order_by('code'):
			parent = acc.parent
			if parent:
				acc.level = (parent.level or 0) + 1
				parent_path = parent.path or parent.code
				acc.path = f"{parent_path}/{acc.code}"
			else:
				acc.level = 0
				acc.path = acc.code
			if acc.is_group and acc.can_post:
				acc.can_post = False
			acc.save(update_fields=['level', 'path', 'can_post'])

	@staticmethod
	def get_trial_balance(include_groups: bool = True) -> List[TrialBalanceRow]:
		rows: List[TrialBalanceRow] = []
		for acc in Account.objects.all().order_by('path'):
			items = JournalEntryItem.objects.filter(account=acc, journal_entry__is_posted=True)
			debits = items.aggregate(val=Sum('amount', filter=Q(type='debit')))['val'] or Decimal('0')
			credits = items.aggregate(val=Sum('amount', filter=Q(type='credit')))['val'] or Decimal('0')
			balance = debits - credits if acc.account_type in ['asset', 'expense'] else credits - debits
			if acc.is_group and include_groups:
				balance = acc.aggregate_balance()
			if acc.is_group and not include_groups:
				continue
			rows.append(TrialBalanceRow(
				code=acc.code,
				name=acc.name,
				level=acc.level,
				debit=debits,
				credit=credits,
				balance=balance,
				is_group=acc.is_group
			))
		return rows

	@staticmethod
	def quick_lookup(code: str) -> Optional[Account]:
		return Account.objects.filter(code=code).first()

__all__ = [
	'build_supplier_statement', 'post_supplier_payment_journal', 'post_purchase_bill_journal',
	'post_sales_invoice_journal', 'post_journal_entry', 'get_account_balance_cached', 'invalidate_account_balance',
	'TrialBalanceRow', 'AccountService'
]


def post_sales_invoice_journal(invoice, user=None):  # دمج الدالة هنا لتكون متاحة للاستيراد
	"""إنشاء قيد يومية لفاتورة مبيعات مع مراعاة سيناريوهات (نقدي كامل، آجل، جزئي) و VAT.

	المعاملات:
	- invoice: كائن الفاتورة (يتوقع وجود الخصم والمبلغ المدفوع والitems)
	- user: المستخدم الذي ينشئ القيد اختيارياً

	ملاحظات:
	- في حالة الدفع النقدي الكامل نتجنب إنشاء بند ذمم عملاء ثم تسويته فوراً.
	- في حالة الآجل الكامل ننشئ بند ذمم فقط.
	- في حالة الجزئي ننشئ ذمم بكامل صافي القيمة ثم نسجل التحصيل الجزئي.
	"""
	try:
		from sales.models import Invoice as SalesInvoice  # type: ignore
		from sales.models import InvoiceItem as SalesInvoiceItem  # noqa: F401
	except Exception:  # pragma: no cover
		SalesInvoice = None  # type: ignore
	if SalesInvoice is not None and not isinstance(invoice, SalesInvoice):  # type: ignore[arg-type]
		raise ValueError('invoice must be sales.models.Invoice')
	settings = AccountingSettings.get()
	# حسابات أساسية
	cash_acc = settings.cash_account or _get_account_by_code_or_name('1001', 'نقد') or _get_account_by_code_or_name('1002', 'بنك')
	ar_acc = getattr(settings, 'ar_account', None) or _get_account_by_code_or_name('1101', 'عملاء')
	vat_output_acc = settings.vat_output_account
	revenue_acc = _get_account_by_code_or_name('4000', 'مبيعات') or _get_account_by_code_or_name('4100', 'إيراد')
	if not revenue_acc:
		# إنشاء حساب إيرادات افتراضي عند أول استخدام في بيئات الاختبار / التطوير
		revenue_acc, _ = Account.objects.get_or_create(
			code='4000', defaults={'name': 'المبيعات', 'account_type': 'income'}
		)
	# اجمالي و صافي
	subtotal = sum([(getattr(it, 'quantity', 0) or 0) * (getattr(it, 'price', 0) or 0) for it in getattr(invoice, 'items', []).all()])  # type: ignore[attr-defined]
	discount = Decimal(getattr(invoice, 'discount', 0) or 0)
	base_total = Decimal(subtotal) - discount
	if base_total <= 0:
		return None
	vat_rate = Decimal(settings.default_vat_rate or 0)
	vat_amount = Decimal('0')
	if settings.enable_vat and vat_rate > 0 and vat_output_acc:
		vat_amount = (base_total * vat_rate) / Decimal('100')
	total_with_vat = base_total + vat_amount
	paid = Decimal(getattr(invoice, 'paid', 0) or 0)
	from datetime import date as _d
	from ..models import FiscalYear  # استيراد داخلي لتجنب الدوران في الأعلى
	with transaction.atomic():
		# تأكد من وجود سنة مالية تغطي التاريخ (تلقائي في بيئات الاختبار)
		entry_date = getattr(invoice, 'date', timezone.now().date()) or timezone.now().date()
		fy_exists = FiscalYear.objects.filter(start_date__lte=entry_date, end_date__gte=entry_date).exists()
		if not fy_exists:
			FiscalYear.objects.get_or_create(
				start_date=_d(entry_date.year, 1, 1),
				end_date=_d(entry_date.year, 12, 31),
				defaults={'name': f'FY{entry_date.year}', 'is_active': True, 'is_closed': False}
			)
		je = JournalEntry.objects.create(
			date=entry_date,
			entry_type='sales',
			description=f"فاتورة مبيعات {getattr(invoice, 'number', '')}",
			reference=getattr(invoice, 'number', ''),
			invoice=invoice,  # type: ignore[arg-type]
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		# الإيراد + الضريبة دائماً في جانب الدائن
		JournalEntryItem.objects.create(journal_entry=je, account=revenue_acc, type='credit', amount=base_total, description='إيراد مبيعات')
		if vat_amount > 0 and vat_output_acc:
			JournalEntryItem.objects.create(journal_entry=je, account=vat_output_acc, type='credit', amount=vat_amount, description='ضريبة مخرجات')
		# السيناريوهات
		if paid >= total_with_vat:  # نقدي كامل
			if cash_acc:
				JournalEntryItem.objects.create(journal_entry=je, account=cash_acc, type='debit', amount=total_with_vat, description='تحصيل نقدي')
		elif paid <= 0:  # آجل كامل
			if not ar_acc:
				raise ValueError('لا يوجد حساب ذمم عملاء متاح')
			JournalEntryItem.objects.create(journal_entry=je, account=ar_acc, type='debit', amount=total_with_vat, description='ذمم عملاء')
		else:  # جزئي
			if not ar_acc:
				raise ValueError('لا يوجد حساب ذمم عملاء متاح')
			JournalEntryItem.objects.create(journal_entry=je, account=ar_acc, type='debit', amount=total_with_vat, description='ذمم عملاء')
			if cash_acc:
				JournalEntryItem.objects.create(journal_entry=je, account=cash_acc, type='debit', amount=paid, description='تحصيل نقدي جزئي')
				JournalEntryItem.objects.create(journal_entry=je, account=ar_acc, type='credit', amount=paid, description='تسوية جزء ذمم')
		if je.total_debit == je.total_credit:
			je.is_posted = True
			je.save(update_fields=['is_posted'])
		return je

def post_customer_discount_journal(discount_note, user=None):
	"""إنشاء قيد محاسبي لخصم عميل (خصم مسموح به).
	
	القيد:
	- مدين: خصم مسموح به (مصروف)
	- دائن: ذمم العملاء (أصل)
	"""
	from sales.models_discount import CustomerDiscountNote
	
	if not isinstance(discount_note, CustomerDiscountNote):
		raise ValueError("discount_note must be CustomerDiscountNote")
	
	amount = discount_note.calculated_amount
	if not amount or amount <= 0:
		raise ValueError("مبلغ الخصم يجب أن يكون أكبر من صفر")
	
	settings = AccountingSettings.get()
	
	# حساب خصم مسموح به (مصروف)
	discount_expense_acc = _get_account_by_code_or_name("6005", "خصم مسموح") or \
						   _get_account_by_code_or_name("6006", "خصم مبيعات") or \
						   _get_account_by_code_or_name("4120", "خصم") or \
						   getattr(settings, 'sales_discount_account', None)
	
	# حساب ذمم العملاء
	customer_ar = getattr(discount_note.customer, 'ar_account', None) if discount_note.customer else None
	ar_acc = customer_ar or settings.ar_account or _get_account_by_code_or_name("1201", "العملاء") or \
			 _get_account_by_code_or_name("1101", "ذمم")
	
	if not ar_acc:
		raise ValueError("لا يوجد حساب ذمم عملاء متاح")
	
	# إذا لم يوجد حساب خصم، نستخدم حساب مصروفات عامة
	if not discount_expense_acc:
		discount_expense_acc = _get_account_by_code_or_name("6001", "مصروفات") or \
							   Account.objects.filter(account_type='expense', is_active=True, is_group=False).first()
	
	if not discount_expense_acc:
		raise ValueError("لا يوجد حساب خصم مسموح به أو مصروفات متاح")
	
	with transaction.atomic():
		je = JournalEntry.objects.create(
			date=discount_note.date,
			entry_type='adjustment',
			description=f"خصم مسموح به للعميل {discount_note.customer.name if discount_note.customer else ''} - {discount_note.number}",
			reference=discount_note.number,
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		# مدين: خصم مسموح به
		JournalEntryItem.objects.create(
			journal_entry=je,
			account=discount_expense_acc,
			type='debit',
			amount=amount,
			description=f'خصم مسموح به - {discount_note.get_reason_display()}'
		)
		# دائن: ذمم العملاء (تخفيض رصيد العميل)
		JournalEntryItem.objects.create(
			journal_entry=je,
			account=ar_acc,
			type='credit',
			amount=amount,
			description=f'تخفيض ذمم - خصم للعميل {discount_note.customer.name if discount_note.customer else ""}'
		)
		
		if je.total_debit == je.total_credit:
			je.is_posted = True
			je.save(update_fields=['is_posted'])
		
		return je


def post_supplier_discount_journal(discount_note, user=None):
	"""إنشاء قيد محاسبي لخصم مورد (خصم مكتسب).
	
	القيد:
	- مدين: ذمم الموردين (التزام) - تخفيض المديونية
	- دائن: خصم مكتسب (إيراد)
	"""
	from purchases.models_discount import SupplierDiscountNote
	
	if not isinstance(discount_note, SupplierDiscountNote):
		raise ValueError("discount_note must be SupplierDiscountNote")
	
	amount = discount_note.calculated_amount
	if not amount or amount <= 0:
		raise ValueError("مبلغ الخصم يجب أن يكون أكبر من صفر")
	
	settings = AccountingSettings.get()
	
	# حساب خصم مكتسب (إيراد)
	discount_revenue_acc = _get_account_by_code_or_name("4110", "خصم مكتسب") or \
						   _get_account_by_code_or_name("4120", "إيرادات أخرى") or \
						   getattr(settings, 'purchase_discount_account', None)
	
	# حساب ذمم الموردين (الدائنون)
	supplier_ap = getattr(discount_note.supplier, 'ap_account', None) if discount_note.supplier else None
	ap_acc = supplier_ap or settings.ap_account or _get_account_by_code_or_name("2001", "الموردين") or \
			 _get_account_by_code_or_name("2101", "الدائنون")
	
	if not ap_acc:
		raise ValueError("لا يوجد حساب ذمم موردين متاح")
	
	# إذا لم يوجد حساب خصم مكتسب، نستخدم حساب إيرادات أخرى
	if not discount_revenue_acc:
		discount_revenue_acc = _get_account_by_code_or_name("4001", "إيرادات") or \
							   Account.objects.filter(account_type='revenue', is_active=True, is_group=False).first()
	
	if not discount_revenue_acc:
		raise ValueError("لا يوجد حساب خصم مكتسب أو إيرادات متاح")
	
	with transaction.atomic():
		je = JournalEntry.objects.create(
			date=discount_note.date,
			entry_type='adjustment',
			description=f"خصم مكتسب من المورد {discount_note.supplier.name if discount_note.supplier else ''} - {discount_note.number}",
			reference=discount_note.number,
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		# مدين: ذمم الموردين (تخفيض المديونية للمورد)
		JournalEntryItem.objects.create(
			journal_entry=je,
			account=ap_acc,
			type='debit',
			amount=amount,
			description='تخفيض ذمم مورد - خصم مكتسب'
		)
		# دائن: خصم مكتسب (إيراد)
		JournalEntryItem.objects.create(
			journal_entry=je,
			account=discount_revenue_acc,
			type='credit',
			amount=amount,
			description=f'خصم مكتسب - {discount_note.get_reason_display()}'
		)
		
		if je.total_debit == je.total_credit:
			je.is_posted = True
			je.save(update_fields=['is_posted'])
		
		return je


def reverse_discount_journal(journal_entry, user=None):
	"""عكس قيد خصم (عند إلغاء الخصم)."""
	if not journal_entry or not journal_entry.is_posted:
		return None
	
	with transaction.atomic():
		# إنشاء قيد عكسي
		reverse_je = JournalEntry.objects.create(
			date=timezone.now().date(),
			entry_type='adjustment',
			description=f"عكس: {journal_entry.description}",
			reference=f"REV-{journal_entry.reference}",
			created_by=user if user and getattr(user, 'is_authenticated', False) else None,
			is_posted=False,
		)
		
		# عكس جميع بنود القيد الأصلي
		for item in journal_entry.items.all():
			reversed_type = 'credit' if item.type == 'debit' else 'debit'
			JournalEntryItem.objects.create(
				journal_entry=reverse_je,
				account=item.account,
				type=reversed_type,
				amount=item.amount,
				description=f'عكس: {item.description}'
			)
		
		if reverse_je.total_debit == reverse_je.total_credit:
			reverse_je.is_posted = True
			reverse_je.save(update_fields=['is_posted'])
		
		return reverse_je