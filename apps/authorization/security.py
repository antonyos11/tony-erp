"""
الأمان المتقدم — RITA ERP Sprint 25
Brute Force Protection + Login/Logout Logging + 2FA
"""
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from apps.authorization.services.audit import log_action, get_client_ip


# ─────────────────────────────────────────────────────────────
# Brute Force Protection
# ─────────────────────────────────────────────────────────────
BRUTE_FORCE_MAX_ATTEMPTS = 5
BRUTE_FORCE_LOCKOUT_MINUTES = 30
BRUTE_FORCE_WINDOW_MINUTES = 15


def get_brute_force_cache_key(username: str, ip: str) -> str:
    return f"bf_attempts:{username}:{ip}"


def get_lockout_cache_key(username: str, ip: str) -> str:
    return f"bf_locked:{username}:{ip}"


def check_brute_force(username: str, ip: str) -> dict:
    """
    التحقق من حالة Brute Force للمستخدم.
    إرجاع: {'locked': bool, 'attempts': int, 'remaining_minutes': int}
    """
    lock_key = get_lockout_cache_key(username, ip)
    locked_until = cache.get(lock_key)

    if locked_until:
        remaining = max(0, int((locked_until - timezone.now()).total_seconds() / 60))
        return {'locked': True, 'attempts': BRUTE_FORCE_MAX_ATTEMPTS, 'remaining_minutes': remaining}

    attempt_key = get_brute_force_cache_key(username, ip)
    attempts = cache.get(attempt_key, 0)
    return {'locked': False, 'attempts': attempts, 'remaining_minutes': 0}


def record_failed_attempt(username: str, ip: str):
    """تسجيل محاولة دخول فاشلة — يُقفل الحساب بعد 5 محاولات"""
    attempt_key = get_brute_force_cache_key(username, ip)
    attempts = cache.get(attempt_key, 0) + 1
    cache.set(attempt_key, attempts, timeout=BRUTE_FORCE_WINDOW_MINUTES * 60)

    if attempts >= BRUTE_FORCE_MAX_ATTEMPTS:
        lock_key = get_lockout_cache_key(username, ip)
        unlock_time = timezone.now() + timezone.timedelta(minutes=BRUTE_FORCE_LOCKOUT_MINUTES)
        cache.set(lock_key, unlock_time, timeout=BRUTE_FORCE_LOCKOUT_MINUTES * 60)
        # مسح عداد المحاولات
        cache.delete(attempt_key)

    return attempts


def reset_brute_force(username: str, ip: str):
    """إعادة ضبط عداد المحاولات بعد تسجيل دخول ناجح"""
    cache.delete(get_brute_force_cache_key(username, ip))
    cache.delete(get_lockout_cache_key(username, ip))


def unlock_account(username: str, ip: str = None):
    """فتح قفل الحساب يدويًا (بواسطة المدير)"""
    if ip:
        reset_brute_force(username, ip)
    else:
        # فتح من كل الـ IPs (بالبحث في الكاش)
        pattern = f"bf_locked:{username}:*"
        # للـ Redis يمكن استخدام keys pattern, هنا نستخدم طريقة بسيطة
        cache.delete(get_lockout_cache_key(username, ''))


# ─────────────────────────────────────────────────────────────
# Login / Logout Signal Handlers
# ─────────────────────────────────────────────────────────────

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """تسجيل حدث الدخول الناجح"""
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')

    # إعادة ضبط محاولات Brute Force
    reset_brute_force(user.username, ip)

    log_action(
        user=user,
        action='login',
        module='authorization',
        model_name='User',
        object_id=str(user.pk),
        description=f"تسجيل دخول ناجح — {user.username}",
        new_value={'user_agent': ua[:255], 'ip': ip},
        ip_address=ip,
        branch=getattr(user, 'branch', None),
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """تسجيل حدث الخروج"""
    if not user:
        return
    ip = get_client_ip(request)

    log_action(
        user=user,
        action='logout',
        module='authorization',
        model_name='User',
        object_id=str(user.pk),
        description=f"تسجيل خروج — {user.username}",
        ip_address=ip,
        branch=getattr(user, 'branch', None),
    )


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """تسجيل محاولة دخول فاشلة + Brute Force"""
    username = credentials.get('username', '')
    ip = get_client_ip(request)
    attempts = record_failed_attempt(username, ip)

    # Try to get user object
    from apps.core.models import User as EUser
    try:
        user = EUser.objects.get(username=username)
    except EUser.DoesNotExist:
        user = None

    log_action(
        user=user,
        action='failed_login',
        module='authorization',
        model_name='User',
        object_id=username,
        description=f"محاولة دخول فاشلة ({attempts}/{BRUTE_FORCE_MAX_ATTEMPTS}) — {username}",
        new_value={'attempts': attempts, 'ip': ip, 'locked': attempts >= BRUTE_FORCE_MAX_ATTEMPTS},
        ip_address=ip,
    )


# ─────────────────────────────────────────────────────────────
# Two-Factor Authentication (اختياري)
# ─────────────────────────────────────────────────────────────
import secrets
import string

def generate_totp_secret() -> str:
    """توليد سر 2FA"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


def generate_otp_code() -> str:
    """توليد كود OTP مكوّن من 6 أرقام"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def send_otp_email(user, otp_code: str):
    """إرسال كود OTP بالبريد الإلكتروني"""
    from django.core.mail import send_mail
    from django.conf import settings
    send_mail(
        subject='RITA ERP — كود التحقق الثنائي',
        message=f'كود التحقق الخاص بك: {otp_code}\nصالح لمدة 10 دقائق.',
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@rita-erp.com'),
        recipient_list=[user.email],
        fail_silently=True,
    )


def store_otp(user_id: str, otp_code: str, expiry_minutes: int = 10):
    """حفظ كود OTP في الكاش"""
    key = f"otp_2fa:{user_id}"
    cache.set(key, otp_code, timeout=expiry_minutes * 60)


def verify_otp(user_id: str, code: str) -> bool:
    """التحقق من صحة كود OTP"""
    key = f"otp_2fa:{user_id}"
    stored = cache.get(key)
    if stored and stored == code:
        cache.delete(key)
        return True
    return False


def is_2fa_enabled(user) -> bool:
    """هل المستخدم فعّل المصادقة الثنائية؟"""
    return getattr(user, 'two_factor_enabled', False)
