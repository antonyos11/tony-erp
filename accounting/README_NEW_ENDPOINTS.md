# Accounting New Endpoints & Features

## Cash Transfer
- URL: `/accounting/cash/transfer`
- View: `cash_transfer_create`
- Permission: `accounting.add_journalentry`
- Creates a balanced journal entry (credit from_account / debit to_account)
- Optional immediate posting (`post_now` checkbox).

## Cash Positions
- URL: `/accounting/cash/positions` (HTML) / `?format=json`
- View: `cash_positions_view`
- Permission: `accounting.view_cashposition` (staff bypass)
- Aggregated using annotated sums; cached 30s.
- Filters: `prefix=`, `q=` (search code/name), `refresh=1` to bypass cache.

## Bank Reconciliation
- URL: `/accounting/bank/reconcile`
- View: `bank_reconcile_view`
- Permission: `accounting.reconcile_bank` (staff bypass)
- POST action: mark selected `BankTransaction` rows as reconciled.
- Placeholder model `BankTransaction` added if none existed.

## Supporting Model Added
```
BankTransaction(account, date, description, amount, is_reconciled, reference, created_at)
```

## Forms
- `CashTransferForm` in `accounting/forms.py`.

## Templates Added
- `accounting/cash_transfer_form.html`
- `accounting/cash_positions.html`
- `accounting/bank_reconcile.html`

## Future Enhancements (Suggested)
1. Enforce minimum balance / overdraft rules on from_account.
2. Add statement import (.csv) + auto-matching heuristics (amount/date window) for reconciliation.
3. Drill-down link from cash positions row -> filtered ledger.
4. Audit logging improvements (create specific AuditLog entries for transfers & reconciliations).
5. Add pagination to bank reconcile list.

## Quick Test Commands
Run server:
```
python manage.py runserver 127.0.0.1:8000 --noreload
```
Create transfer:
1. Open `/accounting/cash/transfer`
2. Fill form -> submit
3. Redirect goes to journal entry detail.

Reconcile sample (after creating some `BankTransaction` objects in shell):
```
python manage.py shell
>>> from accounting.models import BankTransaction, Account
>>> a = Account.objects.first()
>>> BankTransaction.objects.create(account=a, amount=150, description='Test deposit')
```
Visit `/accounting/bank/reconcile`, tick, press "وضع مسوّى".

---
Generated automatically. Update as logic evolves.
