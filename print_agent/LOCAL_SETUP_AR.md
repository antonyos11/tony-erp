# 🖨️ تثبيت خدمة الطباعة على جهازك المحلي

## ✅ ما هي هذه الخدمة؟

هذه خدمة تعمل على جهازك **المحلي (Windows)** وتسمح للسيرفر بطلب الطباعة مباشرة على طابعتك الحرارية **XPrinter** بدون تدخل منك.

```
السيرفر (Server) ← → جهازك المحلي (Local PC) → طابعتك الحرارية
```

---

## 📥 الخطوة 1: تحميل الملفات

### الطريقة أ: تحميل ZIP (الأسهل)

1. **افتح المتصفح وادخل:**
   ```
   http://72.62.176.249/static/print_agent_windows.zip
   ```

2. **اضغط لتحميل الملف** (سيحفظ على جهازك)

3. **استخرج الملفات:**
   - اضغط **كليك يمين** على `print_agent_windows.zip`
   - اختر **Extract All...**
   - اختر المجلد: `C:\TonyERP\`
   - يجب أن تظهر مجلد جديد: `C:\TonyERP\print_agent_windows`

### الطريقة ب: تحميل يدوي

أنسخ هذه الملفات من السيرفر إلى `C:\TonyERP\print_agent_windows\`:
- `agent_windows.py`
- `run_windows.bat`
- `install_simple.bat`
- `test_print.html`
- `requirements.txt`
- `README_WINDOWS_AR.md`

---

## 🔧 الخطوة 2: التثبيت

### طريقة سريعة وآمنة:

1. **افتح Command Prompt كـ Administrator:**
   - اضغط `Win + R`
   - اكتب: `cmd`
   - اضغط `Ctrl + Shift + Enter` (لتشغيله كـ Admin)

2. **اذهب إلى المجلد:**
   ```cmd
   cd C:\TonyERP\print_agent_windows
   ```

3. **تحقق من Python:**
   ```cmd
   python --version
   ```
   - يجب أن ترى: `Python 3.x.x`
   - إذا لم تره → [انسخ وثبت Python أولاً](#-تثبيت-python)

4. **ثبّت المكتبات المطلوبة:**
   ```cmd
   pip install websockets --user
   pip install pywin32 --user
   python -m pywin32_postinstall -install
   ```

---

## 🚀 الخطوة 3: تشغيل الخدمة

### التشغيل البسيط:

1. **شغّل هذا الملف:**
   ```
   C:\TonyERP\print_agent_windows\run_windows.bat
   ```

2. **ستظهر نافذة سوداء مع الرسالة:**
   ```
   WebSocket Server running on ws://localhost:9876
   ```

3. **اترك هذه النافذة مفتوحة طول الوقت** ⚠️
   - إذا أغلقتها = الطباعة توقفت
   - اختياري: اضغط `Alt + Enter` لتوسيع النافذة

---

## 🧪 الخطوة 4: اختبار الطباعة

### اختبر أن كل شيء يشتغل:

1. **افتح هذا الملف في Chrome:**
   ```
   C:\TonyERP\print_agent_windows\test_print.html
   ```

2. **يجب أن ترى في الصفحة:**
   - ✅ **"متصل بخدمة الطباعة"** (أخضر)
   - اسم الطابعة (مثلاً: XPrinter-80mm)
   - زر "طباعة اختبارية"

3. **اضغط "طباعة اختبارية":**
   - 🖨️ الطابعة يجب أن تطبع استلام تجريبي

---

## 🌐 الخطوة 5: ربط السيرفر مع جهازك

### الآن السيرفر يقدر يطبع من خلالك:

في أي صفحة في المتجر على السيرفر (مثلاً عند طباعة فاتورة):
- الكود تلقائياً سيطلب الطباعة من جهازك المحلي
- طابعتك ستطبع مباشرة ✅

---

## 🔄 تشغيل دوري (اختياري)

إذا أردت **تشغيل الخدمة تلقائياً عند تشغيل الحاسوب**:

1. اضغط `Win + R`
2. اكتب: `shell:startup`
3. انسخ اختصار لـ `run_windows.bat` إلى هذا المجلد

---

## ⚠️ حل المشاكل الشائعة

### المشكلة 1: "Python غير مثبت"

**الحل:**
1. حمّل Python من: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **مهم جداً:** أثناء التثبيت اختر ✅ **"Add Python to PATH"**
3. أعد تشغيل Command Prompt
4. تحقق بـ: `python --version`

---

### المشكلة 2: "لا توجد أي طابعات"

**التحقق:**
1. هل الطابعة موصولة؟ (USB أو Network)
2. في Windows اذهب إلى: **Settings → Devices → Printers & Scanners**
3. تأكد أن طابعتك ظاهرة في القائمة

**إذا كانت ظاهرة:**
1. أغلق `run_windows.bat`
2. افتح Command Prompt و اكتب:
   ```cmd
   python agent_windows.py
   ```
3. شوف الأخطاء وأرسلها

---

### المشكلة 3: "الطابعة لا تطبع"

1. **تأكد أن `run_windows.bat` مفتوح** (نافذة سوداء مفتوحة)
2. **شوف رسائل الخطأ في النافذة السوداء**
3. **جرّب اختبار من `test_print.html`**
4. إذا اختبار يعمل لكن الفاتورة لا تطبع → قول لنا

---

### المشكلة 4: "خطأ pip install"

**جرّب هذا بدلاً منه:**
```cmd
python -m pip install --upgrade pip
python -m pip install websockets pywin32
python -m pywin32_postinstall -install
```

---

## 📋 ملخص الخطوات السريعة

```
1. حمّل ZIP من: http://72.62.176.249/static/print_agent_windows.zip
2. استخرج إلى: C:\TonyERP\print_agent_windows\
3. افتح Command Prompt كـ Admin
4. اكتب: cd C:\TonyERP\print_agent_windows
5. اكتب: pip install websockets pywin32 --user
6. اكتب: python -m pywin32_postinstall -install
7. شغّل: run_windows.bat
8. افتح: test_print.html واختبر
```

---

## 📞 الدعم

- **الملفات موجودة في:** `/print_agent/` على السيرفر
- **إذا واجهت مشكلة:** خذ screenshot للنافذة السوداء وأرسله

---

## ✅ سلام التثبيت كامل!

عندما تشتغل كل شيء صح:
- ✅ Command Prompt يظهر: "WebSocket Server running on ws://localhost:9876"
- ✅ test_print.html يظهر: "متصل بخدمة الطباعة" (أخضر)
- ✅ اختبار الطباعة يطبع استلام
- ✅ الآن أنت جاهز لطباعة الفاتورة من السيرفر!

