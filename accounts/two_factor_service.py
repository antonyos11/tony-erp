"""
خدمات المصادقة الثنائية - نسخة مبسطة
"""

import pyotp
import qrcode
from io import BytesIO
import base64
import hashlib
import json
import secrets
import string
from django.utils import timezone
from datetime import timedelta


class TOTPService:
    """خدمة TOTP"""
    
    @staticmethod
    def generate_secret():
        """توليد سر جديد"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret, username, issuer='Tony ERP'):
        """توليد URI لـ QR Code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code(secret, username):
        """توليد QR Code كـ Base64"""
        uri = TOTPService.get_totp_uri(secret, username)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_token(secret, token):
        """التحقق من رمز TOTP"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)


class BackupCodesService:
    """خدمة رموز النسخ الاحتياطي"""
    HASH_ALGO = 'sha256'

    @staticmethod
    def hash_code(code: str) -> str:
        """إرجاع تجزئة آمنة للرمز (hex)"""
        return hashlib.new(BackupCodesService.HASH_ALGO, code.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_backup_codes(count=10):
        """توليد رموز نسخ احتياطي بصيغة XXXX-XXXX"""
        codes = []
        for _ in range(count):
            code = '-'.join([
                secrets.token_hex(2).upper() for _ in range(2)
            ])
            codes.append(code)
        return codes
    
    @staticmethod
    def verify_backup_code(code: str, codes_store):
        """تحقق من الرمز مقابل قائمة مجزأة أو نموذج TwoFactorAuth.

        - إذا كان codes_store قائمة مجزأة، يرجع التجزئة إذا وُجد (ويزيلها من القائمة).
        - إذا كان نموذج TwoFactorAuth، يتحقق ويحذف الرمز من التخزين.
        """
        hashed = BackupCodesService.hash_code(code)
        # قائمة مجزأة (تستخدمها الاختبارات مباشرة)
        if isinstance(codes_store, list):
            if hashed in codes_store:
                codes_store.remove(hashed)
                return hashed
            return None
        # نموذج TwoFactorAuth
        try:
            backup_codes = json.loads(codes_store.backup_codes or '[]')
            if hashed in backup_codes:
                backup_codes.remove(hashed)
                codes_store.backup_codes = json.dumps(backup_codes)
                codes_store.save(update_fields=['backup_codes'])
                return True
        except (json.JSONDecodeError, AttributeError):
            pass
        return False


class LoginAttemptTracker:
    """تتبع محاولات تسجيل الدخول"""
    
    MAX_ATTEMPTS = 15  # زيادة عدد المحاولات المسموحة (كان 5)
    LOCKOUT_TIME = 5 * 60  # 5 دقائق (كان 30 دقيقة)
    
    @staticmethod
    def _is_disabled():
        """تعطيل تتبع المحاولات في بيئة الاختبار أو التطوير"""
        from django.conf import settings
        return getattr(settings, 'DISABLE_LOGIN_LOCKOUT', False) or getattr(settings, 'TESTING', False)
    
    @staticmethod
    def record_attempt(username, ip_address, success, method='password', user=None, user_agent='', failure_reason=''):
        """تسجيل محاولة تسجيل دخول مع ربط اختياري بالمستخدم."""
        from .models import LoginAttempt
        LoginAttempt.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            method=method,
            failure_reason=failure_reason,
        )
    
    @staticmethod
    def is_locked_out(username, ip_address=None):
        """التحقق من حظر الحساب"""
        if LoginAttemptTracker._is_disabled():
            return False
        from .models import LoginAttempt
        cutoff = timezone.now() - timedelta(seconds=LoginAttemptTracker.LOCKOUT_TIME)
        qs = LoginAttempt.objects.filter(
            username=username,
            success=False,
            timestamp__gte=cutoff
        )
        if ip_address:
            qs = qs.filter(ip_address=ip_address)
        failed_attempts = qs.count()
        return failed_attempts >= LoginAttemptTracker.MAX_ATTEMPTS
    
    @staticmethod
    def get_lockout_time_remaining(username, ip_address=None):
        """الوقت المتبقي للحظر"""
        from .models import LoginAttempt
        cutoff = timezone.now() - timedelta(seconds=LoginAttemptTracker.LOCKOUT_TIME)
        qs = LoginAttempt.objects.filter(
            username=username,
            success=False,
            timestamp__gte=cutoff
        )
        if ip_address:
            qs = qs.filter(ip_address=ip_address)
        last_attempt = qs.order_by('-timestamp').first()
        
        if last_attempt:
            elapsed = (timezone.now() - last_attempt.timestamp).total_seconds()
            return max(0, LoginAttemptTracker.LOCKOUT_TIME - int(elapsed))
        return 0

    @staticmethod
    def get_failed_attempts(username, ip_address=None):
        """إرجاع عدد المحاولات الفاشلة ضمن نافذة القفل الحالية."""
        from .models import LoginAttempt
        cutoff = timezone.now() - timedelta(seconds=LoginAttemptTracker.LOCKOUT_TIME)
        qs = LoginAttempt.objects.filter(
            username=username,
            success=False,
            timestamp__gte=cutoff
        )
        if ip_address:
            qs = qs.filter(ip_address=ip_address)
        return qs.count()


class TwoFactorAuthService:
    """خدمة المصادقة الثنائية الرئيسية"""
    
    @staticmethod
    def is_2fa_enabled(user):
        """التحقق من تفعيل 2FA"""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user)
            return tfa.is_enabled
        except TwoFactorAuth.DoesNotExist:
            return False
    
    @staticmethod
    def setup_2fa(user):
        """متوافق مع الواجهات القديمة - يستدعي الإعداد الكامل لـ TOTP."""
        return TwoFactorAuthService.setup_totp_for_user(user)

    @staticmethod
    def setup_totp_for_user(user):
        """إعداد TOTP وحفظ الرموز الاحتياطية (مجزأة) مع إرجاع النسخ الخام للعرض."""
        from .models import TwoFactorAuth
        tfa, _ = TwoFactorAuth.objects.get_or_create(user=user)
        if not tfa.totp_secret:
            tfa.totp_secret = TOTPService.generate_secret()
        raw_backup_codes = BackupCodesService.generate_backup_codes()
        hashed_codes = [BackupCodesService.hash_code(c) for c in raw_backup_codes]
        tfa.backup_codes = json.dumps(hashed_codes)
        tfa.is_enabled = False
        tfa.save(update_fields=['totp_secret', 'backup_codes', 'is_enabled'])

        qr_code = TOTPService.generate_qr_code(tfa.totp_secret, user.username)
        return {
            'secret': tfa.totp_secret,
            'qr_code': qr_code,
            'backup_codes': raw_backup_codes,
        }
    
    @staticmethod
    def enable_2fa(user, backup_codes):
        """تفعيل 2FA"""
        from .models import TwoFactorAuth
        tfa = TwoFactorAuth.objects.get(user=user)
        tfa.is_enabled = True
        tfa.backup_codes = json.dumps([BackupCodesService.hash_code(c) for c in backup_codes])
        tfa.enabled_at = timezone.now()
        tfa.save()

    @staticmethod
    def verify_and_enable_totp(user, token):
        """تحقق من رمز TOTP الحالي وتفعيل 2FA عند النجاح."""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user)
        except TwoFactorAuth.DoesNotExist:
            return False
        if not tfa.totp_secret:
            return False
        if not TOTPService.verify_token(tfa.totp_secret, token):
            return False
        tfa.is_enabled = True
        tfa.enabled_at = timezone.now()
        tfa.save(update_fields=['is_enabled', 'enabled_at'])
        return True
    
    @staticmethod
    def verify_login_token(user, token, token_type='totp'):
        """التحقق من رمز تسجيل الدخول"""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user, is_enabled=True)
            
            if token_type in ('backup', 'backup_code'):
                result = BackupCodesService.verify_backup_code(token, tfa)
                return bool(result)
            return TOTPService.verify_token(tfa.totp_secret, token)
        except TwoFactorAuth.DoesNotExist:
            return False
    
    @staticmethod
    def get_remaining_backup_codes_count(user):
        """عدد رموز النسخ الاحتياطي المتبقية"""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user)
            backup_codes = json.loads(tfa.backup_codes or '[]')
            return len(backup_codes)
        except (TwoFactorAuth.DoesNotExist, json.JSONDecodeError):
            return 0
    
    @staticmethod
    def disable_2fa(user):
        """تعطيل 2FA"""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user)
            tfa.is_enabled = False
            tfa.save(update_fields=['is_enabled'])
            return True
        except TwoFactorAuth.DoesNotExist:
            return False
    
    @staticmethod
    def regenerate_backup_codes(user):
        """إعادة توليد رموز النسخ الاحتياطي"""
        from .models import TwoFactorAuth
        try:
            tfa = TwoFactorAuth.objects.get(user=user)
            raw_codes = BackupCodesService.generate_backup_codes()
            hashed_codes = [BackupCodesService.hash_code(c) for c in raw_codes]
            tfa.backup_codes = json.dumps(hashed_codes)
            tfa.save(update_fields=['backup_codes'])
            return raw_codes
        except TwoFactorAuth.DoesNotExist:
            return []


class OTPService:
    """خدمة OTP (للمستقبل - SMS/Email)"""
    _store = {}
    DEFAULT_TTL = 300  # ثواني

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        length = max(4, int(length or 6))
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @classmethod
    def store_otp(cls, user_id, otp, ttl: int | None = None):
        expires_at = timezone.now() + timedelta(seconds=ttl or cls.DEFAULT_TTL)
        cls._store[user_id] = {'otp': otp, 'expires_at': expires_at}

    @classmethod
    def verify_otp(cls, user_id, otp):
        data = cls._store.get(user_id)
        if not data:
            return False
        if timezone.now() > data['expires_at']:
            cls._store.pop(user_id, None)
            return False
        if data['otp'] == otp:
            cls._store.pop(user_id, None)
            return True
        return False
