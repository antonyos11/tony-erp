# 🛏️ نظام بناء المراتب المخصصة - Custom Mattress Builder

## 📋 نظرة عامة

نظام تفاعلي متقدم يمكّن العملاء من تصميم مراتبهم الخاصة بطريقة ممتعة تشبه الألعاب، مع معاينة فورية ونظام اقتراحات ذكي وحساب تلقائي للأسعار.

---

## ✨ الميزات الرئيسية

### 1. 🎨 الواجهة التفاعلية
- **معاينة مرئية فورية** - شاهد مرتبتك وهي تُبنى طبقة بطبقة
- **تصميم 2.5D متحرك** - رسوم متحركة سلسة وجذابة
- **واجهة سهلة** - تجربة بسيطة ومباشرة

### 2. 🧩 نظام المكونات الذكي
- **6 فئات رئيسية**:
  - السوست (جيوب منفصلة، متصلة)
  - الإسفنج (ميموري فوم، عالي المرونة، قياسي)
  - القماش الخارجي (مضاد للبكتيريا، قطني)
  - طبقات الراحة
  - أنظمة التبريد (جل التبريد)
  - القاعدة

- **مواصفات تفصيلية**:
  - السماكة والكثافة
  - مستوى الجودة (أساسي، قياسي، ممتاز، فاخر)
  - الفوائد والميزات

### 3. 💰 نظام تسعير ذكي
- **حساب فوري** للسعر مع كل تغيير
- **3 أنواع تسعير**:
  - ثابت
  - حسب المساحة
  - مركب (ثابت + مساحة)
- **تحليل مفصل** للتكلفة

### 4. 🎯 نظام الاقتراحات
- اقتراحات ذكية بناءً على:
  - الاختيارات الحالية
  - الميزانية
  - التفضيلات
  - الشعبية

### 5. 📐 أحجام متنوعة
- مفرد (90×190 سم)
- نفر ونص (120×190 سم)
- مزدوج (140×190 سم)
- كوين (160×200 سم)
- كينج (180×200 سم)
- سوبر كينج (200×200 سم)

### 6. ✅ نظام الموافقات
- **للعملاء**:
  - حفظ كمسودة
  - إرسال للموافقة
  - تتبع الحالة

- **للإدارة**:
  - مراجعة التصميمات
  - الموافقة/الرفض
  - إضافة ملاحظات
  - تحويل للإنتاج

---

## 🚀 التثبيت والإعداد

### المتطلبات الأساسية
```bash
# تم التثبيت بالفعل ✅
- Django 4.x
- Django REST Framework
- PostgreSQL/SQLite
```

### التفعيل
النظام مفعل ومجهز تلقائياً! ✨

---

## 📖 دليل الاستخدام

### للعملاء

#### 1. الوصول للنظام
```
المتجر الإلكتروني → بناء مرتبة مخصصة
أو مباشرة: /mattress-builder/builder/
```

#### 2. بناء المرتبة
1. **اختر الحجم** 📏
   - حدد حجم المرتبة المناسب
   - شاهد السعر الأساسي

2. **اختر القاعدة** 🏗️
   - قاعدة إسفنج مضغوط (مطلوب)

3. **اختر السوست** 🔄
   - سوست جيوب منفصلة (فاخر) 
   - سوست متصلة (قياسي)

4. **أضف الإسفنج** 🌊
   - ميموري فوم (راحة استثنائية)
   - إسفنج عالي المرونة
   - إسفنج قياسي

5. **اختر القماش** 👕
   - قماش مضاد للبكتيريا
   - قماش قطني فاخر

6. **إضافات اختيارية** ❄️
   - جل التبريد
   - طبقات راحة إضافية

#### 3. إتمام الطلب
```
مراجعة التصميم → إضافة ملاحظات → إرسال للموافقة
```

---

### للإدارة

#### 1. الدخول للوحة التحكم
```
/admin/ → Mattress Builder
```

#### 2. إدارة المكونات

**إضافة مكون جديد:**
```
المكونات → إضافة مكون
- اسم المكون
- الفئة
- التسعير
- المواصفات
- الصورة
- الفوائد
```

**إعداد القواعد:**
- قواعد التوافق
- قواعد التسعير
- قواعد الاقتراحات

#### 3. إدارة الطلبات

**قائمة الطلبات:**
```
التصميمات المخصصة → فلترة حسب الحالة
- مسودة
- في انتظار الموافقة ⏳
- موافق عليه ✅
- مرفوض ❌
- تحت الإنتاج 🏭
- مكتمل ✓
```

**الموافقة على طلب:**
```
1. فتح التصميم
2. مراجعة التفاصيل
3. فحص السعر
4. اختيار:
   - موافقة ✅
   - رفض (مع السبب) ❌
```

---

## 🔌 APIs المتاحة

### نقاط النهاية الرئيسية

#### الأحجام
```http
GET /mattress-builder/api/sizes/
```

#### الفئات
```http
GET /mattress-builder/api/categories/
GET /mattress-builder/api/categories/{id}/components/
```

#### المكونات
```http
GET /mattress-builder/api/components/
GET /mattress-builder/api/components/?category={id}
GET /mattress-builder/api/components/?featured=true
POST /mattress-builder/api/components/{id}/calculate_price/
{
  "size_id": 3
}
```

#### التصميمات
```http
# إنشاء تصميم جديد
POST /mattress-builder/api/designs/
{
  "design_name": "مرتبتي المريحة",
  "mattress_size": 3,
  "notes": "أريد مرتبة مريحة جداً"
}

# عرض تصميماتي
GET /mattress-builder/api/designs/

# إضافة مكون
POST /mattress-builder/api/designs/{id}/add_component/
{
  "component_id": 5,
  "quantity": 1,
  "layer_position": 2
}

# حذف مكون
POST /mattress-builder/api/designs/{id}/remove_component/
{
  "design_component_id": 10
}

# إرسال للموافقة
POST /mattress-builder/api/designs/{id}/submit_for_approval/

# حساب السعر
POST /mattress-builder/api/designs/calculate_price/
{
  "mattress_size_id": 3,
  "component_ids": [1, 3, 5, 7]
}

# الحصول على اقتراحات
POST /mattress-builder/api/designs/get_recommendations/
{
  "design_data": {...},
  "mattress_size_id": 3,
  "selected_component_ids": [1, 3]
}
```

#### القوالب
```http
GET /mattress-builder/api/templates/
GET /mattress-builder/api/templates/?featured=true
POST /mattress-builder/api/templates/{id}/use_template/
```

---

## 🎨 مثال عملي كامل

### سيناريو: العميل يريد مرتبة كينج فاخرة

```python
# 1. اختيار الحجم (كينج)
size = MattressSize.objects.get(name='كينج')
design = CustomMattressDesign.objects.create(
    customer=request.user,
    design_name="مرتبة النوم الفاخرة",
    mattress_size=size
)

# 2. إضافة القاعدة
base = MattressComponent.objects.get(name__contains='قاعدة')
DesignComponent.objects.create(
    design=design,
    component=base,
    layer_position=1
)

# 3. إضافة السوست
springs = MattressComponent.objects.get(name__contains='جيوب منفصلة')
DesignComponent.objects.create(
    design=design,
    component=springs,
    layer_position=2
)

# 4. إضافة الإسفنج
memory_foam = MattressComponent.objects.get(name__contains='ميموري فوم')
DesignComponent.objects.create(
    design=design,
    component=memory_foam,
    layer_position=3
)

# 5. إضافة جل التبريد
cooling = MattressComponent.objects.get(name__contains='جل التبريد')
DesignComponent.objects.create(
    design=design,
    component=cooling,
    layer_position=4
)

# 6. إضافة القماش
fabric = MattressComponent.objects.get(name__contains='مضاد للبكتيريا')
DesignComponent.objects.create(
    design=design,
    component=fabric,
    layer_position=5
)

# 7. حساب السعر النهائي
total = design.calculate_total_price()
# السعر النهائي: ~3,150 ج.م

# 8. إرسال للموافقة
design.submit_for_approval()
```

---

## 📊 لوحة التحكم

### إحصائيات متاحة
- عدد التصميمات الكلي
- التصميمات المعلقة
- المكونات الأكثر شعبية
- الأحجام الأكثر طلباً
- متوسط سعر التصميم

### تقارير
- تقرير المبيعات اليومي
- تحليل المكونات
- تحليل الأسعار
- معدل التحويل

---

## ⚙️ الإعدادات

### إعدادات النظام
```python
BuilderSettings.get_settings()

الإعدادات المتاحة:
- profit_margin_percent: هامش الربح (25%)
- auto_approval_threshold: حد الموافقة التلقائية (5000 ج.م)
- enable_auto_approval: تفعيل الموافقة التلقائية (لا)
- estimated_production_days: مدة الإنتاج (7 أيام)
- max_designs_per_customer: الحد الأقصى للتصميمات (10)
- enable_recommendations: تفعيل الاقتراحات (نعم)
- enable_gamification: عناصر اللعب (نعم)
- welcome_message: رسالة الترحيب
```

---

## 🔧 التخصيص

### إضافة مكون جديد

```python
# مثال: إضافة وسادة طبية
from mattress_builder.models import MattressComponent, MattressComponentCategory

category = MattressComponentCategory.objects.get(category_type='extras')

pillow = MattressComponent.objects.create(
    category=category,
    name='وسادة طبية ميموري فوم',
    name_en='Medical Memory Foam Pillow',
    description='وسادة طبية متقدمة للرقبة',
    short_description='دعم للرقبة',
    base_price=Decimal('200'),
    pricing_type='fixed',
    quality_level='premium',
    specifications={
        'material': 'memory foam',
        'height': '12cm',
        'certification': 'medical grade'
    },
    benefits=[
        'دعم طبي للرقبة',
        'تخفيف آلام العنق',
        'مضاد للحساسية'
    ],
    is_active=True,
    is_featured=True
)
```

### إضافة قاعدة اقتراح

```python
from mattress_builder.models import MattressRecommendationRule

rule = MattressRecommendationRule.objects.create(
    name='اقترح ميموري فوم للسوست الفاخرة',
    description='عند اختيار سوست جيوب منفصلة، اقترح ميموري فوم',
    condition_type='component_selected',
    condition_data={'component_id': 1},  # سوست جيوب منفصلة
    action_type='suggest_component',
    action_data={'component_id': 3},  # ميموري فوم
    message='💎 للحصول على أفضل راحة، جرب ميموري فوم!',
    message_type='tip',
    priority=80,
    is_active=True
)
```

---

## 📱 التكامل مع المتجر الإلكتروني

النظام متكامل بالكامل مع المتجر:

```python
# بعد الموافقة، يمكن تحويل التصميم لطلب
design = CustomMattressDesign.objects.get(pk=123)
if design.status == 'approved':
    # إنشاء منتج مخصص
    custom_product = Product.objects.create(
        sku=f'CUSTOM-{design.id}',
        name=design.design_name,
        price=design.final_price,
        product_type='finished',
        # ... باقي التفاصيل
    )
    
    # إنشاء طلب
    order = Order.objects.create(
        customer=design.customer,
        # ... التفاصيل
    )
```

---

## 🎯 حالات الاستخدام الشائعة

### 1. عميل يريد مرتبة اقتصادية
```
الحجم: مفرد
السوست: متصلة قياسي
الإسفنج: قياسي
القماش: قطني
السعر: ~1,400 ج.م
```

### 2. عميل يريد مرتبة فاخرة
```
الحجم: كينج
السوست: جيوب منفصلة فاخر
الإسفنج: ميموري فوم + عالي المرونة
التبريد: جل التبريد
القماش: مضاد للبكتيريا
السعر: ~3,800 ج.م
```

### 3. عميل لديه مشاكل ظهر
```
الحجم: مزدوج
السوست: جيوب منفصلة (دعم متميز)
الإسفنج: عالي المرونة (دعم قوي)
القماش: قطني طبيعي
السعر: ~2,500 ج.م
```

---

## 🔐 الصلاحيات

### العملاء
- ✅ إنشاء تصميمات
- ✅ حفظ كمسودة
- ✅ إرسال للموافقة
- ✅ عرض تصميماتهم فقط
- ❌ حذف بعد الإرسال

### الموظفين
- ✅ كل صلاحيات العملاء
- ✅ عرض جميع التصميمات
- ✅ الموافقة/الرفض
- ✅ تعديل الأسعار
- ✅ إضافة ملاحظات

### الإدارة
- ✅ كل الصلاحيات
- ✅ إدارة المكونات
- ✅ إدارة الأحجام
- ✅ إدارة الإعدادات
- ✅ التقارير والإحصائيات

---

## 🐛 استكشاف الأخطاء

### المشكلة: السعر غير صحيح
```python
# التحقق من الحسابات
design = CustomMattressDesign.objects.get(pk=123)
design.calculate_total_price()
design.save()
```

### المشكلة: لا يمكن إضافة مكون
```python
# التحقق من القيود
category = component.category
print(f"الحد الأقصى: {category.max_selections}")
print(f"المضاف حالياً: {design.design_components.filter(component__category=category).count()}")
```

---

## 📈 التحسينات المستقبلية

### المرحلة 2
- [ ] معاينة 3D كاملة
- [ ] الواقع المعزز (AR) لرؤية المرتبة في الغرفة
- [ ] مقارنة التصميمات
- [ ] مشاركة التصميمات على السوشيال ميديا

### المرحلة 3
- [ ] تكامل مع نظام الإنتاج
- [ ] تتبع الطلب مباشرةً
- [ ] تقييمات العملاء للتصميمات
- [ ] برنامج ولاء خاص

---

## 🎓 نصائح للمستخدمين

### للعملاء
1. **ابدأ بالحجم** - اختر الحجم الصحيح أولاً
2. **فكر في الاستخدام** - راحة؟ دعم؟ فخامة؟
3. **راجع الفوائد** - كل مكون له ميزات محددة
4. **استخدم الاقتراحات** - النظام يقترح الأفضل لك
5. **لا تتسرع** - خذ وقتك في الاختيار

### للإدارة
1. **راقب الشعبية** - المكونات الشائعة مهمة
2. **راجع الأسعار** - تأكد من التنافسية
3. **سرّع الموافقات** - لا تترك العملاء ينتظرون
4. **حلل البيانات** - استخدم التقارير للتحسين
5. **استمع للعملاء** - ملاحظاتهم ذهب

---

## 📞 الدعم

### المشاكل التقنية
```
/helpdesk/ → تذكرة دعم جديدة
```

### الأسئلة الشائعة
راجع قسم FAQ في المتجر الإلكتروني

---

## 📝 الملاحظات

- ✅ النظام جاهز للاستخدام الفوري
- ✅ البيانات التجريبية محملة
- ✅ جميع APIs فعالة
- ✅ لوحة التحكم جاهزة

**ملاحظة هامة**: هذا النظام الأساسي جاهز، المرحلة التالية هي إنشاء الواجهة التفاعلية Vue.js

---

**تم التطوير بواسطة**: Tony ERP Development Team  
**التاريخ**: يناير 2026  
**الإصدار**: 1.0.0  

🎉 **استمتع ببناء المراتب المخصصة!** 🛏️
