# 🛒 WooCommerce Integration

## نظرة عامة
وحدة التكامل مع WooCommerce لمزامنة المنتجات والطلبات والعملاء بين نظام Tony ERP ومتجر WooCommerce.

## الميزات الرئيسية
- ✅ مزامنة المنتجات ثنائية الاتجاه
- ✅ استيراد الطلبات تلقائياً
- ✅ مزامنة العملاء
- ✅ تحديث المخزون في الوقت الفعلي
- ✅ إشعارات بالطلبات الجديدة

## الإعداد

### 1. إعدادات WooCommerce
```python
# في لوحة الإعدادات
WOOCOMMERCE_URL = 'https://your-store.com'
WOOCOMMERCE_KEY = 'ck_xxxxx'
WOOCOMMERCE_SECRET = 'cs_xxxxx'
```

### 2. تفعيل المزامنة
```bash
python manage.py sync_woo_products
python manage.py sync_woo_orders
```

## النماذج (Models)
| النموذج | الوصف |
|---------|-------|
| `WooCommerceConfig` | إعدادات الاتصال |
| `ProductMapping` | ربط المنتجات |
| `CustomerMapping` | ربط العملاء |
| `OrderSync` | سجل مزامنة الطلبات |

## API Endpoints
| Endpoint | Method | الوصف |
|----------|--------|-------|
| `/api/woo/sync/products/` | POST | مزامنة المنتجات |
| `/api/woo/sync/orders/` | POST | مزامنة الطلبات |
| `/api/woo/webhook/` | POST | استقبال Webhooks |

## الصلاحيات
- `woocommerce_integration.view_config` - عرض الإعدادات
- `woocommerce_integration.sync_products` - مزامنة المنتجات
- `woocommerce_integration.sync_orders` - مزامنة الطلبات

## استكشاف الأخطاء
1. **فشل الاتصال**: تحقق من Consumer Key/Secret
2. **منتج غير موجود**: تحقق من ربط SKU
3. **طلب مكرر**: راجع سجل المزامنة

---
**آخر تحديث**: ديسمبر 2025
