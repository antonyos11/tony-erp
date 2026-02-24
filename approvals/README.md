# ✅ نظام الموافقات (Approvals)

## نظرة عامة
نظام موافقات متعدد المستويات لإدارة سير العمل والموافقة على المستندات والطلبات في Tony ERP.

## الميزات الرئيسية
- ✅ سير عمل متعدد المستويات
- ✅ موافقات متسلسلة ومتوازية
- ✅ إشعارات فورية للموافقين
- ✅ سجل تدقيق كامل
- ✅ تفويض الصلاحيات

## كيفية الاستخدام

### 1. إنشاء طلب موافقة
```python
from approvals.models import ApprovalRequest

request = ApprovalRequest.objects.create(
    content_object=purchase_order,
    workflow='purchase_approval',
    requested_by=user
)
```

### 2. الموافقة/الرفض
```python
request.approve(user=approver, comment='موافق')
# أو
request.reject(user=approver, reason='السعر مرتفع')
```

## النماذج (Models)
| النموذج | الوصف |
|---------|-------|
| `ApprovalRequest` | طلب الموافقة |
| `ApprovalAction` | إجراء الموافقة/الرفض |
| `ApprovalWorkflow` | تعريف سير العمل |
| `ApprovalLevel` | مستوى الموافقة |

## حالات الطلب
| الحالة | الوصف |
|--------|-------|
| `pending` | قيد الانتظار |
| `approved` | موافق عليه |
| `rejected` | مرفوض |
| `cancelled` | ملغي |

## API Endpoints
| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/approvals/` | GET | قائمة الطلبات |
| `/api/approvals/<id>/approve/` | POST | الموافقة |
| `/api/approvals/<id>/reject/` | POST | الرفض |
| `/api/approvals/pending/` | GET | الطلبات المعلقة |

## الصلاحيات
- `approvals.view_approval` - عرض الطلبات
- `approvals.approve_request` - الموافقة على الطلبات
- `approvals.reject_request` - رفض الطلبات

## التكامل
- **المشتريات**: موافقة أوامر الشراء
- **الإنتاج**: موافقة أوامر الإنتاج
- **HR**: موافقة طلبات الإجازات
- **المالية**: موافقة الصرفيات

---
**آخر تحديث**: ديسمبر 2025
