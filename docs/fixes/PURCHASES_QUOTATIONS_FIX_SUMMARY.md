# Purchases Quotations Module - Fix Summary

## Problem
The purchases quotations page (`/purchases/quotations/`) was returning a Server Error (500).

## Root Causes Identified and Fixed

### 1. **Missing Context Variables in View**
- **Issue**: The `quotation_list` view was not providing the `rfqs` variable to the template
- **Fix**: Added `rfqs = RFQ.objects.all()` to the view context in `purchases/views_advanced.py`

### 2. **Template Using Non-existent Variable**
- **Issue**: Template was using `object_list` which was not provided by the view
- **Locations Fixed**:
  - Line 97: Changed `{% for quote in quotations|default:object_list %}` to `{% for quote in quotations %}`
  - Line 78: Changed `{{ quotations|length|default:object_list|length }}` to `{{ quotations|length }}`

### 3. **Invalid URL References**
- **Issue**: Template was trying to use non-existent URL patterns
- **Fixes**:
  - Removed reference to `quotation_create` without `rfq_id` parameter
  - Removed references to non-existent views: `quotation_convert`, `quotation_edit`, `quotation_print`
  - Updated empty state to only show `rfq_create` button

### 4. **Incorrect Field Names**
- **Issue**: Template was using wrong field names from the model
- **Fixes**:
  - Changed `quote.date` to `quote.quotation_date`
  - Changed `quote.quotation_number` to `quote.number`
  - Changed `quote.rfq.rfq_number` to `quote.rfq.number`
  - Changed `quote.items_count` to `quote.items.count`

### 5. **Incorrect Status Values**
- **Issue**: Template was using status values that don't exist in the model
- **Fixes**:
  - Updated status filter options to match model choices:
    - `draft` → `draft`
    - `pending` → `submitted`, `under_review`
    - `accepted` → `accepted`
    - `rejected` → `rejected`
    - `converted` → removed (not in model)
    - Added `expired` status

## Files Modified

1. **`purchases/views_advanced.py`**
   - Added `rfqs = RFQ.objects.all()` to quotation_list view context

2. **`templates/purchases/quotation/list.html`**
   - Fixed template variable references
   - Removed invalid URL patterns
   - Updated status filter options
   - Fixed field name references
   - Simplified empty state

## Verification

✓ Quotations list page loads successfully (HTTP 200)
✓ All context variables are provided correctly
✓ Template renders without errors
✓ No missing URL patterns
✓ All field references are correct

## Testing

Run the following to verify:
```bash
python manage.py shell -c "
from django.test import Client
from django.contrib.auth.models import User

user, _ = User.objects.get_or_create(
    username='testuser',
    defaults={'is_staff': True, 'is_superuser': True}
)
user.set_password('testpass123')
user.save()

client = Client()
client.login(username='testuser', password='testpass123')
response = client.get('/purchases/quotations/')
print(f'Status: {response.status_code}')
"
```

Expected output: `Status: 200`

