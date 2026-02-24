"""نماذج إدخال إنتاج العمال"""
from django import forms
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from .models import WorkerProductionEntry
from inventory.models import Product
from production.models import ProductionWorkCenter, ProductionOrder
from hr.models import Employee


class WorkerProductionEntryForm(forms.ModelForm):
    """نموذج إدخال إنتاج عامل"""
    
    class Meta:
        model = WorkerProductionEntry
        fields = [
            'employee', 'date', 'shift', 'product', 'quantity', 
            'unit_of_measure', 'work_center', 'machine_code',
            'start_time', 'end_time', 'hours_worked', 
            'production_order', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'shift': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: صباحي، مسائي'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'unit_of_measure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'متر، كجم، قطعة...'}),
            'work_center': forms.Select(attrs={'class': 'form-select'}),
            'machine_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: M-001'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'production_order': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # إذا كان العامل محدداً، نضعه افتراضياً ونخفي الحقل
        if employee:
            self.fields['employee'].initial = employee
            self.fields['employee'].widget = forms.HiddenInput()
        
        # تصفية المنتجات (فقط المنتجات النشطة)
        self.fields['product'].queryset = Product.objects.filter(
            is_active=True
        ).order_by('name')
        
        # تصفية مراكز العمل (فقط النشطة)
        self.fields['work_center'].queryset = ProductionWorkCenter.objects.filter(
            is_active=True
        ).order_by('name')
        
        # تصفية أوامر الإنتاج (فقط المفتوحة)
        self.fields['production_order'].queryset = ProductionOrder.objects.filter(
            status__in=['confirmed', 'in_progress']
        ).order_by('-created_at')[:50]
        
        # التاريخ الافتراضي = اليوم
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        hours_worked = cleaned_data.get('hours_worked')
        
        # حساب ساعات العمل تلقائياً إذا تم توفير البداية والنهاية
        if start_time and end_time and not hours_worked:
            from datetime import datetime, timedelta
            start_dt = datetime.combine(timezone.now().date(), start_time)
            end_dt = datetime.combine(timezone.now().date(), end_time)
            
            # إذا كان وقت الانتهاء قبل البدء، يعني الوردية تمتد لليوم التالي
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            duration = end_dt - start_dt
            cleaned_data['hours_worked'] = Decimal(str(duration.total_seconds() / 3600))
        
        return cleaned_data


class WorkerProductionEntrySimpleForm(forms.ModelForm):
    """نموذج مبسط لإدخال إنتاج العامل (لبوابة العمال)"""
    
    class Meta:
        model = WorkerProductionEntry
        fields = ['product', 'quantity', 'unit_of_measure', 'size_description', 'machine_code', 'notes']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'style': 'font-size: 1.2rem;'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'step': '0.001',
                'min': '0',
                'placeholder': 'الكمية المنتجة',
                'style': 'font-size: 1.5rem;'
            }),
            'unit_of_measure': forms.Select(attrs={
                'class': 'form-select form-select-lg'
            }, choices=[
                ('متر', 'متر'),
                ('كجم', 'كيلوجرام'),
                ('قطعة', 'قطعة'),
                ('رول', 'رول'),
            ]),
            'size_description': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'المقاس (مثال: 160×200) - اختياري'
            }),
            'machine_code': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'رقم الماكينة (اختياري)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات إضافية (اختياري)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # المنتجات النشطة فقط، ومقيدة على قسم العامل إن وُجد إعداد ذلك
        qs = Product.objects.all()
        try:
            qs = qs.filter(is_active=True)
        except Exception:
            # لو لم يكن هناك حقل is_active في المنتج نتجاهل الفلتر
            pass
        if employee and getattr(employee, 'department', None) and employee.department.code:
            code = employee.department.code
            qs = qs.filter(Q(production_department_code="") | Q(production_department_code=code))
        self.fields['product'].queryset = qs.order_by('name')
        
        # إذا كان العامل محدداً، نحفظه في الفورم
        self.employee = employee
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # ضبط البيانات الافتراضية
        if self.employee:
            instance.employee = self.employee
        
        instance.date = timezone.now().date()
        instance.status = 'submitted'  # مقدم تلقائياً
        
        # تحديد الوردية بناءً على الوقت
        current_hour = timezone.now().hour
        if 6 <= current_hour < 14:
            instance.shift = 'صباحي'
        elif 14 <= current_hour < 22:
            instance.shift = 'مسائي'
        else:
            instance.shift = 'ليلي'
        
        # حساب تكلفة العمالة
        instance.calculate_labor_cost()
        
        if commit:
            instance.save()
        
        return instance


class WorkerProductionApprovalForm(forms.ModelForm):
    """نموذج الموافقة على تسجيل إنتاج"""
    
    approve = forms.BooleanField(required=False, label='الموافقة')
    
    class Meta:
        model = WorkerProductionEntry
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'سبب الرفض (إذا لم تتم الموافقة)'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        approve = cleaned_data.get('approve')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if not approve and not rejection_reason:
            raise forms.ValidationError('يرجى إدخال سبب الرفض')
        
        return cleaned_data

