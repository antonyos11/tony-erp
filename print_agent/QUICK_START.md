# 🚀 دليل البدء السريع - نظام الطباعة

## الخطوات الأساسية (5 دقائق)

### 1️⃣ التثبيت على كمبيوتر الفرع

#### Windows:
```cmd
1. افتح Command Prompt كمسؤول
2. cd C:\path\to\print_agent
3. install_windows.bat
4. اضغط Enter واتبع التعليمات
```

#### Linux:
```bash
1. cd /path/to/print_agent
2. chmod +x install_linux.sh
3. ./install_linux.sh
4. sudo systemctl start tony-print-agent
```

---

### 2️⃣ اختبار النظام

1. **افتح المتصفح** على نفس الكمبيوتر
2. **افتح الملف:** `test_print.html`
3. **يجب أن ترى:** "✓ متصل بخدمة الطباعة"
4. **اضغط:** "طباعة اختبارية"
5. **النتيجة:** يجب أن تطبع الطابعة صفحة اختبار

✅ إذا طبعت = النظام يعمل بنجاح!
❌ إذا لم تطبع = راجع قسم "حل المشاكل"

---

### 3️⃣ دمج مع نظام Django

#### أ) أضف الكود في `base.html`:

```html
<!-- قبل </body> -->
<script src="{% static 'js/tony_print.js' %}"></script>
<div id="print-status"></div>
```

انسخ محتوى `static_integration.html` إلى ملف:
- `static/js/tony_print.js`

#### ب) أضف API في Django:

انسخ `django_integration_example.py` إلى:
- `your_app/views_print.py`

#### ج) أضف URLs:

في `urls.py`:
```python
from .views_print import invoice_print_html

urlpatterns = [
    path('api/invoices/<int:invoice_id>/print-html/', 
         invoice_print_html),
]
```

#### د) استخدم في HTML:

```html
<button onclick="tonyPrint.printInvoice({{ invoice.id }})">
    🖨️ طباعة
</button>
```

---

### 4️⃣ جرب الطباعة من النظام

1. **افتح** صفحة الفاتورة
2. **اضغط** زر "طباعة"
3. **النتيجة:** يجب أن تطبع فورًا!

---

## ✅ Checklist سريع

- [ ] تم تثبيت Python 3.8+
- [ ] تم تثبيت المكتبات (`pip install -r requirements.txt`)
- [ ] تم تشغيل `agent.py`
- [ ] الطابعة مثبتة على Windows/Linux
- [ ] ملف الاختبار يعمل
- [ ] تم دمج JavaScript في Django
- [ ] تم إضافة API للطباعة
- [ ] الطباعة تعمل من المتصفح

---

## 🐛 حل سريع للمشاكل الشائعة

### ❌ "لا يمكن الاتصال بـ Print Agent"

```bash
# تحقق من تشغيل الخدمة
# Windows:
tasklist | findstr python

# Linux:
ps aux | grep agent.py

# إذا لم تكن تعمل، شغلها:
python agent.py
```

### ❌ "الطابعة لا تستجيب"

```bash
# 1. تأكد من الطابعة مثبتة:
# Windows: Control Panel → Devices → Printers
# Linux: lpstat -p -d

# 2. اطبع صفحة تجريبية من النظام
# Windows: من قائمة الطابعة → Print Test Page
# Linux: lp -d printer_name test.txt

# 3. أعد تشغيل Print Agent
```

### ❌ "خطأ: websockets module not found"

```bash
pip install websockets
```

### ❌ "خطأ: pywin32 not found" (Windows)

```bash
pip install pywin32
python -m pywin32_postinstall -install
```

---

## 📊 التدفق الكامل (ملخص)

```
1. المستخدم يضغط "طباعة" في المتصفح
         ↓
2. JavaScript يطلب HTML من Django API
         ↓
3. Django يُرجع HTML جاهز للطباعة
         ↓
4. JavaScript يرسل HTML لـ Print Agent عبر WebSocket
         ↓
5. Print Agent يحوّل HTML ويرسله للطابعة
         ↓
6. الطابعة تطبع!
         ↓
7. Print Agent يُرسل تأكيد للمتصفح
         ↓
8. المستخدم يرى: "✓ تمت الطباعة"
```

---

## 🎯 نصائح مهمة

1. ✅ **شغّل Print Agent أول شيء** قبل فتح المتصفح
2. ✅ **استخدم طابعة افتراضية** لتبسيط الأمور
3. ✅ **راجع الـ log** في `print_agent.log` عند المشاكل
4. ✅ **اختبر على localhost أولاً** قبل النشر
5. ✅ **استخدم Firewall Exception** إذا لزم الأمر

---

## 📞 هل تحتاج مساعدة؟

1. راجع `README.md` للتفاصيل الكاملة
2. راجع `print_agent.log` للأخطاء
3. جرب `test_print.html` للتحقق من الاتصال
4. تأكد من تشغيل الخدمة بصلاحيات كافية

---

**وقت التثبيت الكامل:** < 10 دقائق
**وقت الدمج مع Django:** < 15 دقيقة
**النتيجة:** طباعة مباشرة بنقرة واحدة! 🎉
