# 🖨️ دليل تحميل وتثبيت خدمة الطباعة

## 🎯 الهدف
تثبيت خدمة طباعة على جهازك المحلي (Windows) تسمح للسيرفر بطلب الطباعة على طابعتك الحرارية **XPrinter** مباشرة.

---

## 📍 الروابط المهمة

### 1️⃣ تحميل الملفات (ZIP كامل)
```
http://72.62.176.249/static/print_agent_windows.zip
```
✅ **هذا يحتوي على كل شيء تحتاجه - حمّله أولاً**

### 2️⃣ صفحة التثبيت التفاعلية (خطوة خطوة)
```
http://72.62.176.249/print_agent/setup_local.html
```
📖 **افتح هذا إذا احتجت شرح مفصل بالصور والألوان**

### 3️⃣ اختبار الطباعة (بعد التثبيت)
```
C:\TonyERP\print_agent_windows\test_print.html
```
🧪 **افتح هذا في Chrome لاختبار الاتصال والطباعة**

---

## ⚡ خطوات التثبيت السريعة (5 دقائق)

### خطوة 1: تحميل الملفات
```
افتح المتصفح → http://72.62.176.249/static/print_agent_windows.zip
```
✅ حمّل الملف

### خطوة 2: استخراج الملفات
```
كليك يمين على print_agent_windows.zip
استخرج إلى: C:\TonyERP\
```
✅ ستظهر مجلد جديد: `C:\TonyERP\print_agent_windows`

### خطوة 3: التثبيت
```
1. Win + R → cmd → Ctrl + Shift + Enter (كـ Admin)
2. cd C:\TonyERP\print_agent_windows
3. pip install websockets pywin32 --user
4. python -m pywin32_postinstall -install
```
✅ اتركها حتى تنتهي

### خطوة 4: التشغيل
```
شغّل الملف: C:\TonyERP\print_agent_windows\run_windows.bat
```
✅ ستظهر نافذة سوداء مع كلام عن WebSocket

### خطوة 5: الاختبار
```
افتح: C:\TonyERP\print_agent_windows\test_print.html
اضغط: "طباعة اختبارية"
```
✅ 🖨️ الطابعة تطبع الآن!

---

## 📋 ملفات التثبيت (داخل ZIP)

| الملف | الوصف | متى تستخدمه |
|------|-------|-----------|
| `install_simple.bat` | تثبيت المكتبات | أول مرة تفقط |
| `run_windows.bat` | تشغيل الخدمة | كل مرة تريد الطباعة |
| `agent_windows.py` | الخدمة الرئيسية | يعمل تلقائياً من batch |
| `test_print.html` | اختبار الطباعة | للتحقق أن كل شيء يشتغل |
| `requirements.txt` | المكتبات المطلوبة | مرجع فقط |

---

## ✅ علامات النجاح

### هل اكتمل التثبيت بنجاح؟

- ✅ `run_windows.bat` يفتح نافذة سوداء
- ✅ النافذة تقول: "WebSocket Server running on ws://localhost:9876"
- ✅ `test_print.html` يفتح في المتصفح
- ✅ الصفحة تقول: "✅ متصل بخدمة الطباعة" (باللون الأخضر)
- ✅ اسم الطابعة يظهر في قائمة الطابعات
- ✅ عند اضغط "طباعة اختبارية" → 🖨️ الطابعة تطبع

---

## ⚠️ المشاكل الشائعة والحلول

### ❌ "Python غير موجود"
```
الحل: حمّل Python من https://www.python.org
أثناء التثبيت: ✅ اختر "Add Python to PATH"
```

### ❌ "pip لا يشتغل"
```
جرّب:
python -m pip install --upgrade pip
python -m pip install websockets --user
python -m pip install pywin32 --user
```

### ❌ "لا توجد طابعات"
```
1. تأكد الطابعة موصولة (USB)
2. في Windows: Settings → Devices → Printers & Scanners
3. تأكد أنها في القائمة
4. أعد تشغيل run_windows.bat
```

### ❌ "الطابعة لا تطبع"
```
1. تأكد أن run_windows.bat مفتوح (نافذة سوداء)
2. جرّب test_print.html أولاً
3. شوف الأخطاء في النافذة السوداء
4. أعد تشغيل الخدمة
```

---

## 🔄 بعد التثبيت الناجح

### كل مرة تريد الطباعة:
1. فتح `run_windows.bat` (تشغيل مرة واحدة)
2. اترك النافذة مفتوحة
3. الآن يمكنك الطباعة من السيرفر مباشرة! ✅

### اختياري: تشغيل تلقائي عند بدء الحاسوب
```
1. Win + R → shell:startup
2. انسخ اختصار run_windows.bat إلى هنا
3. الخدمة ستبدأ تلقائياً عند تشغيل الحاسوب
```

---

## 📞 إذا حصلت مشكلة

1. **خذ screenshot للنافذة السوداء وأي أخطاء**
2. **افتح `test_print.html` وشوف الرسائل**
3. **تحقق من هذه القائمة في Windows:**
   - Settings → Devices → Printers & Scanners
   - تأكد الطابعة موصولة وظاهرة

---

## 🎉 سلام التثبيت!

عندما تشتغل كل الخطوات:
```
✅ Windows سيكتشف الطابعة
✅ test_print.html سيقول "متصل"
✅ طابعتك ستطبع التجربة
✅ الآن أنت جاهز لطباعة الفواتير من السيرفر!
```

---

## 🔗 ملخص الروابط

| الرابط | الاستخدام |
|--------|----------|
| `http://72.62.176.249/static/print_agent_windows.zip` | 📥 تحميل كل الملفات |
| `http://72.62.176.249/print_agent/setup_local.html` | 📖 شرح مفصل وتفاعلي |
| `C:\TonyERP\print_agent_windows\run_windows.bat` | 🚀 تشغيل الخدمة |
| `C:\TonyERP\print_agent_windows\test_print.html` | 🧪 اختبار الطباعة |

---

**النسخة: 2.0** | **آخر تحديث: يناير 2026**
