# RITA ERP — دليل البنية

## نوع المشروع
نظام ERP صناعي متكامل لمصنع مراتب ومفروشات

## التقنيات
- Django 5.2 + Python 3.12
- PostgreSQL
- Bootstrap 5 RTL

## Settings
- التطوير: config.settings.development (SQLite)
- الإنتاج: config.settings.production (PostgreSQL)
- المتغير: DJANGO_ENV=development أو production

## التطبيقات (Phase 1)
| التطبيق | الوصف |
|---------|-------|
| apps.core | النواة + المستخدمين + الفروع + المخازن |
| apps.accounts | المحاسبة + القيود + دليل الحسابات |
| apps.inventory | المخزون + المنتجات + BOM |
| apps.production | الإنتاج + أوامر التصنيع |
| apps.sales | المبيعات + الفواتير + العملاء |
| apps.partners | الموردين |

## قواعد التطوير
1. كل Model يرث من AuditMixin (إلا المذكور)
2. كل verbose_name بالعربي
3. كل view محمي بـ login_required
4. لا تعديل على migrations يدوياً
5. قيد واحد لكل عملية — لا تجميع
