from django import forms
from django.utils import timezone
from .models import (
    MachineCategory, Machine, MaintenanceType, SparePart, MaintenanceRequest,
    MaintenanceSchedule, MaintenanceRecord, SparePartUsage, MaintenanceChecklist
)
from hr.models import Employee
from inventory.models import Location
from production.models import ProductionWorkCenter


class MachineCategoryForm(forms.ModelForm):
    """نموذج فئة الماكينة"""
    
    class Meta:
        model = MachineCategory
        fields = [
            'code', 'name', 'description', 'default_maintenance_interval_days',
            'default_warranty_months', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'كود الفئة',
                'dir': 'ltr'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الفئة'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف الفئة'
            }),
            'default_maintenance_interval_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'default_warranty_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MachineForm(forms.ModelForm):
    """نموذج الماكينة"""
    
    class Meta:
        model = Machine
        fields = [
            'code', 'name', 'category', 'manufacturer', 'model', 'serial_number',
            'year_manufactured', 'location', 'work_center', 'department',
            'status', 'condition', 'operational_hours', 'purchase_date',
            'purchase_price', 'warranty_start_date', 'warranty_end_date',
            'supplier', 'last_maintenance_date', 'next_maintenance_date',
            'maintenance_interval_days', 'responsible_employee',
            'specifications', 'installation_notes', 'user_manual_path',
            'asset_account', 'depreciation_account', 'maintenance_expense_account',
            'depreciation_method', 'useful_life_years', 'salvage_value',
            'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'كود الماكينة',
                'dir': 'ltr'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الماكينة'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الشركة المصنعة'
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الموديل'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم التسلسلي',
                'dir': 'ltr'
            }),
            'year_manufactured': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1990',
                'max': timezone.now().year + 1
            }),
            'location': forms.Select(attrs={
                'class': 'form-select'
            }),
            'work_center': forms.Select(attrs={
                'class': 'form-select'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'operational_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'warranty_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'warranty_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المورد'
            }),
            'last_maintenance_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_maintenance_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'maintenance_interval_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'responsible_employee': forms.Select(attrs={
                'class': 'form-select'
            }),
            'specifications': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'المواصفات الفنية'
            }),
            'installation_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات التركيب'
            }),
            'user_manual_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مسار دليل المستخدم'
            }),
            'asset_account': forms.Select(attrs={
                'class': 'form-select'
            }),
            'depreciation_account': forms.Select(attrs={
                'class': 'form-select'
            }),
            'maintenance_expense_account': forms.Select(attrs={
                'class': 'form-select'
            }),
            'depreciation_method': forms.Select(attrs={
                'class': 'form-select'
            }),
            'useful_life_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'salvage_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MaintenanceTypeForm(forms.ModelForm):
    """نموذج نوع الصيانة"""
    
    class Meta:
        model = MaintenanceType
        fields = [
            'code', 'name', 'description', 'category', 'default_interval_days',
            'estimated_cost', 'estimated_duration_hours', 'required_skills',
            'requires_external_service', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'كود نوع الصيانة',
                'dir': 'ltr'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم نوع الصيانة'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف نوع الصيانة'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'default_interval_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'estimated_duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'required_skills': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'المهارات المطلوبة'
            }),
            'requires_external_service': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class SparePartForm(forms.ModelForm):
    """نموذج قطعة الغيار"""
    
    class Meta:
        model = SparePart
        fields = [
            'code', 'name', 'description', 'compatible_machines', 'machine_categories',
            'manufacturer', 'part_number', 'alternative_part_numbers',
            'current_stock', 'minimum_stock', 'maximum_stock', 'reorder_point',
            'unit_cost', 'last_purchase_price', 'average_cost',
            'primary_supplier', 'alternative_suppliers',
            'expected_life_hours', 'shelf_life_months', 'category',
            'storage_location', 'bin_location',
            'inventory_account', 'expense_account', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'كود قطعة الغيار',
                'dir': 'ltr'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم قطعة الغيار'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف قطعة الغيار'
            }),
            'compatible_machines': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '5'
            }),
            'machine_categories': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '3'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الشركة المصنعة'
            }),
            'part_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم القطعة الأصلي',
                'dir': 'ltr'
            }),
            'alternative_part_numbers': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'أرقام القطع البديلة (كل رقم في سطر منفصل)'
            }),
            'current_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.001'
            }),
            'minimum_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.001'
            }),
            'maximum_stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.001'
            }),
            'reorder_point': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.001'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'last_purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'average_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'primary_supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المورد الأساسي'
            }),
            'alternative_suppliers': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'الموردين البدائل (كل مورد في سطر منفصل)'
            }),
            'expected_life_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'shelf_life_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'storage_location': forms.Select(attrs={
                'class': 'form-select'
            }),
            'bin_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'موقع الرف'
            }),
            'inventory_account': forms.Select(attrs={
                'class': 'form-select'
            }),
            'expense_account': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MaintenanceRequestForm(forms.ModelForm):
    """نموذج طلب الصيانة"""
    
    class Meta:
        model = MaintenanceRequest
        fields = [
            'machine', 'maintenance_type', 'title', 'description',
            'problem_symptoms', 'priority', 'requested_completion_date',
            'assigned_to', 'estimated_cost', 'estimated_duration_hours',
            'notes'
        ]
        widgets = {
            'machine': forms.Select(attrs={
                'class': 'form-select'
            }),
            'maintenance_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان الطلب'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'وصف المشكلة/المطلوب'
            }),
            'problem_symptoms': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'أعراض المشكلة'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'requested_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'estimated_duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات'
            }),
        }


class MaintenanceScheduleForm(forms.ModelForm):
    """نموذج جدولة الصيانة"""
    
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'name', 'machine', 'maintenance_type', 'frequency', 'interval_days',
            'start_date', 'end_date', 'next_due_date', 'auto_generate_requests',
            'advance_notice_days', 'estimated_cost', 'estimated_duration_hours',
            'assigned_to', 'description', 'checklist_template', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الجدولة'
            }),
            'machine': forms.Select(attrs={
                'class': 'form-select'
            }),
            'maintenance_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'interval_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'auto_generate_requests': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'advance_notice_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'estimated_duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'الوصف'
            }),
            'checklist_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'قائمة الفحص (كل بند في سطر منفصل)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class MaintenanceRecordForm(forms.ModelForm):
    """نموذج سجل الصيانة"""
    
    class Meta:
        model = MaintenanceRecord
        fields = [
            'maintenance_request', 'machine', 'maintenance_type',
            'start_datetime', 'end_datetime', 'status', 'result',
            'work_performed', 'problems_found', 'solutions_applied',
            'technician', 'assistant_technicians', 'labor_cost',
            'external_service_cost', 'other_costs',
            'machine_condition_before', 'machine_condition_after',
            'notes', 'recommendations', 'next_maintenance_notes'
        ]
        widgets = {
            'maintenance_request': forms.Select(attrs={
                'class': 'form-select'
            }),
            'machine': forms.Select(attrs={
                'class': 'form-select'
            }),
            'maintenance_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'result': forms.Select(attrs={
                'class': 'form-select'
            }),
            'work_performed': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'العمل المنفذ'
            }),
            'problems_found': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'المشاكل التي تم اكتشافها'
            }),
            'solutions_applied': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'الحلول المطبقة'
            }),
            'technician': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assistant_technicians': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '3'
            }),
            'labor_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'external_service_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'other_costs': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'machine_condition_before': forms.Select(attrs={
                'class': 'form-select'
            }),
            'machine_condition_after': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'التوصيات'
            }),
            'next_maintenance_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات للصيانة القادمة'
            }),
        }


class SparePartUsageForm(forms.ModelForm):
    """نموذج استخدام قطعة الغيار"""
    
    class Meta:
        model = SparePartUsage
        fields = [
            'spare_part', 'quantity_used', 'unit_cost', 'reason',
            'replaced_part_condition', 'notes'
        ]
        widgets = {
            'spare_part': forms.Select(attrs={
                'class': 'form-select'
            }),
            'quantity_used': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.001'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'reason': forms.Select(attrs={
                'class': 'form-select'
            }),
            'replaced_part_condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات'
            }),
        }


class MaintenanceChecklistForm(forms.ModelForm):
    """نموذج قائمة فحص الصيانة"""
    
    class Meta:
        model = MaintenanceChecklist
        fields = [
            'name', 'maintenance_type', 'machine_category',
            'checklist_items', 'instructions', 'safety_notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم قائمة الفحص'
            }),
            'maintenance_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'machine_category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'checklist_items': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'عناصر قائمة الفحص (كل عنصر في سطر منفصل)'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'تعليمات الفحص'
            }),
            'safety_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات السلامة'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# نماذج مساعدة
class MachineFilterForm(forms.Form):
    """نموذج فلترة الماكينات"""
    
    category = forms.ModelChoiceField(
        queryset=MachineCategory.objects.filter(is_active=True),
        required=False,
        empty_label="كل الفئات",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'كل الحالات')] + Machine.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    condition = forms.ChoiceField(
        choices=[('', 'كل الأوضاع')] + Machine.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="كل المواقع",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بالاسم أو الكود أو الشركة المصنعة'
        })
    )


class SparePartFilterForm(forms.Form):
    """نموذج فلترة قطع الغيار"""
    
    CATEGORY_CHOICES = [
        ('', 'كل الفئات'),
        ('consumable', 'مستهلكات'),
        ('wearing_part', 'قطع تآكل'),
        ('component', 'مكونات'),
        ('tool', 'أدوات'),
        ('filter', 'فلاتر'),
        ('lubricant', 'زيوت وشحوم'),
        ('electrical', 'قطع كهربائية'),
        ('mechanical', 'قطع ميكانيكية'),
    ]
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    stock_status = forms.ChoiceField(
        choices=[
            ('', 'كل الحالات'),
            ('low', 'مخزون منخفض'),
            ('out', 'نفد المخزون'),
            ('reorder', 'يحتاج إعادة طلب')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="كل المواقع",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بالاسم أو الكود أو الرقم المسلسل'
        })
    )