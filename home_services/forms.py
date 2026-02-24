"""
نماذج إدخال الخدمات المنزلية - Forms
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    ServiceType, MaintenanceCategory, CleaningPackage,
    ServiceRequest, RequestImage, ServiceArea, HomeServicesSettings
)


class ServiceTypeForm(forms.ModelForm):
    """نموذج نوع الخدمة"""
    class Meta:
        model = ServiceType
        fields = ['name', 'code', 'category', 'description', 'icon', 'image',
                  'base_price', 'price_per_hour', 'min_price', 'estimated_duration_hours',
                  'requires_inspection', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-tools'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estimated_duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'requires_inspection': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class MaintenanceCategoryForm(forms.ModelForm):
    """نموذج فئة الصيانة"""
    class Meta:
        model = MaintenanceCategory
        fields = ['name', 'code', 'description', 'icon', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-wrench'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CleaningPackageForm(forms.ModelForm):
    """نموذج باقة النظافة"""
    class Meta:
        model = CleaningPackage
        fields = ['name', 'code', 'description', 'includes', 'excludes',
                  'price', 'discount_price', 'duration_hours', 'workers_count',
                  'is_active', 'is_featured', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'includes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'excludes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'workers_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class MaintenanceRequestForm(forms.ModelForm):
    """نموذج طلب صيانة - للعملاء"""
    class Meta:
        model = ServiceRequest
        fields = [
            'customer_name', 'customer_phone', 'customer_email', 'customer_whatsapp',
            'address', 'city', 'district', 'building_type',
            'maintenance_category', 'title', 'description',
            'preferred_date', 'preferred_time_from', 'preferred_time_to',
            'urgency', 'customer_notes'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الاسم الكامل')
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('05xxxxxxxx'),
                'dir': 'ltr'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('example@email.com'),
                'dir': 'ltr'
            }),
            'customer_whatsapp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('رقم الواتساب'),
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('العنوان التفصيلي')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('المدينة')
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الحي')
            }),
            'building_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('شقة، فيلا، مكتب...')
            }),
            'maintenance_category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('ملخص المشكلة')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('اشرح المشكلة بالتفصيل...')
            }),
            'preferred_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'preferred_time_from': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'preferred_time_to': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'customer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('أي ملاحظات إضافية...')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maintenance_category'].queryset = MaintenanceCategory.objects.filter(is_active=True)


class CleaningRequestForm(forms.ModelForm):
    """نموذج طلب نظافة - للعملاء"""
    class Meta:
        model = ServiceRequest
        fields = [
            'customer_name', 'customer_phone', 'customer_email', 'customer_whatsapp',
            'address', 'city', 'district', 'building_type',
            'cleaning_package', 'title', 'description',
            'preferred_date', 'preferred_time_from', 'preferred_time_to',
            'customer_notes'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الاسم الكامل')
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('05xxxxxxxx'),
                'dir': 'ltr'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('example@email.com'),
                'dir': 'ltr'
            }),
            'customer_whatsapp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('رقم الواتساب'),
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('العنوان التفصيلي')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('المدينة')
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('الحي')
            }),
            'building_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('شقة، فيلا، مكتب...')
            }),
            'cleaning_package': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('نوع التنظيف المطلوب')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('تفاصيل إضافية عن المكان والمتطلبات...')
            }),
            'preferred_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'preferred_time_from': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'preferred_time_to': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'customer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('أي ملاحظات إضافية...')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cleaning_package'].queryset = CleaningPackage.objects.filter(is_active=True)


class ServiceRequestAdminForm(forms.ModelForm):
    """نموذج إدارة طلب الخدمة - للمشرفين"""
    class Meta:
        model = ServiceRequest
        fields = '__all__'
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'estimated_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'final_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'worker_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RequestImageForm(forms.ModelForm):
    """نموذج رفع صورة"""
    class Meta:
        model = RequestImage
        fields = ['image', 'description']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class HomeServicesSettingsForm(forms.ModelForm):
    """نموذج إعدادات الخدمات"""
    class Meta:
        model = HomeServicesSettings
        fields = '__all__'
        widgets = {
            'enable_maintenance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_cleaning': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'working_hours_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'working_hours_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'emergency_surcharge_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'urgent_surcharge_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_booking_hours_advance': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_booking_days_advance': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'confirmation_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
