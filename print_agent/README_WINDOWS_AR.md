# 🖨️ Tony ERP Print Agent - للطابعات الحرارية XPrinter

## 📥 خطوات التثبيت السريع

### الطريقة 1: تثبيت تلقائي (موصى بها)

1. **افتح Command Prompt كـ Administrator:**
   - اضغط `Win + R`
   - اكتب: `cmd`
   - اضغط `Ctrl + Shift + Enter` (كـ Administrator)

2. **اذهب للمجلد:**
   ```cmd
   cd C:\TonyERP\print_agent_windows
   ```

3. **شغّل التثبيت:**
   ```cmd
   install_simple.bat
   ```

4. **شغّل الخدمة:**
   ```cmd
   run_windows.bat
   ```

---

### الطريقة 2: تثبيت يدوي

إذا فشلت الطريقة الأولى:

```cmd
pip install websockets --user
pip install pywin32 --user
python -m pywin32_postinstall -install
python agent_windows.py
```

---

## 🧪 اختبار الطباعة

1. **تأكد أن الخدمة تعمل** (نافذة سوداء مفتوحة)
2. **افتح:** `test_print.html` في Chrome
3. **يجب أن ترى:** "✅ متصل بخدمة الطباعة"
4. **اضغط:** "طباعة اختبارية"
5. **🖨️ الطابعة ستطبع!**

---

## ⚠️ حل المشاكل الشائعة

### المشكلة: "Python غير مثبت"
**الحل:**
1. حمّل Python من: https://www.python.org/downloads/
2. **مهم جداً:** اختر ✅ **"Add Python to PATH"**
3. أعد تشغيل Command Prompt

---

### المشكلة: "websockets غير موجود"
**الحل:**
```cmd
pip install websockets --user
```

---

### المشكلة: "win32print غير موجود"
**الحل:**
```cmd
pip install pywin32 --user
python -m pywin32_postinstall -install
```

---

### المشكلة: "لا توجد طابعات"
**الحل:**
1. تأكد من تثبيت طابعة XPrinter على Windows
2. افتح: Control Panel → Devices and Printers
3. يجب أن ترى الطابعة هناك
4. اطبع صفحة تجريبية من Windows أولاً

---

### المشكلة: "الطباعة لا تعمل"
**الحل:**
1. تأكد أن الطابعة قيد التشغيل
2. تأكد من وجود ورق
3. جرب طباعة من Notepad أولاً
4. أعد تشغيل الخدمة

---

## 📋 الملفات

- `agent_windows.py` - الخدمة الرئيسية
- `run_windows.bat` - تشغيل الخدمة
- `install_simple.bat` - تثبيت المكتبات
- `test_print.html` - اختبار الطباعة
- `requirements_windows.txt` - قائمة المكتبات

---

## 🔧 متطلبات النظام

- Windows 10/11
- Python 3.8 أو أحدث
- طابعة حرارية XPrinter مثبتة على Windows
- 50 MB مساحة فارغة

---

## 📞 الدعم

إذا واجهت مشاكل:
1. تأكد من تشغيل Command Prompt كـ Administrator
2. تأكد من تثبيت Python بشكل صحيح
3. جرب التثبيت اليدوي (الطريقة 2)
4. تحقق من ملف `print_agent.log` للأخطاء

---

**وقت التثبيت:** < 5 دقائق
**الحالة:** ✅ جاهز للاستخدام

**بالتوفيق! 🚀**
