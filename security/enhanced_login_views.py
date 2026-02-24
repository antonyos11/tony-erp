"""
Tony ERP - Enhanced Login Views
عروض تسجيل دخول محسّنة مع المصادقة الثنائية
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.utils.translation import gettext as _
import logging
from typing import Optional
from security.two_factor_auth import TwoFactorAuthManager

logger = logging.getLogger(__name__)


@csrf_protect
@never_cache
def enhanced_login_view(request):
    """
    عرض تسجيل دخول محسّن مع دعم المصادقة الثنائية
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me', False)
        otp_token = request.POST.get('otp_token')
        
        # المرحلة الأولى: التحقق من اسم المستخدم وكلمة المرور
        if not otp_token:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # التحقق من تفعيل المصادقة الثنائية
                if TwoFactorAuthManager.is_2fa_enabled(user):
                    # حفظ معلومات المستخدم مؤقتاً
                    request.session['pending_user_id'] = user.id
                    request.session['remember_me'] = remember_me
                    
                    return render(request, 'registration/login_2fa.html', {
                        'username': username,
                        'require_2fa': True
                    })
                else:
                    # تسجيل الدخول مباشرة
                    login(request, user)
                    
                    # إعداد الجلسة
                    if not remember_me:
                        request.session.set_expiry(0)
                    
                    logger.info(f"User {username} logged in successfully")
                    messages.success(request, _('تم تسجيل الدخول بنجاح'))
                    
                    return redirect(request.GET.get('next', 'home'))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                messages.error(request, _('اسم المستخدم أو كلمة المرور غير صحيحة'))
        
        # المرحلة الثانية: التحقق من رمز المصادقة الثنائية
        else:
            pending_user_id = request.session.get('pending_user_id')
            remember_me = request.session.get('remember_me', False)
            
            if not pending_user_id:
                messages.error(request, _('انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.'))
                return redirect('login')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(id=pending_user_id)
                
                # التحقق من رمز OTP
                if TwoFactorAuthManager.verify_token(user, otp_token):
                    # تسجيل الدخول
                    login(request, user)
                    
                    # حذف البيانات المؤقتة
                    del request.session['pending_user_id']
                    if 'remember_me' in request.session:
                        del request.session['remember_me']
                    
                    # إعداد الجلسة
                    if not remember_me:
                        request.session.set_expiry(0)
                    
                    logger.info(f"User {user.username} logged in with 2FA")
                    messages.success(request, _('تم تسجيل الدخول بنجاح'))
                    
                    return redirect(request.GET.get('next', 'home'))
                else:
                    # التحقق من الرمز الاحتياطي
                    if TwoFactorAuthManager.verify_backup_code(user, otp_token):
                        login(request, user)
                        
                        del request.session['pending_user_id']
                        if 'remember_me' in request.session:
                            del request.session['remember_me']
                        
                        if not remember_me:
                            request.session.set_expiry(0)
                        
                        logger.info(f"User {user.username} logged in with backup code")
                        messages.warning(request, _('تم تسجيل الدخول باستخدام رمز احتياطي. يرجى إنشاء رموز جديدة.'))
                        
                        return redirect('settings_2fa')
                    else:
                        logger.warning(f"Invalid 2FA token for user: {user.username}")
                        messages.error(request, _('رمز التحقق غير صحيح'))
                        
                        return render(request, 'registration/login_2fa.html', {
                            'username': username,
                            'require_2fa': True,
                            'error': True
                        })
            
            except User.DoesNotExist:
                messages.error(request, _('حدث خطأ. يرجى المحاولة مرة أخرى.'))
                return redirect('login')
    
    return render(request, 'registration/login_enhanced.html')


@login_required
def logout_view(request):
    """تسجيل الخروج"""
    username = request.user.username
    logout(request)
    logger.info(f"User {username} logged out")
    messages.info(request, _('تم تسجيل الخروج بنجاح'))
    return redirect('login')


@login_required
def settings_2fa_view(request):
    """إعدادات المصادقة الثنائية"""
    user = request.user
    is_2fa_enabled = TwoFactorAuthManager.is_2fa_enabled(user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # تفعيل المصادقة الثنائية
        if action == 'enable':
            device, qr_code = TwoFactorAuthManager.enable_2fa(user)
            
            return render(request, 'security/2fa_setup.html', {
                'qr_code': qr_code,
                'device': device,
                'secret_key': device.key
            })
        
        # تأكيد المصادقة الثنائية
        elif action == 'confirm':
            device_id = request.POST.get('device_id')
            token = request.POST.get('token')
            
            from django_otp.plugins.otp_totp.models import TOTPDevice
            try:
                device = TOTPDevice.objects.get(id=device_id, user=user)
                
                if TwoFactorAuthManager.verify_and_confirm_2fa(device, token):
                    # إنشاء رموز احتياطية
                    backup_codes = TwoFactorAuthManager.get_backup_codes(user)
                    
                    messages.success(request, _('تم تفعيل المصادقة الثنائية بنجاح'))
                    
                    return render(request, 'security/2fa_backup_codes.html', {
                        'backup_codes': backup_codes
                    })
                else:
                    messages.error(request, _('رمز التحقق غير صحيح'))
            
            except TOTPDevice.DoesNotExist:
                messages.error(request, _('جهاز غير موجود'))
        
        # تعطيل المصادقة الثنائية
        elif action == 'disable':
            password = request.POST.get('password')
            
            # التحقق من كلمة المرور
            if user.check_password(password):
                if TwoFactorAuthManager.disable_2fa(user):
                    messages.success(request, _('تم تعطيل المصادقة الثنائية'))
                else:
                    messages.error(request, _('فشل تعطيل المصادقة الثنائية'))
            else:
                messages.error(request, _('كلمة المرور غير صحيحة'))
            
            return redirect('settings_2fa')
    
    return render(request, 'security/2fa_settings.html', {
        'is_2fa_enabled': is_2fa_enabled
    })


@login_required
def generate_backup_codes_view(request):
    """إنشاء رموز احتياطية جديدة"""
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if request.user.check_password(password):
            # حذف الرموز القديمة
            try:
                from users.models import BackupCode
                BackupCode.objects.filter(user=request.user).delete()
            except ImportError:
                pass
            
            # إنشاء رموز جديدة
            backup_codes = TwoFactorAuthManager.get_backup_codes(request.user)
            
            messages.success(request, _('تم إنشاء رموز احتياطية جديدة'))
            
            return render(request, 'security/2fa_backup_codes.html', {
                'backup_codes': backup_codes,
                'regenerated': True
            })
        else:
            messages.error(request, _('كلمة المرور غير صحيحة'))
    
    return redirect('settings_2fa')
