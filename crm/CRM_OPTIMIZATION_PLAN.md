# خطة تحسين أداء نظام CRM

## 🎯 الهدف
تحسين أداء نظام CRM وتسريع الاستعلامات وتقليل استهلاك الموارد

## 📊 التحسينات المقترحة

### 1. تحسين استعلامات قاعدة البيانات

#### أ. إضافة select_related و prefetch_related
```python
# في crm/views.py - customer_list
customers = Customer.objects.select_related(
    'customer_type', 
    'source', 
    'assigned_to'
).prefetch_related(
    'contacts',
    'opportunity_set',
    'activity_set'
)

# في crm/views.py - opportunity_list
opportunities = Opportunity.objects.select_related(
    'customer',
    'stage',
    'assigned_to',
    'contact_person'
).prefetch_related(
    'activity_set'
)

# في crm/views.py - activity_list
activities = Activity.objects.select_related(
    'customer',
    'opportunity',
    'activity_type',
    'assigned_to',
    'contact_person'
)
```

#### ب. إضافة Indexes إضافية
```python
# في crm/models.py - Customer
class Meta:
    indexes = [
        models.Index(fields=['status', 'created_at']),
        models.Index(fields=['assigned_to', 'status']),
        models.Index(fields=['customer_type', 'status']),
        models.Index(fields=['source', 'created_at']),
    ]

# في crm/models.py - Opportunity
class Meta:
    indexes = [
        models.Index(fields=['stage', 'expected_close_date']),
        models.Index(fields=['assigned_to', 'stage']),
        models.Index(fields=['customer', 'stage']),
        models.Index(fields=['priority', 'expected_close_date']),
    ]

# في crm/models.py - Activity
class Meta:
    indexes = [
        models.Index(fields=['status', 'scheduled_date']),
        models.Index(fields=['assigned_to', 'status']),
        models.Index(fields=['customer', 'scheduled_date']),
        models.Index(fields=['opportunity', 'scheduled_date']),
    ]
```

### 2. إضافة Caching

#### أ. Cache للإحصائيات
```python
from django.core.cache import cache

@login_required
def dashboard(request):
    # Cache key
    cache_key = f'crm_dashboard_stats_{request.user.id}'
    stats = cache.get(cache_key)
    
    if not stats:
        stats = {
            'total_customers': Customer.objects.count(),
            'active_customers': Customer.objects.filter(status='active').count(),
            'open_opportunities': Opportunity.objects.filter(
                stage__is_won=False, stage__is_lost=False
            ).count(),
            'open_tickets': SupportTicket.objects.filter(
                status__in=['open', 'in_progress']
            ).count(),
        }
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
    
    # ... rest of the code
```

#### ب. Cache للقوائم الثابتة
```python
# Cache customer types, sources, stages
customer_types = cache.get_or_set(
    'crm_customer_types',
    lambda: list(CustomerType.objects.all()),
    3600  # 1 hour
)

opportunity_stages = cache.get_or_set(
    'crm_opportunity_stages',
    lambda: list(OpportunityStage.objects.all().order_by('order')),
    3600
)
```

### 3. تحسين API Endpoints

#### أ. إضافة Pagination
```python
# في api/crm_views.py
from rest_framework.pagination import PageNumberPagination

class CRMPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class CustomerViewSet(viewsets.ModelViewSet):
    pagination_class = CRMPagination
    # ... rest of the code
```

#### ب. إضافة Filtering و Ordering
```python
from django_filters import rest_framework as filters

class CustomerFilter(filters.FilterSet):
    status = filters.CharFilter()
    customer_type = filters.NumberFilter()
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Customer
        fields = ['status', 'customer_type', 'source']

class CustomerViewSet(viewsets.ModelViewSet):
    filterset_class = CustomerFilter
    ordering_fields = ['created_at', 'first_name', 'last_name']
    ordering = ['-created_at']
```

### 4. تحسين النماذج (Forms)

#### أ. استخدام Select2 للقوائم الطويلة
```python
# في crm/forms.py
from django_select2.forms import Select2Widget

class OpportunityForm(forms.ModelForm):
    class Meta:
        widgets = {
            'customer': Select2Widget,
            'assigned_to': Select2Widget,
            'contact_person': Select2Widget,
        }
```

## 📝 خطوات التنفيذ

1. ✅ إضافة Indexes للنماذج
2. ⏳ تحديث Views لاستخدام select_related
3. ⏳ إضافة Caching للإحصائيات
4. ⏳ تحسين API Endpoints
5. ⏳ اختبار الأداء
6. ⏳ قياس التحسينات

## 🎉 النتائج المتوقعة

- تحسين سرعة تحميل الصفحات بنسبة 50-70%
- تقليل عدد استعلامات قاعدة البيانات بنسبة 60-80%
- تحسين تجربة المستخدم بشكل ملحوظ

