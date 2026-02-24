# دليل الاختبار السريع - نظام Tony ERP

## 🎯 ما تم إنجازه

### ✅ البنية التحتية الكاملة للاختبار
- **11 مكتبة اختبار** مضافة إلى [requirements.txt](requirements.txt)
- **30+ fixture** جاهزة للاستخدام في [tests/conftest.py](tests/conftest.py)
- **20+ factory class** لتوليد البيانات في [tests/factories.py](tests/factories.py)  
- **25+ دالة مساعدة** في [tests/utils.py](tests/utils.py)
- **47 اختبار وحدة** في ملفين (محاسبة ومبيعات)

### ✅ تغطية الاختبارات الحالية
- **المحاسبة:** 22 اختبار (الحسابات، القيود، مراكز التكلفة)
- **المبيعات:** 25 اختبار (الفواتير، الأصناف، المدفوعات، الضرائب)

---

## 🚀 خطوات التشغيل

### 1. تثبيت المكتبات
```bash
cd /var/www/tony_erp
pip install -r requirements.txt
```

### 2. تشغيل الاختبارات
```bash
# تشغيل جميع الاختبارات
pytest

# تشغيل مع تقرير التغطية
pytest --cov=. --cov-report=html

# تشغيل الاختبارات الحرجة فقط (P0)
pytest -m p0

# تشغيل متوازي (أسرع)
pytest -n auto

# تشغيل اختبارات المحاسبة فقط
pytest tests/unit/test_accounting_models.py

# تشغيل اختبارات المبيعات فقط
pytest tests/unit/test_sales_models.py
```

### 3. عرض تقرير التغطية
```bash
pytest --cov=. --cov-report=html
firefox htmlcov/index.html
```

---

## 📊 ما الذي يتم اختباره؟

### المحاسبة (22 اختبار)
✅ إنشاء الحسابات والتسلسل الهرمي  
✅ حساب أرصدة الحسابات (أصول، خصوم، إيرادات، مصروفات)  
✅ التحقق من توازن القيود (المدين = الدائن)  
✅ إنشاء أرقام القيود تلقائياً (JE-2026-000001)  
✅ مراكز التكلفة والسنوات المالية  

### المبيعات (25 اختبار)
✅ إنشاء الفواتير وتوليد الأرقام تلقائياً (INV-202601-000001)  
✅ حساب إجمالي الفاتورة والمتبقي  
✅ خصم المخزون عند إنشاء البند (Signals)  
✅ إرجاع المخزون عند حذف البند  
✅ منع/السماح بالمخزون السالب (حسب الإعدادات)  
✅ حساب الضرائب (شاملة وغير شاملة)  
✅ المدفوعات والخصومات  
✅ **اختبار التزامن:** 20 فاتورة في نفس الوقت بدون تكرار الأرقام  

---

## 🎯 الاختبارات المتبقية (الأولويات)

### Sprint 1 - الوحدات الحرجة (P0)
- [ ] المخزون: Product, Stock, Category
- [ ] الإنتاج: BOM, ProductionOrder, WorkCenter
- [ ] المستخدمين: UserProfile, Permissions

### Sprint 2 - اختبارات التكامل
- [ ] دورة المبيعات الكاملة: فاتورة → مخزون → محاسبة → دفع
- [ ] دورة المشتريات
- [ ] سير عمل الإنتاج

### Sprint 3 - API والأداء
- [ ] JWT Authentication
- [ ] REST API Endpoints
- [ ] اختبارات الأداء والتزامن

---

## 💡 أمثلة الاستخدام

### إنشاء بيانات اختبار بسهولة

```python
from tests.factories import InvoiceFactory, ProductFactory, StockFactory

# إنشاء منتج
product = ProductFactory(price=100.00)

# إنشاء مخزون
stock = StockFactory(product=product, quantity=1000)

# إنشاء فاتورة
invoice = InvoiceFactory()
```

### استخدام Fixtures

```python
def test_something(customer, product, location, sample_chart_of_accounts):
    # customer, product, location, accounts جاهزة للاستخدام
    invoice = InvoiceFactory(customer=customer)
```

### التحقق من الأرصدة والمخزون

```python
from tests.utils import assert_decimal_equal, assert_stock_quantity

# التحقق من رصيد الحساب
assert_account_balance(account, Decimal('1000.00'))

# التحقق من كمية المخزون
assert_stock_quantity(product, location, expected=90)

# التحقق من توازن القيد
assert_journal_entry_balanced(journal_entry)
```

---

## 📈 أهداف التغطية

| الوحدة | الهدف | الحالة |
|--------|-------|--------|
| المحاسبة | 80% | ⏳ قيد العمل |
| المبيعات | 80% | ⏳ قيد العمل |
| المخزون | 80% | ⏳ معلق |
| الإنتاج | 80% | ⏳ معلق |
| المشتريات | 80% | ⏳ معلق |
| **الإجمالي** | **70%** | **30%** |

---

## 🔍 نصائح مهمة

1. **استخدم Factories** بدلاً من إنشاء البيانات يدوياً
2. **استخدم Fixtures** للإعدادات المشتركة
3. **وسّم الاختبارات** بـ markers مناسبة (p0, unit, إلخ)
4. **اختبر الحالات الاستثنائية** (صفر، سالب، 100% خصم)
5. **اختبر التزامن** باستخدام `run_concurrent()`
6. **كل اختبار مستقل** - لا يعتمد على اختبار آخر

---

## 📁 الملفات الرئيسية

| الملف | الوصف | الحالة |
|-------|-------|--------|
| [requirements.txt](../requirements.txt) | المكتبات المطلوبة | ✅ محدّث |
| [pytest.ini](../pytest.ini) | إعدادات pytest | ✅ محدّث |
| [.coveragerc](../.coveragerc) | إعدادات التغطية | ✅ محدّث |
| [tests/conftest.py](conftest.py) | Fixtures مشتركة | ✅ كامل |
| [tests/factories.py](factories.py) | Factory classes | ✅ كامل |
| [tests/utils.py](utils.py) | دوال مساعدة | ✅ كامل |
| [tests/unit/test_accounting_models.py](unit/test_accounting_models.py) | اختبارات المحاسبة | ✅ 22 اختبار |
| [tests/unit/test_sales_models.py](unit/test_sales_models.py) | اختبارات المبيعات | ✅ 25 اختبار |

---

## 🎉 الإنجازات

✅ **البنية الأساسية:** 100%  
✅ **Factories:** 20+ فئة  
✅ **Fixtures:** 30+ fixture  
✅ **Utilities:** 25+ دالة  
✅ **الاختبارات:** 47 اختبار  
✅ **سطور الكود:** ~2,000 سطر  

**الوقت المستثمر:** 4-6 ساعات  
**الهدف النهائي:** 500+ اختبار، تغطية 70-80%  

---

## 📞 الدعم

لمزيد من التفاصيل، راجع:
- [TESTING_IMPLEMENTATION_SUMMARY.md](../TESTING_IMPLEMENTATION_SUMMARY.md) - ملخص شامل
- [tests/README.md](README.md) - دليل باللغة الإنجليزية

---

**الجلسة القادمة:** استكمال Sprint 1 - اختبارات المخزون والإنتاج والمستخدمين
