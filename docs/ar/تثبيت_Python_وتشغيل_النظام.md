# تثبيت Python وتشغيل نظام Tony ERP

## ملاحظة مهمة
يبدو أن Python غير مثبت على نظامك. اتبع الخطوات التالية:

---

## الخطوة 1: تحميل وتثبيت Python

### لنظام ويندوز:

1. **اذهب إلى:** https://python.org/downloads/
2. **اضغط على "Download Python 3.11+" الأصدار الأخير**
3. **شغّل ملف التثبيت المحمّل**
4. **مهم جداً:** تأكد من وضع علامة الصح في الخيار:
   ```
   ☑️ Add Python to PATH
   ```
5. **اضغط "Install Now"**
6. **انتظر حتى ينتهي التثبيت**

### لنظام ماك:
```bash
# استخدم Homebrew
brew install python

# أو حمّل من الموقع الرسمي
```

### لنظام لينوكس:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

---

## الخطوة 2: إعادة تشغيل Terminal

بعد تثبيت Python:
1. **أغلق** Command Prompt أو PowerShell الحالي
2. **افتح جديد** (اضغط Win+R ثم اكتب cmd)
3. **اكتب:** `python --version` للتأكد من التثبيت

---

## الخطوة 3: تشغيل النظام

الآن يمكنك تشغيل Tony ERP:

### تلقائي (الأسهل):
```cmd
# ويندوز - انقر نقرة مزدوجة على:
setup_windows.bat

# أو لينوكس/ماك
bash setup_unix.sh
```

### يدوي:
```cmd
# انتقل لمجلد النظام
cd "d:\الشامل"

# فحص النظام
python manage.py system_self_check

# إعداد النظام (إذا لزم الأمر)
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py load_sample_data

# تشغيل النظام
python manage.py runserver
```

---

## حل المشاكل الشائعة

### إذا ظهر خطأ "python is not recognized":
```cmd
# جرب هذه البدائل:
py manage.py system_self_check
python3 manage.py system_self_check
C:\Python311\python.exe manage.py system_self_check
```

### إذا ظهر خطأ في المكتبات:
```cmd
python -m pip install -r requirements.txt
```

### إذا كانت هناك مشاكل في الإذن:
1. شغّل Command Prompt كمدير (Run as Administrator)
2. أو استخدم:
```cmd
python -m pip install --user -r requirements.txt
```

---

## الأوامر المفيدة بعد التثبيت

### فحص النظام:
```cmd
python manage.py system_self_check --fix
```

### إنشاء بيانات تجريبية:
```cmd
python manage.py load_sample_data
```

### نسخة احتياطية:
```cmd
python manage.py backup_now
```

### تشغيل النظام:
```cmd
python manage.py runserver
```

ثم افتح المتصفح على: **http://127.0.0.1:8000**

---

## بيانات الدخول الافتراضية

- **اسم المستخدم:** `superadmin`
- **كلمة المرور:** `admin123`

---

## إذا استمرت المشاكل

1. تأكد من إغلاق وإعادة فتح Command Prompt بعد تثبيت Python
2. تحقق من أن Python مثبت بشكل صحيح: `python --version`
3. إذا لم تحل المشكلة، جرب: `py manage.py system_self_check` بدلاً من `python`

---

**بعد تثبيت Python، سيعمل النظام بسلاسة!**