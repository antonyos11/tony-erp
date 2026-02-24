"""
Tony ERP - Password Validators
محققات كلمات المرور المخصصة
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import re


class ComplexPasswordValidator:
    """محقق كلمة مرور معقدة"""
    
    def __init__(self, min_length=8):
        self.min_length = min_length
    
    def validate(self, password, user=None):
        """التحقق من صحة كلمة المرور"""
        errors = []
        
        # التحقق من الطول الأدنى
        if len(password) < self.min_length:
            errors.append(
                _('كلمة المرور يجب أن تحتوي على %(min_length)d حرف على الأقل.') 
                % {'min_length': self.min_length}
            )
        
        # التحقق من وجود حرف كبير
        if not re.search(r'[A-Z]', password):
            errors.append(_('كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل.'))
        
        # التحقق من وجود حرف صغير
        if not re.search(r'[a-z]', password):
            errors.append(_('كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل.'))
        
        # التحقق من وجود رقم
        if not re.search(r'\d', password):
            errors.append(_('كلمة المرور يجب أن تحتوي على رقم واحد على الأقل.'))
        
        # التحقق من وجود رمز خاص
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_('كلمة المرور يجب أن تحتوي على رمز خاص واحد على الأقل (!@#$%^&*).'))
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return _(
            'كلمة المرور يجب أن تحتوي على %(min_length)d حرف على الأقل، '
            'وتشمل حرف كبير، حرف صغير، رقم، ورمز خاص.'
        ) % {'min_length': self.min_length}


class NoCommonPasswordValidator:
    """منع كلمات المرور الشائعة"""
    
    COMMON_PASSWORDS = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        '1234567890', 'password1', 'admin123', 'test123', 'demo123',
    ]
    
    def validate(self, password, user=None):
        if password.lower() in self.COMMON_PASSWORDS:
            raise ValidationError(
                _('هذه كلمة مرور شائعة جداً. يرجى اختيار كلمة مرور أكثر تعقيداً.'),
                code='password_too_common'
            )
    
    def get_help_text(self):
        return _('كلمة المرور يجب ألا تكون من كلمات المرور الشائعة.')


class NoUserAttributePasswordValidator:
    """منع كلمات المرور المشابهة لبيانات المستخدم"""
    
    def validate(self, password, user=None):
        if not user:
            return
        
        # قائمة الخصائص للتحقق منها
        user_attributes = [
            user.username,
            user.first_name,
            user.last_name,
            user.email.split('@')[0] if user.email else '',
        ]
        
        password_lower = password.lower()
        
        for attribute in user_attributes:
            if not attribute:
                continue
            
            attribute_lower = str(attribute).lower()
            
            # التحقق من التطابق الكامل
            if attribute_lower in password_lower:
                raise ValidationError(
                    _('كلمة المرور يجب ألا تحتوي على معلومات شخصية.'),
                    code='password_too_similar'
                )
            
            # التحقق من التطابق العكسي
            if attribute_lower[::-1] in password_lower:
                raise ValidationError(
                    _('كلمة المرور يجب ألا تحتوي على معلومات شخصية معكوسة.'),
                    code='password_too_similar'
                )
    
    def get_help_text(self):
        return _('كلمة المرور يجب ألا تكون مشابهة لمعلوماتك الشخصية.')


class PasswordHistoryValidator:
    """منع إعادة استخدام كلمات المرور السابقة"""
    
    def __init__(self, history_count=5):
        self.history_count = history_count
    
    def validate(self, password, user=None):
        if not user or not user.pk:
            return
        
        try:
            from django.contrib.auth.hashers import check_password
            from users.models import PasswordHistory
            
            # التحقق من كلمات المرور السابقة
            password_history = PasswordHistory.objects.filter(
                user=user
            ).order_by('-created_at')[:self.history_count]
            
            for old_password in password_history:
                if check_password(password, old_password.password):
                    raise ValidationError(
                        _('لا يمكنك استخدام كلمة مرور سبق استخدامها.'),
                        code='password_used_before'
                    )
        except ImportError:
            # إذا لم يكن نموذج PasswordHistory موجوداً
            pass
    
    def get_help_text(self):
        return _(
            'كلمة المرور يجب ألا تكون من آخر %(count)d كلمات مرور استخدمتها.'
        ) % {'count': self.history_count}
