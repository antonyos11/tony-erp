"""
نماذج نظام المصادقة الثنائية
Two-Factor Authentication Models
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class TwoFactorAuth(models.Model):
	"""نموذج إعدادات المصادقة الثنائية للمستخدم"""
	
	user = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		related_name='two_factor_auth',
		verbose_name='المستخدم'
	)
	
	# TOTP Settings
	totp_secret = models.CharField(
		max_length=32,
		blank=True,
		verbose_name='المفتاح السري TOTP'
	)
	
	is_enabled = models.BooleanField(
		default=False,
		verbose_name='مفعّل'
	)
	
	# Backup Codes (stored as JSON array of hashed codes)
	backup_codes = models.TextField(
		blank=True,
		verbose_name='رموز النسخ الاحتياطي (مشفرة)',
		help_text='JSON array of hashed backup codes'
	)
	
	# Metadata
	enabled_at = models.DateTimeField(
		null=True,
		blank=True,
		verbose_name='تاريخ التفعيل'
	)
	
	last_used = models.DateTimeField(
		null=True,
		blank=True,
		verbose_name='آخر استخدام'
	)
	
	created_at = models.DateTimeField(
		auto_now_add=True,
		verbose_name='تاريخ الإنشاء'
	)
	
	updated_at = models.DateTimeField(
		auto_now=True,
		verbose_name='تاريخ التحديث'
	)
	
	class Meta:
		verbose_name = 'مصادقة ثنائية'
		verbose_name_plural = 'مصادقات ثنائية'
		db_table = 'accounts_two_factor_auth'
	
	def __str__(self):
		status = "مفعّل" if self.is_enabled else "معطّل"
		return f"{self.user.username} - {status}"
	
	def save(self, *args, **kwargs):
		# تحديث تاريخ التفعيل عند التفعيل
		if self.is_enabled and not self.enabled_at:
			self.enabled_at = timezone.now()
		
		super().save(*args, **kwargs)


class LoginAttempt(models.Model):
	"""سجل محاولات تسجيل الدخول"""
	
	METHOD_CHOICES = [
		('password', 'كلمة المرور'),
		('totp', 'TOTP'),
		('otp', 'OTP'),
		('backup_code', 'رمز نسخ احتياطي'),
	]
	
	user = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='login_attempts',
		verbose_name='المستخدم'
	)
	
	username = models.CharField(
		max_length=150,
		verbose_name='اسم المستخدم'
	)
	
	ip_address = models.GenericIPAddressField(
		verbose_name='عنوان IP'
	)
	
	user_agent = models.TextField(
		blank=True,
		verbose_name='متصفح المستخدم'
	)
	
	success = models.BooleanField(
		verbose_name='نجح'
	)
	
	method = models.CharField(
		max_length=20,
		choices=METHOD_CHOICES,
		default='password',
		verbose_name='طريقة المصادقة'
	)
	
	failure_reason = models.CharField(
		max_length=255,
		blank=True,
		verbose_name='سبب الفشل'
	)
	
	timestamp = models.DateTimeField(
		default=timezone.now,
		verbose_name='التاريخ والوقت',
		db_index=True
	)
	
	class Meta:
		verbose_name = 'محاولة تسجيل دخول'
		verbose_name_plural = 'محاولات تسجيل الدخول'
		db_table = 'accounts_login_attempt'
		ordering = ['-timestamp']
		indexes = [
			models.Index(fields=['username', '-timestamp']),
			models.Index(fields=['ip_address', '-timestamp']),
			models.Index(fields=['success', '-timestamp']),
		]
	
	def __str__(self):
		status = "ناجح" if self.success else "فاشل"
		return f"{self.username} - {status} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class TrustedDevice(models.Model):
	"""الأجهزة الموثوقة للمستخدم"""
	
	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name='trusted_devices',
		verbose_name='المستخدم'
	)
	
	device_token = models.CharField(
		max_length=64,
		unique=True,
		verbose_name='رمز الجهاز',
		help_text='Unique token to identify this device'
	)
	
	device_name = models.CharField(
		max_length=255,
		blank=True,
		verbose_name='اسم الجهاز'
	)
	
	ip_address = models.GenericIPAddressField(
		verbose_name='عنوان IP'
	)
	
	user_agent = models.TextField(
		blank=True,
		verbose_name='متصفح المستخدم'
	)
	
	is_active = models.BooleanField(
		default=True,
		verbose_name='نشط'
	)
	
	last_used = models.DateTimeField(
		default=timezone.now,
		verbose_name='آخر استخدام'
	)
	
	created_at = models.DateTimeField(
		auto_now_add=True,
		verbose_name='تاريخ الإضافة'
	)
	
	expires_at = models.DateTimeField(
		null=True,
		blank=True,
		verbose_name='تاريخ انتهاء الصلاحية',
		help_text='If set, device trust expires at this time'
	)
	
	class Meta:
		verbose_name = 'جهاز موثوق'
		verbose_name_plural = 'أجهزة موثوقة'
		db_table = 'accounts_trusted_device'
		ordering = ['-last_used']
	
	def __str__(self):
		return f"{self.user.username} - {self.device_name or self.device_token[:8]}"
	
	def is_expired(self):
		"""التحقق من انتهاء صلاحية الجهاز"""
		if self.expires_at:
			return timezone.now() > self.expires_at
		return False
