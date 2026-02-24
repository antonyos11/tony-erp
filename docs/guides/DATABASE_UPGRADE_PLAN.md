# خطة تطوير وتحديث قاعدة البيانات - Tony ERP

## نظرة عامة على النظام الحالي

### إحصائيات النظام:
- **إجمالي النماذج**: 307 نموذج
- **عدد التطبيقات**: 28 تطبيق
- **قاعدة البيانات الحالية**: SQLite3

### توزيع النماذج حسب التطبيق:
| التطبيق | عدد النماذج | الوصف |
|---------|------------|-------|
| hr | 37 | الموارد البشرية |
| crm | 37 | إدارة علاقات العملاء |
| accounting | 27 | المحاسبة |
| purchases | 22 | المشتريات |
| production | 17 | الإنتاج |
| inventory | 16 | المخزون |
| showrooms | 12 | المعارض |
| sales | 11 | المبيعات |
| core | 10 | الإعدادات الأساسية |
| maintenance | 10 | الصيانة |
| reports | 8 | التقارير |
| fleet | 8 | الأسطول |
| users | 7 | المستخدمين |
| payments | 5 | المدفوعات |
| partners | 4 | الشركاء |
| pos | 4 | نقطة البيع |

---

## التحسينات المقترحة

### 1. تحسينات الأداء (Performance Optimizations)

#### 1.1 إضافة فهارس للحقول الأكثر استخداماً
```python
# accounting/models.py
class JournalEntry:
    class Meta:
        indexes = [
            models.Index(fields=['date', 'is_posted']),
            models.Index(fields=['entry_type', 'date']),
            models.Index(fields=['created_by', 'date']),
        ]

# sales/models.py
class Invoice:
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['due_date', 'paid']),
        ]
```

#### 1.2 تحسين الاستعلامات المتكررة
- استخدام `select_related()` و `prefetch_related()` للعلاقات
- إضافة كاش للبيانات الثابتة (العملات، الإعدادات)
- تحسين aggregate queries

### 2. تحسينات البنية (Structural Improvements)

#### 2.1 توحيد الحقول المشتركة
إنشاء نموذج أساسي مشترك للحقول المتكررة:

```python
class BaseAuditModel(models.Model):
    """نموذج أساسي للتتبع"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    """نموذج للحذف الناعم"""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    delete_reason = models.TextField(blank=True)
    
    class Meta:
        abstract = True
```

#### 2.2 إضافة حقول تكامل مفقودة
- ربط الفروع بجميع العمليات
- إضافة حقل العملة لجميع المستندات المالية
- توحيد معرف المستخدم المسؤول

### 3. تحسينات التكامل بين الوحدات

#### 3.1 المحاسبة والمخزون
- ربط حركات المخزون بالقيود المحاسبية تلقائياً
- تتبع تكلفة البضاعة المباعة (COGS)

#### 3.2 الموارد البشرية والرواتب
- ربط الرواتب بالقيود المحاسبية
- تكامل الحضور مع حساب الأجور

#### 3.3 الإنتاج والمخزون
- خصم المواد الخام تلقائياً
- إضافة المنتجات التامة للمخزون

### 4. تحسينات الأمان

#### 4.1 سجل التدقيق الشامل
```python
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'إنشاء'),
        ('update', 'تحديث'),
        ('delete', 'حذف'),
        ('view', 'عرض'),
        ('export', 'تصدير'),
        ('print', 'طباعة'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField()
    ip_address = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
```

### 5. دعم متعدد الفروع والعملات

#### 5.1 نظام الفروع المتقدم
- كل فرع له مخازنه الخاصة
- تقارير منفصلة لكل فرع
- صلاحيات على مستوى الفرع

#### 5.2 نظام العملات المتعدد
- تحويل تلقائي بين العملات
- تتبع فروقات سعر الصرف
- تقارير بالعملة المحلية والأجنبية

---

## خطة التنفيذ المرحلية

### المرحلة 1: تحسينات الأداء الفورية (أسبوع 1)
1. ✅ إضافة الفهارس المفقودة
2. ✅ تحسين الاستعلامات البطيئة
3. ✅ إضافة التخزين المؤقت

### المرحلة 2: تحسينات البنية (أسبوع 2-3)
1. إنشاء النماذج الأساسية المشتركة
2. توحيد الحقول المتكررة
3. إضافة الحقول المفقودة

### المرحلة 3: التكامل (أسبوع 4-5)
1. ربط الوحدات ببعضها
2. إضافة المشغلات التلقائية
3. تحسين سير العمل

### المرحلة 4: الأمان والتدقيق (أسبوع 6)
1. تفعيل سجل التدقيق الشامل
2. تحسين الصلاحيات
3. إضافة التشفير للبيانات الحساسة

---

## الهجرات المطلوبة

سيتم إنشاء الهجرات التالية:
1. `core_add_base_models` - إضافة النماذج الأساسية
2. `core_add_indexes` - إضافة الفهارس
3. `accounting_add_multicurrency` - دعم العملات المتعددة
4. `inventory_add_branch_support` - دعم الفروع للمخزون
5. `sales_add_audit_fields` - حقول التدقيق للمبيعات

---

## ملاحظات هامة

1. **النسخ الاحتياطي**: يجب عمل نسخة احتياطية قبل أي تحديث
2. **الاختبار**: اختبار شامل قبل النشر
3. **التوثيق**: توثيق جميع التغييرات
4. **التوافق**: الحفاظ على التوافق مع الإصدارات السابقة

---

## الأوامر المطلوبة للتنفيذ

```bash
# نسخة احتياطية
python manage.py backup_now

# إنشاء الهجرات
python manage.py makemigrations

# تطبيق الهجرات
python manage.py migrate

# فحص النظام
python manage.py system_self_check
```

---

**تاريخ الإنشاء**: ديسمبر 2025
**الإصدار**: 1.0
