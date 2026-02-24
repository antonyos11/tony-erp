from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import UserRole, UserProfile, UserSession
import ipaddress


class CustomUserCreationForm(UserCreationForm):
    """نموذج إنشاء مستخدم جديد"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تخصيص الحقول
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'البريد الإلكتروني'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'الاسم الأول'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'اسم العائلة'
        })


class CustomUserChangeForm(UserChangeForm):
    """نموذج تحديث بيانات المستخدم"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إزالة حقل كلمة المرور من النموذج
        if 'password' in self.fields:
            del self.fields['password']
            
        # تخصيص الحقول
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs.update({'class': 'form-control'})


class UserProfileForm(forms.ModelForm):
    """نموذج تحديث الملف الشخصي للمستخدم"""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class PasswordChangeForm(forms.Form):
    """نموذج تغيير كلمة المرور"""
    
    old_password = forms.CharField(
        label='كلمة المرور الحالية',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label='كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='يجب أن تحتوي على 8 أحرف على الأقل'
    )
    new_password2 = forms.CharField(
        label='تأكيد كلمة المرور الجديدة',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise ValidationError('كلمة المرور الحالية غير صحيحة')
        return old_password
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('كلمتا المرور غير متطابقتان')
        
        # التحقق من قوة كلمة المرور
        if password2:
            validate_password(password2, self.user)
        
        return password2
    
    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.must_change_password = False
        self.user.save()
        return self.user


# ApprovalRequestForm - تم تعليقه مؤقتاً لعدم وجود موديل ApprovalRequest
# class ApprovalRequestForm(forms.ModelForm):
#     """نموذج طلب الموافقة"""
#     
#     class Meta:
#         model = ApprovalRequest
#         fields = ('notes',)
#         widgets = {
#             'notes': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 3,
#                 'placeholder': 'ملاحظات إضافية (اختيارية)'
#             })
#         }


class ApprovalActionForm(forms.Form):
    """نموذج إجراء الموافقة"""
    
    ACTION_CHOICES = [
        ('approved', 'موافق'),
        ('rejected', 'مرفوض'),
        ('returned', 'مُرجع للمراجعة'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الإجراء'
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'التعليقات'
        }),
        label='التعليقات',
        required=False
    )


class UserSearchForm(forms.Form):
    """نموذج البحث عن المستخدمين"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بالاسم أو اسم المستخدم'
        }),
        label='البحث'
    )
    
    role = forms.ModelChoiceField(
        queryset=UserRole.objects.all(),
        required=False,
        empty_label='جميع الأدوار',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الدور'
    )
    
    is_active = forms.ChoiceField(
        choices=[('', 'الكل'), ('true', 'نشط'), ('false', 'غير نشط')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الحالة'
    )


class BulkUserActionForm(forms.Form):
    """نموذج الإجراءات المجمعة على المستخدمين"""
    
    ACTION_CHOICES = [
        ('activate', 'تفعيل'),
        ('deactivate', 'إلغاء تفعيل'),
        ('approve', 'موافقة'),
        ('delete', 'حذف'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الإجراء'
    )
    
    selected_users = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean_selected_users(self):
        selected_users = self.cleaned_data.get('selected_users', '')
        if not selected_users:
            raise ValidationError('يجب اختيار مستخدم واحد على الأقل')
        
        try:
            user_ids = [int(id) for id in selected_users.split(',')]
            return user_ids
        except ValueError:
            raise ValidationError('معرفات المستخدمين غير صحيحة')


class SessionManagementForm(forms.Form):
    """نموذج إدارة الجلسات"""
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label='جميع المستخدمين',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='المستخدم'
    )
    
    action = forms.ChoiceField(
        choices=[
            ('terminate_all', 'إنهاء جميع الجلسات'),
            ('terminate_inactive', 'إنهاء الجلسات غير النشطة'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الإجراء'
    )


# ===== نموذج إدارة الأدوار =====

class UserRoleForm(forms.ModelForm):
    """نموذج إنشاء/تعديل الأدوار"""
    
    class Meta:
        model = UserRole
        fields = ['name', 'display_name', 'description']
        labels = {
            'name': 'الاسم (بالإنجليزية)',
            'display_name': 'الاسم المعروض',
            'description': 'الوصف',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: sales_manager',
                'dir': 'ltr'
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: مدير المبيعات'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'وصف الدور والصلاحيات...',
                'rows': 3
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip().lower()
        # التحقق من عدم وجود مسافات
        if ' ' in name:
            raise forms.ValidationError('الاسم يجب أن لا يحتوي على مسافات')
        # التحقق من عدم التكرار
        if self.instance.pk:
            if UserRole.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('هذا الاسم مستخدم مسبقاً')
        else:
            if UserRole.objects.filter(name=name).exists():
                raise forms.ValidationError('هذا الاسم مستخدم مسبقاً')
        return name