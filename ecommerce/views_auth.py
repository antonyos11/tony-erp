"""
Views للمصادقة وتسجيل الدخول الاجتماعي
Authentication & Social Login Views
"""
import secrets
import hashlib
import urllib.parse
import json
import requests
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from .models import (
    Customer, CustomerAddress, SocialAccount, SocialAuthProvider,
    PasswordResetToken, EmailVerificationToken, EcommerceSettings
)

# CRM Integration
try:
    from crm.models import Customer as CrmCustomer, Activity, ActivityType, CustomerSource, CustomerType
except ImportError:
    CrmCustomer = None

User = get_user_model()


def log_crm_login(user):
    """تسجيل دخول العميل في نظام CRM"""
    if not CrmCustomer:
        return

    try:
        # البحث عن العميل في CRM
        crm_customer = CrmCustomer.objects.filter(email=user.email).first()
        
        # إذا لم يكن موجوداً، نقوم بإنشائه (لضمان المزامنة)
        if not crm_customer:
            try:
                source, _ = CustomerSource.objects.get_or_create(name="المتجر الإلكتروني")
                ctype, _ = CustomerType.objects.get_or_create(name="عميل أونلاين")
                
                phone = ''
                if hasattr(user, 'customer_profile'):
                    phone = user.customer_profile.phone
                
                crm_customer = CrmCustomer.objects.create(
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    phone=phone,
                    source=source,
                    customer_type=ctype,
                )
            except Exception:
                pass
        
        if crm_customer:
            # تسجيل النشاط
            activity_type, _ = ActivityType.objects.get_or_create(name="تسجيل دخول المتجر")
            
            # نحتاج مستخدم لتعيين النشاط له - نستخدم المشرف
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                return
                
            Activity.objects.create(
                title="تسجيل دخول عميل",
                activity_type=activity_type,
                description=f"قام العميل {user.get_full_name()} بتسجيل الدخول للمتجر",
                customer=crm_customer,
                scheduled_date=timezone.now(),
                status='completed',
                priority='medium',
                assigned_to=admin_user,
                completed_at=timezone.now()
            )
    except Exception as e:
        print(f"CRM Logging Error: {e}")


def get_store_context():
    """الحصول على السياق الأساسي للمتجر"""
    store_settings = EcommerceSettings.get_settings()
    social_providers = SocialAuthProvider.objects.filter(is_active=True).order_by('sort_order')
    return {
        'store_settings': store_settings,
        'social_providers': social_providers,
    }


def customer_login(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:store_home')
    
    context = get_store_context()
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember_me')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                # التحقق من أن المستخدم عميل
                customer, created = Customer.objects.get_or_create(user=user)
                login(request, user)

                # تسجيل النشاط في CRM
                if settings.DEBUG:  # To avoid blocking in dev if something is wrong
                    try:
                        log_crm_login(user)
                    except:
                        pass
                else:
                    log_crm_login(user)
                
                if not remember:
                    request.session.set_expiry(0)  # تنتهي عند إغلاق المتصفح
                
                messages.success(request, _('مرحباً بك!'))
                
                # إعادة التوجيه للصفحة المطلوبة
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('ecommerce:store_home')
            else:
                messages.error(request, _('كلمة المرور غير صحيحة'))
        except User.DoesNotExist:
            messages.error(request, _('لا يوجد حساب بهذا البريد الإلكتروني'))
    
    context['next'] = request.GET.get('next', '')
    return render(request, 'ecommerce/auth/login.html', context)


def customer_register(request):
    """صفحة التسجيل"""
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:store_home')
    
    context = get_store_context()
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        agree_terms = request.POST.get('agree_terms')
        
        # التحقق من البيانات
        errors = []
        
        if not first_name:
            errors.append(_('الاسم الأول مطلوب'))
        if not email:
            errors.append(_('البريد الإلكتروني مطلوب'))
        elif User.objects.filter(email=email).exists():
            errors.append(_('البريد الإلكتروني مستخدم بالفعل'))
        if len(password) < 8:
            errors.append(_('كلمة المرور يجب أن تكون 8 أحرف على الأقل'))
        if password != password_confirm:
            errors.append(_('كلمتا المرور غير متطابقتين'))
        if not agree_terms:
            errors.append(_('يجب الموافقة على الشروط والأحكام'))
        
        if errors:
            for error in errors:
                messages.error(request, error)
            context['form_data'] = request.POST
        else:
            try:
                with transaction.atomic():
                    # إنشاء المستخدم
                    username = f"customer_{email.split('@')[0]}_{secrets.token_hex(4)}"
                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=make_password(password),
                    )
                    
                    # إنشاء ملف العميل في المتجر الإلكتروني
                    customer = Customer.objects.create(
                        user=user,
                        phone=phone,
                    )
                    
                    # ===== إنشاء سجل العميل في نظام المبيعات تلقائياً =====
                    from partners.models import Customer as PartnerCustomer
                    full_name = f"{first_name} {last_name}".strip() or email.split('@')[0]
                    
                    # إنشاء العميل في نظام الشركاء مع تسجيل المصدر
                    partner_customer = PartnerCustomer.objects.create(
                        name=full_name,
                        email=email,
                        phone=phone,
                        address=_('عميل من المتجر الإلكتروني'),  # ملاحظة المصدر
                    )
                    
                    # ربط العميل بملف المتجر الإلكتروني
                    customer.partner_customer = partner_customer
                    customer.save(update_fields=['partner_customer'])
                    
                    # تسجيل في سجل التدقيق
                    try:
                        from core.models import AuditLog
                        AuditLog.objects.create(
                            action=AuditLog.ACTION_CREATE,
                            model_name='Customer',
                            app_label='partners',
                            object_id=str(partner_customer.pk),
                            object_repr=f"عميل متجر إلكتروني: {full_name}",
                            changes={'source': 'ecommerce_registration', 'email': email}
                        )
                    except Exception:
                        pass  # لا نوقف العملية إذا فشل التسجيل
                    # ===== انتهى إنشاء سجل العميل =====
                    
                    # إرسال بريد التأكيد
                    send_verification_email(customer)
                    
                    # تسجيل الدخول
                    login(request, user)
                    
                    # تسجيل النشاط في CRM
                    log_crm_login(user)
                    
                    messages.success(request, _('تم إنشاء حسابك بنجاح! تم إرسال رابط تأكيد البريد الإلكتروني.'))
                    
                    next_url = request.GET.get('next') or request.POST.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('ecommerce:store_home')
                    
            except Exception as e:
                messages.error(request, _('حدث خطأ أثناء إنشاء الحساب. حاول مرة أخرى.'))
    
    context['next'] = request.GET.get('next', '')
    return render(request, 'ecommerce/auth/register.html', context)


@login_required(login_url='ecommerce:customer_login')
def customer_logout(request):
    """تسجيل الخروج"""
    logout(request)
    messages.success(request, _('تم تسجيل خروجك بنجاح'))
    return redirect('ecommerce:store_home')


def forgot_password(request):
    """صفحة نسيت كلمة المرور"""
    context = get_store_context()
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        try:
            user = User.objects.get(email=email)
            if hasattr(user, 'customer_profile'):
                customer = user.customer_profile
                
                # إنشاء توكن إعادة التعيين
                token = secrets.token_urlsafe(32)
                PasswordResetToken.objects.create(
                    customer=customer,
                    token=token,
                    expires_at=timezone.now() + timedelta(hours=1),
                )
                
                # إرسال البريد
                reset_url = request.build_absolute_uri(
                    reverse('ecommerce:reset_password', args=[token])
                )
                
                try:
                    send_mail(
                        subject=_('إعادة تعيين كلمة المرور'),
                        message=f'''
مرحباً {user.first_name},

لقد طلبت إعادة تعيين كلمة المرور لحسابك.

اضغط على الرابط التالي لإعادة تعيين كلمة المرور:
{reset_url}

هذا الرابط صالح لمدة ساعة واحدة.

إذا لم تطلب إعادة تعيين كلمة المرور، تجاهل هذا البريد.

مع تحياتنا،
فريق المتجر
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=True,
                    )
                except:
                    pass
                
        except User.DoesNotExist:
            pass  # لا نكشف إذا كان البريد موجوداً أم لا
        
        messages.success(request, _('إذا كان البريد الإلكتروني مسجلاً، سيتم إرسال رابط إعادة تعيين كلمة المرور.'))
        return redirect('ecommerce:customer_login')
    
    return render(request, 'ecommerce/auth/forgot_password.html', context)


def reset_password(request, token):
    """صفحة إعادة تعيين كلمة المرور"""
    context = get_store_context()
    
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        if not reset_token.is_valid():
            messages.error(request, _('رابط إعادة تعيين كلمة المرور منتهي الصلاحية أو مستخدم.'))
            return redirect('ecommerce:forgot_password')
    except PasswordResetToken.DoesNotExist:
        messages.error(request, _('رابط إعادة تعيين كلمة المرور غير صالح.'))
        return redirect('ecommerce:forgot_password')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        if len(password) < 8:
            messages.error(request, _('كلمة المرور يجب أن تكون 8 أحرف على الأقل'))
        elif password != password_confirm:
            messages.error(request, _('كلمتا المرور غير متطابقتين'))
        else:
            user = reset_token.customer.user
            user.set_password(password)
            user.save()
            
            reset_token.used = True
            reset_token.save()
            
            messages.success(request, _('تم تغيير كلمة المرور بنجاح. يمكنك تسجيل الدخول الآن.'))
            return redirect('ecommerce:customer_login')
    
    context['token'] = token
    return render(request, 'ecommerce/auth/reset_password.html', context)


def verify_email(request, token):
    """تأكيد البريد الإلكتروني"""
    try:
        verification_token = EmailVerificationToken.objects.get(token=token)
        if verification_token.is_valid():
            customer = verification_token.customer
            customer.email_verified = True
            customer.save()
            
            verification_token.used = True
            verification_token.save()
            
            messages.success(request, _('تم تأكيد بريدك الإلكتروني بنجاح!'))
        else:
            messages.error(request, _('رابط التأكيد منتهي الصلاحية أو مستخدم.'))
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, _('رابط التأكيد غير صالح.'))
    
    return redirect('ecommerce:customer_account')


@login_required(login_url='ecommerce:customer_login')
def resend_verification(request):
    """إعادة إرسال بريد التأكيد"""
    if hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        if not customer.email_verified:
            send_verification_email(customer)
            messages.success(request, _('تم إرسال رابط التأكيد إلى بريدك الإلكتروني.'))
        else:
            messages.info(request, _('بريدك الإلكتروني مؤكد بالفعل.'))
    
    return redirect('ecommerce:customer_account')


def send_verification_email(customer):
    """إرسال بريد تأكيد البريد الإلكتروني"""
    token = secrets.token_urlsafe(32)
    EmailVerificationToken.objects.create(
        customer=customer,
        token=token,
        email=customer.user.email,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    
    try:
        from django.core.mail import send_mail
        verify_url = f"{settings.SITE_URL}/store/verify-email/{token}/"
        
        send_mail(
            subject=_('تأكيد البريد الإلكتروني'),
            message=f'''
مرحباً {customer.user.first_name},

شكراً لتسجيلك في متجرنا!

اضغط على الرابط التالي لتأكيد بريدك الإلكتروني:
{verify_url}

هذا الرابط صالح لمدة 24 ساعة.

مع تحياتنا،
فريق المتجر
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.user.email],
            fail_silently=True,
        )
    except:
        pass


# =====================================================
# Social Authentication Views
# =====================================================

def social_login_init(request, provider):
    """بدء عملية تسجيل الدخول الاجتماعي"""
    try:
        auth_provider = SocialAuthProvider.objects.get(provider=provider, is_active=True)
    except SocialAuthProvider.DoesNotExist:
        messages.error(request, _('مزود تسجيل الدخول غير متوفر.'))
        return redirect('ecommerce:customer_login')
    
    config = auth_provider.get_oauth_config()
    
    # إنشاء state للحماية من CSRF
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    request.session['oauth_provider'] = provider
    request.session['oauth_next'] = request.GET.get('next', '')
    
    # بناء URL الـ callback
    callback_url = request.build_absolute_uri(
        reverse('ecommerce:social_callback', args=[provider])
    )
    
    # بناء URL التفويض
    params = {
        'client_id': config['client_id'],
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': config['scopes'],
        'state': state,
    }
    
    # معاملات إضافية حسب المزود
    if provider == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'
    elif provider == 'facebook':
        params['auth_type'] = 'rerequest'
    
    auth_url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    
    return redirect(auth_url)


def social_callback(request, provider):
    """Callback من مزود تسجيل الدخول الاجتماعي"""
    # التحقق من الأخطاء
    error = request.GET.get('error')
    if error:
        error_description = request.GET.get('error_description', _('حدث خطأ أثناء تسجيل الدخول'))
        messages.error(request, error_description)
        return redirect('ecommerce:customer_login')
    
    # التحقق من state
    state = request.GET.get('state')
    session_state = request.session.get('oauth_state')
    
    if not state or state != session_state:
        messages.error(request, _('جلسة غير صالحة. حاول مرة أخرى.'))
        return redirect('ecommerce:customer_login')
    
    code = request.GET.get('code')
    if not code:
        messages.error(request, _('لم يتم استلام رمز التفويض.'))
        return redirect('ecommerce:customer_login')
    
    try:
        auth_provider = SocialAuthProvider.objects.get(provider=provider, is_active=True)
    except SocialAuthProvider.DoesNotExist:
        messages.error(request, _('مزود تسجيل الدخول غير متوفر.'))
        return redirect('ecommerce:customer_login')
    
    config = auth_provider.get_oauth_config()
    
    # بناء URL الـ callback
    callback_url = request.build_absolute_uri(
        reverse('ecommerce:social_callback', args=[provider])
    )
    
    # استبدال الكود بـ access token
    token_data = {
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'code': code,
        'redirect_uri': callback_url,
        'grant_type': 'authorization_code',
    }
    
    try:
        token_response = requests.post(
            config['token_url'],
            data=token_data,
            headers={'Accept': 'application/json'},
            timeout=30,
        )
        token_response.raise_for_status()
        tokens = token_response.json()
    except Exception as e:
        messages.error(request, _('فشل الحصول على رمز الوصول.'))
        return redirect('ecommerce:customer_login')
    
    access_token = tokens.get('access_token')
    if not access_token:
        messages.error(request, _('لم يتم استلام رمز الوصول.'))
        return redirect('ecommerce:customer_login')
    
    # الحصول على بيانات المستخدم
    try:
        user_info = get_social_user_info(provider, access_token, config)
    except Exception as e:
        messages.error(request, _('فشل الحصول على بيانات الحساب.'))
        return redirect('ecommerce:customer_login')
    
    if not user_info:
        messages.error(request, _('لم يتم استلام بيانات الحساب.'))
        return redirect('ecommerce:customer_login')
    
    # معالجة تسجيل الدخول أو التسجيل
    try:
        customer = process_social_login(provider, user_info, tokens)
        login(request, customer.user)
        
        # تسجيل النشاط في CRM
        log_crm_login(customer.user)
        
        messages.success(request, _('مرحباً بك!'))
        
        next_url = request.session.get('oauth_next', '')
        
        # تنظيف الجلسة
        for key in ['oauth_state', 'oauth_provider', 'oauth_next']:
            request.session.pop(key, None)
        
        if next_url:
            return redirect(next_url)
        return redirect('ecommerce:store_home')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('ecommerce:customer_login')


def get_social_user_info(provider, access_token, config):
    """الحصول على بيانات المستخدم من المزود"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    if provider == 'google':
        response = requests.get(config['userinfo_url'], headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {
            'id': data.get('sub'),
            'email': data.get('email'),
            'name': data.get('name'),
            'first_name': data.get('given_name', ''),
            'last_name': data.get('family_name', ''),
            'picture': data.get('picture'),
            'verified_email': data.get('email_verified', False),
        }
    
    elif provider == 'facebook':
        response = requests.get(
            'https://graph.facebook.com/me?fields=id,name,email,first_name,last_name,picture',
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return {
            'id': data.get('id'),
            'email': data.get('email'),
            'name': data.get('name'),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'picture': data.get('picture', {}).get('data', {}).get('url'),
        }
    
    elif provider == 'twitter':
        response = requests.get(
            'https://api.twitter.com/2/users/me?user.fields=profile_image_url',
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json().get('data', {})
        name_parts = data.get('name', '').split(' ', 1)
        return {
            'id': data.get('id'),
            'name': data.get('name'),
            'first_name': name_parts[0] if name_parts else '',
            'last_name': name_parts[1] if len(name_parts) > 1 else '',
            'picture': data.get('profile_image_url'),
            'username': data.get('username'),
        }
    
    elif provider == 'github':
        response = requests.get(config['userinfo_url'], headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # الحصول على البريد الإلكتروني
        email_response = requests.get(
            'https://api.github.com/user/emails',
            headers=headers,
            timeout=30,
        )
        emails = email_response.json()
        primary_email = next((e['email'] for e in emails if e.get('primary')), None)
        
        name_parts = (data.get('name') or '').split(' ', 1)
        return {
            'id': str(data.get('id')),
            'email': primary_email or data.get('email'),
            'name': data.get('name'),
            'first_name': name_parts[0] if name_parts else data.get('login'),
            'last_name': name_parts[1] if len(name_parts) > 1 else '',
            'picture': data.get('avatar_url'),
        }
    
    elif provider == 'microsoft':
        response = requests.get(config['userinfo_url'], headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {
            'id': data.get('id'),
            'email': data.get('mail') or data.get('userPrincipalName'),
            'name': data.get('displayName'),
            'first_name': data.get('givenName', ''),
            'last_name': data.get('surname', ''),
        }
    
    elif provider == 'apple':
        # Apple تعيد البيانات في id_token
        # نحتاج لفك JWT
        return None
    
    return None


def process_social_login(provider, user_info, tokens):
    """معالجة تسجيل الدخول أو التسجيل الاجتماعي"""
    provider_user_id = str(user_info.get('id'))
    email = user_info.get('email', '').lower() if user_info.get('email') else None
    
    # البحث عن حساب اجتماعي موجود
    try:
        social_account = SocialAccount.objects.get(
            provider=provider,
            provider_user_id=provider_user_id,
        )
        # تحديث التوكنات
        social_account.access_token = tokens.get('access_token', '')
        social_account.refresh_token = tokens.get('refresh_token', '')
        if tokens.get('expires_in'):
            social_account.token_expires_at = timezone.now() + timedelta(seconds=int(tokens['expires_in']))
        social_account.raw_data = user_info
        social_account.save()
        
        return social_account.customer
        
    except SocialAccount.DoesNotExist:
        pass
    
    # البحث عن مستخدم بنفس البريد الإلكتروني
    customer = None
    if email:
        try:
            user = User.objects.get(email=email)
            if hasattr(user, 'customer_profile'):
                customer = user.customer_profile
        except User.DoesNotExist:
            pass
    
    with transaction.atomic():
        if not customer:
            # إنشاء مستخدم وعميل جديد
            username = f"{provider}_{provider_user_id}"
            user = User.objects.create(
                username=username,
                email=email or f"{username}@social.local",
                first_name=user_info.get('first_name', ''),
                last_name=user_info.get('last_name', ''),
            )
            # تعيين كلمة مرور عشوائية (لن يستخدمها)
            user.set_password(secrets.token_urlsafe(32))
            user.save()
            
            customer = Customer.objects.create(
                user=user,
                email_verified=bool(user_info.get('verified_email')),
            )
            
            # تحميل الصورة إذا وجدت
            if user_info.get('picture'):
                customer.avatar = user_info['picture']  # يمكن تحسين هذا لتحميل الصورة
                customer.save()
        
        # ربط الحساب الاجتماعي
        social_account = SocialAccount.objects.create(
            customer=customer,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email or '',
            name=user_info.get('name', ''),
            picture_url=user_info.get('picture', ''),
            access_token=tokens.get('access_token', ''),
            refresh_token=tokens.get('refresh_token', ''),
            raw_data=user_info,
        )
        
        if tokens.get('expires_in'):
            social_account.token_expires_at = timezone.now() + timedelta(seconds=int(tokens['expires_in']))
            social_account.save()
    
    return customer


@login_required(login_url='ecommerce:customer_login')
def link_social_account(request, provider):
    """ربط حساب اجتماعي بحساب موجود"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, _('يجب أن تكون عميلاً لربط حساب اجتماعي.'))
        return redirect('ecommerce:customer_login')
    
    request.session['linking_account'] = True
    return social_login_init(request, provider)


@login_required(login_url='ecommerce:customer_login')
def unlink_social_account(request, provider):
    """إلغاء ربط حساب اجتماعي"""
    if not hasattr(request.user, 'customer_profile'):
        return JsonResponse({'error': _('غير مصرح')}, status=403)
    
    customer = request.user.customer_profile
    
    # التحقق من أن العميل لديه طريقة تسجيل دخول أخرى
    social_accounts_count = customer.social_accounts.count()
    has_password = request.user.has_usable_password()
    
    if social_accounts_count <= 1 and not has_password:
        messages.error(request, _('لا يمكنك إلغاء ربط آخر طريقة تسجيل دخول. أضف كلمة مرور أولاً.'))
        return redirect('ecommerce:customer_account')
    
    try:
        social_account = customer.social_accounts.get(provider=provider)
        social_account.delete()
        messages.success(request, _('تم إلغاء ربط الحساب بنجاح.'))
    except SocialAccount.DoesNotExist:
        messages.error(request, _('الحساب غير مرتبط.'))
    
    return redirect('ecommerce:customer_account')


# =====================================================
# Customer Account Views
# =====================================================

@login_required(login_url='ecommerce:customer_login')
def customer_account(request):
    """صفحة حساب العميل"""
    if not hasattr(request.user, 'customer_profile'):
        Customer.objects.create(user=request.user)
    
    context = get_store_context()
    context['customer'] = request.user.customer_profile
    context['addresses'] = request.user.customer_profile.addresses.all()
    context['social_accounts'] = request.user.customer_profile.social_accounts.all()
    
    return render(request, 'ecommerce/auth/account.html', context)


@login_required(login_url='ecommerce:customer_login')
def update_profile(request):
    """تحديث الملف الشخصي"""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:customer_login')
    
    if request.method == 'POST':
        user = request.user
        customer = user.customer_profile
        
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()
        
        customer.phone = request.POST.get('phone', customer.phone)
        customer.date_of_birth = request.POST.get('date_of_birth') or None
        customer.gender = request.POST.get('gender', customer.gender)
        customer.newsletter_subscribed = request.POST.get('newsletter_subscribed') == 'on'
        customer.sms_notifications = request.POST.get('sms_notifications') == 'on'
        
        if 'avatar' in request.FILES:
            customer.avatar = request.FILES['avatar']
        
        customer.save()
        
        messages.success(request, _('تم تحديث البيانات بنجاح'))
    
    return redirect('ecommerce:customer_account')


@login_required(login_url='ecommerce:customer_login')
def change_password(request):
    """تغيير كلمة المرور"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not request.user.check_password(current_password):
            messages.error(request, _('كلمة المرور الحالية غير صحيحة'))
        elif len(new_password) < 8:
            messages.error(request, _('كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل'))
        elif new_password != confirm_password:
            messages.error(request, _('كلمتا المرور غير متطابقتين'))
        else:
            request.user.set_password(new_password)
            request.user.save()
            
            # إعادة تسجيل الدخول
            login(request, request.user)
            
            messages.success(request, _('تم تغيير كلمة المرور بنجاح'))
    
    return redirect('ecommerce:customer_account')


@login_required(login_url='ecommerce:customer_login')
def set_password(request):
    """تعيين كلمة مرور للحسابات الاجتماعية"""
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if len(new_password) < 8:
            messages.error(request, _('كلمة المرور يجب أن تكون 8 أحرف على الأقل'))
        elif new_password != confirm_password:
            messages.error(request, _('كلمتا المرور غير متطابقتين'))
        else:
            request.user.set_password(new_password)
            request.user.save()
            
            login(request, request.user)
            
            messages.success(request, _('تم تعيين كلمة المرور بنجاح'))
    
    return redirect('ecommerce:customer_account')


@login_required(login_url='ecommerce:customer_login')
def manage_addresses(request):
    """إدارة عناوين العميل"""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:customer_login')
    
    customer = request.user.customer_profile
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            CustomerAddress.objects.create(
                customer=customer,
                address_type=request.POST.get('address_type', 'home'),
                full_name=request.POST.get('full_name'),
                phone=request.POST.get('phone'),
                address_line1=request.POST.get('address_line1'),
                address_line2=request.POST.get('address_line2', ''),
                city=request.POST.get('city'),
                state=request.POST.get('state', ''),
                country=request.POST.get('country', 'مصر'),
                postal_code=request.POST.get('postal_code', ''),
                is_default=request.POST.get('is_default') == 'on',
            )
            messages.success(request, _('تم إضافة العنوان بنجاح'))
        
        elif action == 'delete':
            address_id = request.POST.get('address_id')
            try:
                address = customer.addresses.get(id=address_id)
                address.delete()
                messages.success(request, _('تم حذف العنوان بنجاح'))
            except CustomerAddress.DoesNotExist:
                messages.error(request, _('العنوان غير موجود'))
        
        elif action == 'set_default':
            address_id = request.POST.get('address_id')
            try:
                address = customer.addresses.get(id=address_id)
                address.is_default = True
                address.save()
                messages.success(request, _('تم تعيين العنوان الافتراضي'))
            except CustomerAddress.DoesNotExist:
                messages.error(request, _('العنوان غير موجود'))
    
    return redirect('ecommerce:customer_account')


@login_required(login_url='ecommerce:customer_login')
def customer_orders(request):
    """صفحة طلبات العميل"""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:customer_login')
    
    context = get_store_context()
    context['customer'] = request.user.customer_profile
    context['orders'] = request.user.ecommerce_orders.all().order_by('-created_at')
    
    return render(request, 'ecommerce/auth/orders.html', context)


@login_required(login_url='ecommerce:customer_login')
def customer_wishlist(request):
    """صفحة قائمة الأمنيات"""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('ecommerce:customer_login')
    
    context = get_store_context()
    context['customer'] = request.user.customer_profile
    context['wishlist'] = request.user.ecommerce_wishlists.all()
    
    return render(request, 'ecommerce/auth/wishlist.html', context)
