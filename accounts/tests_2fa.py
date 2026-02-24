"""
اختبارات شاملة لنظام المصادقة الثنائية (Two-Factor Authentication)
"""

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
try:
    import pyotp
except ImportError:
    pyotp = None  # سيتم تخطي الاختبارات إذا لم يكن مثبتاً
import json

from accounts.models import TwoFactorAuth, LoginAttempt, TrustedDevice
from accounts.two_factor_service import (
    TOTPService,
    BackupCodesService,
    OTPService,
    LoginAttemptTracker,
    TwoFactorAuthService
)


class TOTPServiceTests(TestCase):
    """اختبارات خدمة TOTP"""
    
    def test_generate_secret(self):
        """اختبار توليد السر"""
        secret = TOTPService.generate_secret()
        self.assertIsNotNone(secret)
        self.assertEqual(len(secret), 32)
    
    def test_get_totp_uri(self):
        """اختبار توليد URI"""
        secret = TOTPService.generate_secret()
        uri = TOTPService.get_totp_uri(secret, 'testuser')
        
        self.assertIn('otpauth://totp/', uri)
        self.assertIn('testuser', uri)
        self.assertIn(secret, uri)
    
    def test_generate_qr_code(self):
        """اختبار توليد QR Code"""
        secret = TOTPService.generate_secret()
        qr_code = TOTPService.generate_qr_code(secret, 'testuser')
        
        self.assertIsNotNone(qr_code)
        self.assertTrue(qr_code.startswith('data:image/png;base64,'))
    
    def test_verify_valid_token(self):
        """اختبار التحقق من رمز صحيح"""
        secret = TOTPService.generate_secret()
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        
        is_valid = TOTPService.verify_token(secret, current_token)
        self.assertTrue(is_valid)
    
    def test_verify_invalid_token(self):
        """اختبار رفض رمز خاطئ"""
        secret = TOTPService.generate_secret()
        
        is_valid = TOTPService.verify_token(secret, '000000')
        self.assertFalse(is_valid)
    
    def test_verify_expired_token(self):
        """اختبار رفض رمز منتهي الصلاحية (محاكاة)"""
        secret = TOTPService.generate_secret()
        
        # رمز عشوائي (سيكون منتهي)
        is_valid = TOTPService.verify_token(secret, '123456')
        self.assertFalse(is_valid)


class BackupCodesServiceTests(TestCase):
    """اختبارات خدمة رموز النسخ الاحتياطي"""
    
    def test_generate_backup_codes_default_count(self):
        """اختبار توليد 10 رموز افتراضياً"""
        codes = BackupCodesService.generate_backup_codes()
        self.assertEqual(len(codes), 10)
    
    def test_generate_backup_codes_custom_count(self):
        """اختبار توليد عدد مخصص من الرموز"""
        codes = BackupCodesService.generate_backup_codes(5)
        self.assertEqual(len(codes), 5)
    
    def test_backup_code_format(self):
        """اختبار تنسيق الرمز XXXX-XXXX"""
        codes = BackupCodesService.generate_backup_codes(1)
        code = codes[0]
        
        self.assertEqual(len(code), 9)  # 4 + 1 (-) + 4
        self.assertIn('-', code)
        
        parts = code.split('-')
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0]), 4)
        self.assertEqual(len(parts[1]), 4)
    
    def test_hash_code(self):
        """اختبار تشفير الرمز"""
        code = "ABCD-1234"
        hashed = BackupCodesService.hash_code(code)
        
        self.assertIsNotNone(hashed)
        self.assertEqual(len(hashed), 64)  # SHA-256 hex
        self.assertNotEqual(code, hashed)
    
    def test_verify_valid_backup_code(self):
        """اختبار التحقق من رمز صحيح"""
        code = "ABCD-1234"
        hashed_code = BackupCodesService.hash_code(code)
        hashed_codes = [hashed_code]
        
        result = BackupCodesService.verify_backup_code(code, hashed_codes)
        self.assertIsNotNone(result)
        self.assertEqual(result, hashed_code)
    
    def test_verify_invalid_backup_code(self):
        """اختبار رفض رمز خاطئ"""
        code = "ABCD-1234"
        wrong_code = "WXYZ-9999"
        hashed_code = BackupCodesService.hash_code(code)
        hashed_codes = [hashed_code]
        
        result = BackupCodesService.verify_backup_code(wrong_code, hashed_codes)
        self.assertIsNone(result)
    
    def test_backup_codes_uniqueness(self):
        """اختبار عدم تكرار الرموز"""
        codes = BackupCodesService.generate_backup_codes(20)
        unique_codes = set(codes)
        self.assertEqual(len(codes), len(unique_codes))


class OTPServiceTests(TestCase):
    """اختبارات خدمة OTP عبر البريد"""
    
    def test_generate_otp_default_length(self):
        """اختبار توليد OTP بطول افتراضي"""
        otp = OTPService.generate_otp()
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
    
    def test_generate_otp_custom_length(self):
        """اختبار توليد OTP بطول مخصص"""
        otp = OTPService.generate_otp(8)
        self.assertEqual(len(otp), 8)
        self.assertTrue(otp.isdigit())
    
    def test_store_and_verify_otp(self):
        """اختبار حفظ والتحقق من OTP"""
        user_id = 1
        otp = "123456"
        
        OTPService.store_otp(user_id, otp)
        
        is_valid = OTPService.verify_otp(user_id, otp)
        self.assertTrue(is_valid)
        
        # يجب حذف OTP بعد الاستخدام
        is_valid_again = OTPService.verify_otp(user_id, otp)
        self.assertFalse(is_valid_again)
    
    def test_verify_wrong_otp(self):
        """اختبار رفض OTP خاطئ"""
        user_id = 1
        otp = "123456"
        wrong_otp = "999999"
        
        OTPService.store_otp(user_id, otp)
        
        is_valid = OTPService.verify_otp(user_id, wrong_otp)
        self.assertFalse(is_valid)


class LoginAttemptTrackerTests(TestCase):
    """اختبارات نظام تتبع محاولات الدخول"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_record_successful_attempt(self):
        """اختبار تسجيل محاولة ناجحة"""
        LoginAttemptTracker.record_attempt(
            user=self.user,
            username='testuser',
            ip_address='192.168.1.1',
            success=True,
            method='password'
        )
        
        attempts = LoginAttempt.objects.filter(user=self.user)
        self.assertEqual(attempts.count(), 1)
        
        attempt = attempts.first()
        self.assertTrue(attempt.success)
        self.assertEqual(attempt.method, 'password')
    
    def test_record_failed_attempt(self):
        """اختبار تسجيل محاولة فاشلة"""
        LoginAttemptTracker.record_attempt(
            username='testuser',
            ip_address='192.168.1.1',
            success=False,
            method='password'
        )
        
        attempts = LoginAttempt.objects.filter(username='testuser')
        self.assertEqual(attempts.count(), 1)
        
        attempt = attempts.first()
        self.assertFalse(attempt.success)
    
    def test_get_failed_attempts_count(self):
        """اختبار عد المحاولات الفاشلة"""
        for i in range(3):
            LoginAttemptTracker.record_attempt(
                username='testuser',
                ip_address='192.168.1.1',
                success=False,
                method='password'
            )
        
        count = LoginAttemptTracker.get_failed_attempts('testuser', '192.168.1.1')
        self.assertEqual(count, 3)
    
    @override_settings(TESTING=False, DISABLE_LOGIN_LOCKOUT=False)
    def test_lockout_after_max_attempts(self):
        """اختبار القفل بعد الوصول للحد الأقصى"""
        max_attempts = LoginAttemptTracker.MAX_ATTEMPTS
        for i in range(max_attempts):
            LoginAttemptTracker.record_attempt(
                username='testuser',
                ip_address='192.168.1.1',
                success=False,
                method='password'
            )
        
        is_locked = LoginAttemptTracker.is_locked_out('testuser', '192.168.1.1')
        self.assertTrue(is_locked)
    
    def test_no_lockout_before_max_attempts(self):
        """اختبار عدم القفل قبل الحد الأقصى"""
        # 4 محاولات فقط
        for i in range(4):
            LoginAttemptTracker.record_attempt(
                username='testuser',
                ip_address='192.168.1.1',
                success=False,
                method='password'
            )
        
        is_locked = LoginAttemptTracker.is_locked_out('testuser', '192.168.1.1')
        self.assertFalse(is_locked)
    
    def test_lockout_time_remaining(self):
        """اختبار حساب الوقت المتبقي للقفل"""
        for i in range(5):
            LoginAttemptTracker.record_attempt(
                username='testuser',
                ip_address='192.168.1.1',
                success=False,
                method='password'
            )
        
        time_remaining = LoginAttemptTracker.get_lockout_time_remaining(
            'testuser', '192.168.1.1'
        )
        
        self.assertIsNotNone(time_remaining)
        self.assertGreater(time_remaining, 0)
        self.assertLessEqual(time_remaining, 30 * 60)  # 30 دقيقة


class TwoFactorAuthServiceTests(TestCase):
    """اختبارات الخدمة الرئيسية للمصادقة الثنائية"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_setup_totp_for_user(self):
        """اختبار إعداد TOTP لمستخدم"""
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        
        self.assertIn('secret', result)
        self.assertIn('qr_code', result)
        self.assertIn('backup_codes', result)
        
        self.assertEqual(len(result['backup_codes']), 10)
        
        # التحقق من حفظ في قاعدة البيانات
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertIsNotNone(two_factor.totp_secret)
        self.assertFalse(two_factor.is_enabled)  # لم يتم التفعيل بعد
    
    def test_verify_and_enable_totp(self):
        """اختبار التحقق وتفعيل TOTP"""
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        secret = result['secret']
        
        # توليد رمز صحيح
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        
        # التحقق والتفعيل
        success = TwoFactorAuthService.verify_and_enable_totp(self.user, current_token)
        self.assertTrue(success)
        
        # التحقق من التفعيل في قاعدة البيانات
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertTrue(two_factor.is_enabled)
        self.assertIsNotNone(two_factor.enabled_at)
    
    def test_verify_login_with_totp(self):
        """اختبار التحقق من تسجيل الدخول بـ TOTP"""
        # إعداد وتفعيل
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        secret = result['secret']
        
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        TwoFactorAuthService.verify_and_enable_totp(self.user, current_token)
        
        # التحقق من تسجيل الدخول
        new_token = totp.now()
        is_valid = TwoFactorAuthService.verify_login_token(
            self.user, new_token, 'totp'
        )
        self.assertTrue(is_valid)
    
    def test_verify_login_with_backup_code(self):
        """اختبار التحقق من تسجيل الدخول برمز احتياطي"""
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        backup_codes = result['backup_codes']
        
        secret = result['secret']
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        TwoFactorAuthService.verify_and_enable_totp(self.user, current_token)
        
        # استخدام رمز احتياطي
        backup_code = backup_codes[0]
        is_valid = TwoFactorAuthService.verify_login_token(
            self.user, backup_code, 'backup_code'
        )
        self.assertTrue(is_valid)
        
        # لا يمكن استخدام نفس الرمز مرة أخرى
        is_valid_again = TwoFactorAuthService.verify_login_token(
            self.user, backup_code, 'backup_code'
        )
        self.assertFalse(is_valid_again)
    
    def test_disable_2fa(self):
        """اختبار تعطيل المصادقة الثنائية"""
        # إعداد وتفعيل
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        secret = result['secret']
        
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        TwoFactorAuthService.verify_and_enable_totp(self.user, current_token)
        
        # التعطيل
        TwoFactorAuthService.disable_2fa(self.user)
        
        two_factor = TwoFactorAuth.objects.get(user=self.user)
        self.assertFalse(two_factor.is_enabled)
    
    def test_regenerate_backup_codes(self):
        """اختبار إعادة توليد رموز النسخ الاحتياطي"""
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        old_codes = result['backup_codes']
        
        secret = result['secret']
        totp = pyotp.TOTP(secret)
        current_token = totp.now()
        TwoFactorAuthService.verify_and_enable_totp(self.user, current_token)
        
        # توليد رموز جديدة
        new_codes = TwoFactorAuthService.regenerate_backup_codes(self.user)
        
        self.assertEqual(len(new_codes), 10)
        self.assertNotEqual(set(old_codes), set(new_codes))


class TwoFactorAuthViewsTests(TestCase):
    """اختبارات الواجهات (Views)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_setup_2fa_requires_login(self):
        """اختبار أن صفحة الإعداد تتطلب تسجيل الدخول"""
        response = self.client.get(reverse('accounts:setup_2fa'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_setup_2fa_page_loads(self):
        """اختبار تحميل صفحة الإعداد"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:setup_2fa'))
        
        self.assertEqual(response.status_code, 200)
        # الصفحة يجب أن تحتوي على عنوان التحقق الثنائي أو رمز QR
        self.assertTrue(
            'التحقق الثنائي' in response.content.decode('utf-8') or
            'data:image' in response.content.decode('utf-8') or
            'qr_code' in response.content.decode('utf-8') or
            'secret' in response.content.decode('utf-8')
        )
    
    def test_manage_2fa_requires_login(self):
        """اختبار أن صفحة الإدارة تتطلب تسجيل الدخول"""
        response = self.client.get(reverse('accounts:manage_2fa'))
        self.assertEqual(response.status_code, 302)
    
    def test_manage_2fa_page_loads(self):
        """اختبار تحميل صفحة الإدارة"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:manage_2fa'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'المصادقة الثنائية')


class IntegrationTests(TestCase):
    """اختبارات التكامل الشامل"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_full_2fa_setup_and_login_flow(self):
        """اختبار دورة كاملة: إعداد → تفعيل → تسجيل دخول"""
        # تسجيل الدخول
        self.client.login(username='testuser', password='testpass123')
        
        # إعداد 2FA
        result = TwoFactorAuthService.setup_totp_for_user(self.user)
        secret = result['secret']
        
        # توليد رمز والتفعيل
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        success = TwoFactorAuthService.verify_and_enable_totp(self.user, token)
        self.assertTrue(success)
        
        # تسجيل الخروج
        self.client.logout()
        
        # محاولة تسجيل الدخول من جديد
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # يجب إعادة التوجيه لصفحة التحقق
        self.assertEqual(response.status_code, 302)
        
        # التحقق بـ TOTP
        new_token = totp.now()
        is_valid = TwoFactorAuthService.verify_login_token(
            self.user, new_token, 'totp'
        )
        self.assertTrue(is_valid)


if __name__ == '__main__':
    import unittest
    unittest.main()
