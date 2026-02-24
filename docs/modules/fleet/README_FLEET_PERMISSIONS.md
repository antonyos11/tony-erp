# صلاحيات وحدة الأسطول

تشغيل الأمر التالي لتهيئة صلاحيات الأسطول للأدوار الإدارية:

```
python manage.py init_fleet_permissions
```
أو على Windows PowerShell (ضمن البيئة الافتراضية):
```
& .\.venv\Scripts\python.exe manage.py init_fleet_permissions
```

يُنشئ الصلاحيات (view, add, change, delete, export) للأدوار:
- super_admin
- accounting_manager
- inventory_manager
- sales_manager
- production_manager
- hr_manager

يمكن بعدها تعديل أو تعطيل أي عملية من شاشة الإدارة (ModulePermission).

يتم فحص الصلاحية عبر الدالة: `user.has_module_permission('fleet', 'view')`.

الديكور `require_fleet_access` يحجب الوصول للواجهات عند غياب صلاحية العرض.
