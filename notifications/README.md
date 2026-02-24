# 🔔 نظام الإشعارات (Notifications)

## نظرة عامة
نظام إشعارات متكامل لإرسال التنبيهات للمستخدمين عبر قنوات متعددة في Tony ERP.

## الميزات الرئيسية
- ✅ إشعارات داخل التطبيق (In-App)
- ✅ إشعارات البريد الإلكتروني
- ✅ إشعارات فورية (WebSocket)
- ✅ قوالب إشعارات قابلة للتخصيص
- ✅ تفضيلات المستخدم
- ✅ سجل الإشعارات

## أنواع الإشعارات
| النوع | الوصف |
|-------|-------|
| `info` | معلومة |
| `success` | نجاح |
| `warning` | تحذير |
| `error` | خطأ |
| `action` | يتطلب إجراء |

## كيفية الاستخدام

### 1. إرسال إشعار بسيط
```python
from notifications.services import send_notification

send_notification(
    user=user,
    title='طلب جديد',
    message='تم استلام طلب شراء جديد',
    notification_type='info'
)
```

### 2. إشعار مع رابط
```python
send_notification(
    user=user,
    title='موافقة مطلوبة',
    message='طلب شراء ينتظر موافقتك',
    notification_type='action',
    action_url='/purchases/orders/123/'
)
```

### 3. إشعار جماعي
```python
from notifications.services import broadcast_notification

broadcast_notification(
    users=User.objects.filter(role='manager'),
    title='تقرير شهري',
    message='التقرير الشهري جاهز للمراجعة'
)
```

## النماذج (Models)
| النموذج | الوصف |
|---------|-------|
| `Notification` | الإشعار |
| `NotificationTemplate` | قالب الإشعار |
| `UserNotificationPreference` | تفضيلات المستخدم |

## API Endpoints
| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/notifications/` | GET | قائمة الإشعارات |
| `/api/notifications/unread/` | GET | غير المقروءة |
| `/api/notifications/<id>/read/` | POST | تحديد كمقروء |
| `/api/notifications/mark-all-read/` | POST | تحديد الكل كمقروء |
| `/api/notifications/preferences/` | GET/PUT | التفضيلات |

## WebSocket
```javascript
// الاتصال
const ws = new WebSocket('ws://localhost:8000/ws/notifications/');

ws.onmessage = function(e) {
    const notification = JSON.parse(e.data);
    showNotification(notification);
};
```

## الإعدادات
```python
# settings.py
NOTIFICATION_SETTINGS = {
    'EMAIL_ENABLED': True,
    'WEBSOCKET_ENABLED': True,
    'MAX_NOTIFICATIONS_PER_USER': 100,
    'RETENTION_DAYS': 30,
}
```

## التكامل
- 📦 **المخزون**: تنبيه انخفاض المخزون
- 💰 **المبيعات**: إشعار بيع جديد
- 👥 **HR**: تذكير بالإجازات
- ✅ **الموافقات**: طلب موافقة جديد

---
**آخر تحديث**: ديسمبر 2025
