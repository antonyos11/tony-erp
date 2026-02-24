# TestSprite Fixes - Quick Reference Card

## Files Modified

### ✅ New Files Created
```
/var/www/tony_erp/api/test_views.py
/var/www/tony_erp/sales/services/accounting_integration.py
/var/www/tony_erp/TESTSPRITE_FIXES_IMPLEMENTATION.md
/var/www/tony_erp/TESTSPRITE_FIXES_SETUP_GUIDE.md
```

### ✅ Files Modified
```
/var/www/tony_erp/api_app/urls.py
/var/www/tony_erp/sales/models.py
/var/www/tony_erp/sales/views.py
/var/www/tony_erp/sales/urls.py
/var/www/tony_erp/crm/views.py
/var/www/tony_erp/production/services/inventory_integration.py
/var/www/tony_erp/production/services/production_lifecycle.py
/var/www/tony_erp/accountant_pro/settings.py
```

---

## Database Migrations

### Run Migrations
```bash
python3 manage.py migrate sales
```

### Migration Details
- **File:** `sales/migrations/0030_add_accounting_integration.py`
- **Changes:**
  - Added `Invoice.journal_entry` (ForeignKey to JournalEntry)
  - Added `Invoice.is_posted` (BooleanField)

---

## New API Endpoints

### Test Resources
```
GET    /api/resource/          - List test resources
GET    /api/resource/{id}/     - Get test resource
POST   /api/resource/          - Create test resource
PUT    /api/resource/{id}/     - Update test resource
DELETE /api/resource/{id}/     - Delete test resource
```

### Health Check
```
GET /api/health/               - API health status
```

### Authentication
- Basic Authentication: `username:password`
- Token Authentication: `Token <your-token>`

---

## New URLs

### Sales Module
```python
# Invoice Accounting
POST /sales/<int:pk>/post-accounting/
# Redirects to invoice_detail after posting
```

---

## New Settings

### Environment Variables (.env)
```bash
# Inventory Management
ALLOW_NEGATIVE_INVENTORY=0  # 0=prevent, 1=allow

# Existing settings (for reference)
DEBUG=0
ENVIRONMENT=production
ENTERPRISE_MODE=1
```

---

## New Services

### Accounting Integration
```python
from sales.services.accounting_integration import post_invoice_to_accounting

# Post invoice to accounting
je = post_invoice_to_accounting(invoice, user, description='...')

# Returns: JournalEntry object or None
```

### Usage Example
```python
from django.db import transaction

with transaction.atomic():
    je = post_invoice_to_accounting(invoice, request.user)
    if je:
        invoice.journal_entry = je
        invoice.is_posted = True
        invoice.save()
```

---

## Journal Entry Structure (Invoice Posting)

### Example Entry
```
Invoice: INV-202401-000123
Customer: ABC Company
Total: 1,140 LE (including 14% VAT)
Subtotal: 1,000 LE
Tax: 140 LE

Journal Entry:
DR  Accounts Receivable    1,140 LE
  CR  Sales Revenue        1,000 LE
  CR  VAT Payable            140 LE
```

### Accounts Required
1. **AR Account** (Debit): Customer receivables
2. **Sales Revenue Account** (Credit): Revenue from sales
3. **VAT Payable Account** (Credit): Tax collected (optional)

---

## Pagination Parameters

### URL Parameters
```
?page=1              # Page number (default: 1)
?page_size=50        # Items per page (25/50/100/200, default: 50)
```

### Template Context
```python
context = {
    'invoices': invoices_page,  # Paginated queryset
    'page_size': page_size,
}
```

### Template Usage
```django
{% for invoice in invoices %}
  <!-- invoice row -->
{% endfor %}

<div class="pagination">
  {% if invoices.has_previous %}
    <a href="?page={{ invoices.previous_page_number }}">السابق</a>
  {% endif %}
  
  صفحة {{ invoices.number }} من {{ invoices.paginator.num_pages }}
  
  {% if invoices.has_next %}
    <a href="?page={{ invoices.next_page_number }}">التالي</a>
  {% endif %}
</div>
```

---

## Negative Inventory Validation

### In Signal Handler
```python
from django.conf import settings

allow_negative = getattr(settings, 'ALLOW_NEGATIVE_INVENTORY', False)

if not allow_negative and current_qty < required_qty:
    raise ValueError(
        f'الكمية المتوفرة في المخزن غير كافية. '
        f'المتاح: {current_qty}، المطلوب: {required_qty}'
    )
```

### Error Handling in Views
```python
try:
    invoice_item = InvoiceItem.objects.create(...)
except ValueError as e:
    messages.error(request, str(e))
    return redirect(...)
```

---

## CRM Workflow - Data Inheritance

### Opportunity → Quotation
```python
# In quotation_create view
if opportunity_id:
    opportunity = Opportunity.objects.get(pk=opportunity_id)
    form.fields['customer'].initial = opportunity.customer.id
    form.fields['contact_person'].initial = opportunity.contact_person.id
    form.initial['subtotal'] = opportunity.estimated_value
    form.fields['valid_until'].initial = opportunity.expected_close_date
    form.initial['notes'] = opportunity.description
```

### Quotation → Invoice
```python
# In quotation_convert_to_invoice view
invoice = Invoice.objects.create(
    customer=quotation.customer,
    date=timezone.now().date(),
    due_date=quotation.valid_until,
    discount=quotation.discount_amount,
    is_tax_inclusive=True if quotation.tax_amount > 0 else False,
)

# Copy items
for q_item in quotation.items.all():
    InvoiceItem.objects.create(
        invoice=invoice,
        product=q_item.product,
        quantity=int(q_item.quantity),
        price=q_item.unit_price,
    )

# Update opportunity
if quotation.opportunity:
    won_stage = OpportunityStage.objects.filter(is_won=True).first()
    quotation.opportunity.stage = won_stage
    quotation.opportunity.probability = 100
    quotation.opportunity.closed_at = timezone.now()
    quotation.opportunity.save()
```

---

## Production Workflow Improvements

### Error Handling in Material Issue
```python
for item in bom_items:
    try:
        issue_item = IssueItem.objects.create(...)
        MaterialConsumption.objects.create(...)
    except Exception as e:
        logger.error(f"Error: {e}")
        continue  # Continue with other items
```

### Explicit Status Updates
```python
production_order.status = 'in_progress'
production_order.actual_start_date = timezone.now()
production_order.save(update_fields=['status', 'actual_start_date'])
# ✓ Uses update_fields to ensure save
```

---

## Testing Commands

### API Testing
```bash
# Test authentication
curl -u admin:password http://localhost:8000/api/resource/

# Test health endpoint
curl http://localhost:8000/api/health/

# Expected response
{"status": "ok", "message": "API is working"}
```

### Database Testing
```bash
# Check migrations
python3 manage.py showmigrations sales

# Test invoice posting
python3 manage.py shell
>>> from sales.models import Invoice
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> invoice = Invoice.objects.first()
>>> user = User.objects.first()
>>> from sales.services.accounting_integration import post_invoice_to_accounting
>>> je = post_invoice_to_accounting(invoice, user)
>>> print(je.id)
```

---

## Common Issues & Solutions

### Issue: "لم يتم ضبط حساب العملاء"
**Solution:** Go to Settings → Accounting Settings → Set AR Account

### Issue: Migration failed
**Solution:**
```bash
python3 manage.py migrate sales --fake-initial
```

### Issue: API returns 401
**Solution:** Check authentication in request:
```bash
curl -u username:password ...
```

### Issue: Negative inventory still allowed
**Solution:** 
1. Check `.env` has `ALLOW_NEGATIVE_INVENTORY=0`
2. Restart server: `sudo systemctl restart gunicorn`

---

## Performance Optimization

### Query Optimization
```python
# Before (N+1 queries)
invoices = Invoice.objects.all()

# After (optimized)
invoices = Invoice.objects.select_related(
    'customer', 'payment_method'
).prefetch_related('items')
```

### Pagination Best Practices
- Use 50 items per page for balance
- Add `order_by()` for consistent pagination
- Use `Paginator.count` for total count

---

## Rollback Instructions

### Quick Rollback
```bash
# Rollback migration
python3 manage.py migrate sales 0029

# Restore files from git
git checkout HEAD -- sales/views.py sales/models.py crm/views.py

# Restart server
sudo systemctl restart gunicorn
```

---

**Version:** 1.0  
**Last Updated:** 2024-01-20  
**For:** Django 5.x, Python 3.10+
