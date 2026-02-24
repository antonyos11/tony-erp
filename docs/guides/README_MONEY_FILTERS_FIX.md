# فلتر money وإصلاح الأخطاء المحتملة

تم إعداد فلتر `money` في `core/templatetags/money_tags.py` ويقوم بتنسيق القيم المالية مع رمز العملة وعدد المنازل العشرية.

## لماذا ظهر الخطأ "Invalid filter: 'money'"؟
حدث الخطأ لأن القالب استخدم `|money` بدون تحميل مكتبة الفلتر `{% load money_tags %}` ولم يكن الفلتر مضافاً لقائمة `builtins` في إعدادات Django.

## الإجراءات التصحيحية التي تمت
1. إضافة المكتبتين `core.templatetags.money_tags` و `core.templatetags.currency_tags` إلى الإعداد:
   ```python
   TEMPLATES[0]['OPTIONS']['builtins'] = [
       'core.templatetags.money_tags',
       'core.templatetags.currency_tags',
   ]
   ```
2. تعديل القالب `templates/accounting/journal_entries_list.html` لإضافة:
   ```django
   {% load currency_tags money_tags %}
   ```
3. التأكد من وجود تعريف الفلتر في `money_tags.py`.

## كيفية استخدام الفلتر
أمثلة:
```django
{{ amount|money }}               {# 1,234.50 ﷼ مثلاً #}
{{ amount|money:"USD" }}         {# 1,234.50 $ #}
{{ amount|money:"USD:$" }}       {# تحديد الرمز يدوياً #}
{{ amount|money:"|0" }}          {# بدون منازل عشرية #}
{{ amount|money:"USD|3" }}       {# ثلاث منازل عشرية #}
{{ amount|money_compact }}       {# يحذف .00 النهائية #}
{{ amount|money_plain:"3" }}     {# أرقام فقط 3 منازل #}
```

صيغة مدمجة: `CODE:SYMBOL|DECIMALS` مثال: `"USD:$|0"`.

## أفضل الممارسات لتجنب أخطاء مشابهة
- عند إنشاء مكتبة فلاتر تُستخدم كثيراً أضفها إلى `builtins`.
- حافظ على اسم الملف داخل مجلد `templatetags` ولا تنس ملف `__init__.py`.
- استخدم أسماء واضحة للفلاتر وتوثيق مختصر أعلى كل فلتر.
- نفّذ اختباراً سريعاً في shell:
  ```python
  from django.template import Template, Context
  Template('{{ 1234.5|money }}').render(Context())
  ```

## في حال نقل أو إعادة تسمية الملفات
- تأكد من تحديث المسارات في `builtins`.
- ابحث عن جميع القوالب التي تعتمد على الفلتر وتأكد من أنها لا تُحمّل مكتبات قديمة.

## تشخيص سريع إذا عاد الخطأ
1. `python manage.py shell` وجرب استيراد: `import core.templatetags.money_tags`.
2. اطبع `from django.template import engines; print(engines['django'].engine.template_builtins)` للتحقق من التحميل.
3. تأكد أن `INSTALLED_APPS` يحتوي على التطبيق المالك للمكتبة.

تم الإصلاح بنجاح ويمكن الآن استخدام `|money` في أي قالب دون تحميل صريح، لكن يفضل الإبقاء على `{% load money_tags %}` في القوالب الحرجة للوضوح.
