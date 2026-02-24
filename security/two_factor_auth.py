"""
Tony ERP - Two-Factor Authentication
المصادقة الثنائية
"""
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
import qrcode
from io import BytesIO
import base64
from typing import Tuple, Optional

User = get_user_model()


class TwoFactorAuthManager:
    """مدير المصادقة الثنائية"""
    
    @staticmethod
    def enable_2fa(user: User, device_name: str = 'default') -> Tuple[TOTPDevice, str]:
        """
        تفعيل المصادقة الثنائية للمستخدم
        
        Returns:
            Tuple[TOTPDevice, str]: الجهاز و QR code كـ base64
        """
        # إنشاء أو استرجاع جهاز TOTP
        device, created = TOTPDevice.objects.get_or_create(
            user=user,
            name=device_name,
            defaults={'confirmed': False}
        )
        
        if created or not device.confirmed:
            # إنشاء مفتاح سري جديد
            device.key = random_hex(20)
            device.save()
        
        # إنشاء QR code
        qr_uri = device.config_url
        qr_code_base64 = TwoFactorAuthManager._generate_qr_code(qr_uri)
        
        return device, qr_code_base64
    
    @staticmethod
    def verify_and_confirm_2fa(device: TOTPDevice, token: str) -> bool:
        """
        التحقق من الرمز وتأكيد الجهاز
        
        Args:
            device: جهاز TOTP
            token: رمز التحقق
            
        Returns:
            bool: نجاح التحقق
        """
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            return True
        return False
    
    @staticmethod
    def disable_2fa(user: User) -> bool:
        """
        تعطيل المصادقة الثنائية
        
        Args:
            user: المستخدم
            
        Returns:
            bool: نجاح التعطيل
        """
        deleted_count, _ = TOTPDevice.objects.filter(user=user).delete()
        return deleted_count > 0
    
    @staticmethod
    def verify_token(user: User, token: str) -> bool:
        """
        التحقق من رمز المصادقة الثنائية
        
        Args:
            user: المستخدم
            token: رمز التحقق
            
        Returns:
            bool: نجاح التحقق
        """
        try:
            device = TOTPDevice.objects.get(user=user, confirmed=True)
            return device.verify_token(token)
        except TOTPDevice.DoesNotExist:
            return False
    
    @staticmethod
    def is_2fa_enabled(user: User) -> bool:
        """
        التحقق من تفعيل المصادقة الثنائية
        
        Args:
            user: المستخدم
            
        Returns:
            bool: حالة التفعيل
        """
        return TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    
    @staticmethod
    def get_backup_codes(user: User, count: int = 10) -> list[str]:
        """
        إنشاء رموز احتياطية
        
        Args:
            user: المستخدم
            count: عدد الرموز
            
        Returns:
            list[str]: قائمة الرموز الاحتياطية
        """
        codes = []
        for _ in range(count):
            code = random_hex(4)
            codes.append(code)
        
        # حفظ الرموز المشفرة في قاعدة البيانات
        from django.contrib.auth.hashers import make_password
        try:
            from users.models import BackupCode
            for code in codes:
                BackupCode.objects.create(
                    user=user,
                    code=make_password(code)
                )
        except ImportError:
            pass
        
        return codes
    
    @staticmethod
    def verify_backup_code(user: User, code: str) -> bool:
        """
        التحقق من رمز احتياطي
        
        Args:
            user: المستخدم
            code: الرمز الاحتياطي
            
        Returns:
            bool: نجاح التحقق
        """
        try:
            from users.models import BackupCode
            from django.contrib.auth.hashers import check_password
            
            backup_codes = BackupCode.objects.filter(user=user, used=False)
            
            for backup_code in backup_codes:
                if check_password(code, backup_code.code):
                    # وضع علامة كمستخدم
                    backup_code.used = True
                    backup_code.save()
                    return True
            
            return False
        except ImportError:
            return False
    
    @staticmethod
    def _generate_qr_code(data: str) -> str:
        """
        إنشاء QR code كـ base64
        
        Args:
            data: البيانات المراد ترميزها
            
        Returns:
            str: QR code كـ base64
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
