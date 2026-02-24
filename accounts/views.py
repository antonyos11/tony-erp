"""
واجهات عرض نظام المصادقة الثنائية
Two-Factor Authentication Views
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.utils import timezone
import json

from accounts.two_factor_service import (
    TOTPService,
    BackupCodesService,
    OTPService,
    LoginAttemptTracker,
    TwoFactorAuthService
)
from accounts.models import TwoFactorAuth, LoginAttempt


def get_client_ip(request):
	"""الحصول على عنوان IP للعميل"""
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


@csrf_exempt
def custom_login(request):
	"""صفحة تسجيل الدخول المخصصة مع دعم 2FA"""
	
	# الحصول على معامل next من الطلب
	next_url = request.POST.get('next') or request.GET.get('next', '')
	
	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		
		# التحقق من الحظر
		if LoginAttemptTracker.is_locked_out(username):
			lockout_time = LoginAttemptTracker.get_lockout_time_remaining(username)
			remaining_minutes = max(1, lockout_time // 60)
			messages.error(
				request,
				f'تم تعليق تسجيل الدخول مؤقتاً بسبب محاولات متعددة فاشلة. يرجى المحاولة بعد {remaining_minutes} دقيقة.'
			)
			context = {'next': next_url}
			return render(request, 'accounts/login.html', context)
		
		# المصادقة بكلمة المرور
		user = authenticate(request, username=username, password=password)
		
		ip_address = get_client_ip(request)
		
		if user is not None:
			# التحقق من تفعيل 2FA
			if TwoFactorAuthService.is_2fa_enabled(user):
				# تسجيل نجاح كلمة المرور
				LoginAttemptTracker.record_attempt(
					username, ip_address, True, 'password'
				)
				
				# حفظ معرف المستخدم في الجلسة
				request.session['pre_2fa_user_id'] = user.id
				request.session['pre_2fa_username'] = username
				request.session['pre_2fa_next'] = next_url
				
				return redirect('accounts:verify_2fa')
			else:
				# تسجيل دخول مباشر
				auth_login(request, user)
				LoginAttemptTracker.record_attempt(
					username, ip_address, True, 'password'
				)
				messages.success(request, f'مرحباً {user.username}')
				
				# التوجيه إلى next أو الصفحة الرئيسية
				if next_url:
					return redirect(next_url)
				return redirect('core:home')
		else:
			# تسجيل فشل
			LoginAttemptTracker.record_attempt(
				username, ip_address, False, 'password'
			)
			messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
			context = {'next': next_url}
			return render(request, 'accounts/login.html', context)
	
	context = {'next': next_url}
	return render(request, 'accounts/login.html', context)


def verify_2fa(request):
	"""صفحة التحقق من رمز 2FA"""
	
	# التحقق من وجود مستخدم في الجلسة
	user_id = request.session.get('pre_2fa_user_id')
	username = request.session.get('pre_2fa_username')
	next_url = request.session.get('pre_2fa_next', '')
	
	if not user_id:
		return redirect('accounts:login')
	
	try:
		user = User.objects.get(id=user_id)
	except User.DoesNotExist:
		return redirect('accounts:login')
	
	if request.method == 'POST':
		token = request.POST.get('token', '').strip() or request.POST.get('otp_code', '').strip()
		backup_code = request.POST.get('backup_code', '').strip()
		use_backup = request.POST.get('use_backup', False)
		
		# الحصول على next من POST إن وجدت
		next_url = request.POST.get('next', next_url) or next_url
		
		ip_address = get_client_ip(request)
		
		# التحقق باستخدام رمز احتياطي
		if use_backup and backup_code:
			token_type = 'backup_code'
			token = backup_code
		else:
			token_type = 'totp'
		
		# التحقق من الرمز
		if TwoFactorAuthService.verify_login_token(user, token, token_type):
			# تسجيل دخول ناجح
			auth_login(request, user)
			LoginAttemptTracker.record_attempt(
				username, ip_address, True, token_type
			)
			
			# تحديث آخر استخدام
			tfa = TwoFactorAuth.objects.get(user=user)
			tfa.last_used = timezone.now()
			tfa.save()
			
			# حذف بيانات الجلسة المؤقتة
			del request.session['pre_2fa_user_id']
			del request.session['pre_2fa_username']
			if 'pre_2fa_next' in request.session:
				del request.session['pre_2fa_next']
			
			messages.success(request, 'تم تسجيل الدخول بنجاح')
			
			# التوجيه إلى next أو الصفحة الرئيسية
			if next_url:
				return redirect(next_url)
			return redirect('core:home')
		else:
			# رمز خاطئ
			LoginAttemptTracker.record_attempt(
				username, ip_address, False, token_type
			)
			messages.error(request, 'الرمز غير صحيح')
	
	# عدد رموز النسخ الاحتياطي المتبقية
	backup_codes_count = TwoFactorAuthService.get_remaining_backup_codes_count(user)
	
	context = {
		'username': username,
		'backup_codes_count': backup_codes_count,
		'next': next_url
	}
	
	return render(request, 'accounts/verify_2fa.html', context)


@login_required
def setup_2fa(request):
	"""إعداد المصادقة الثنائية"""
	
	user = request.user
	
	# التحقق من عدم التفعيل مسبقاً
	if TwoFactorAuthService.is_2fa_enabled(user):
		messages.info(request, 'المصادقة الثنائية مفعلة بالفعل')
		return redirect('accounts:manage_2fa')
	
	# إنشاء QR Code ورموز النسخ
	setup_data = TwoFactorAuthService.setup_2fa(user)
	
	# حفظ رموز النسخ في الجلسة لعرضها بعد التفعيل
	request.session['temp_backup_codes'] = setup_data['backup_codes']
	request.session['temp_secret'] = setup_data['secret']
	
	context = {
		'qr_code': setup_data['qr_code'],
		'secret': setup_data['secret'],
	}
	
	return render(request, 'accounts/setup_2fa.html', context)


@login_required
@require_http_methods(["POST"])
def verify_and_enable_2fa(request):
	"""التحقق من TOTP وتفعيله"""
	
	token = request.POST.get('token', '').strip()
	secret = request.session.get('temp_secret')
	backup_codes = request.session.get('temp_backup_codes', [])
	
	if not secret:
		messages.error(request, 'انتهت صلاحية الجلسة. يرجى إعادة المحاولة')
		return redirect('accounts:setup_2fa')
	
	# التحقق من الرمز
	if TwoFactorAuthService.verify_token(secret, token):
		# تفعيل 2FA
		TwoFactorAuthService.enable_2fa(request.user, backup_codes)
		
		context = {
			'backup_codes': backup_codes
		}
		
		# حذف من الجلسة
		if 'temp_backup_codes' in request.session:
			del request.session['temp_backup_codes']
		if 'temp_secret' in request.session:
			del request.session['temp_secret']
		
		messages.success(request, 'تم تفعيل المصادقة الثنائية بنجاح')
		return render(request, 'accounts/backup_codes_display.html', context)
	else:
		messages.error(request, 'الرمز غير صحيح. حاول مجدداً')
		return redirect('accounts:setup_2fa')


@login_required
def manage_2fa(request):
	"""إدارة إعدادات المصادقة الثنائية"""
	
	user = request.user
	is_enabled = TwoFactorAuthService.is_2fa_enabled(user)
	
	tfa = None
	backup_codes_count = 0
	
	if is_enabled:
		try:
			tfa = TwoFactorAuth.objects.get(user=user)
			backup_codes_count = TwoFactorAuthService.get_remaining_backup_codes_count(user)
		except TwoFactorAuth.DoesNotExist:
			pass
	
	# آخر محاولات تسجيل الدخول
	recent_attempts = LoginAttempt.objects.filter(
		user=user
	).order_by('-timestamp')[:10]
	
	context = {
		'is_enabled': is_enabled,
		'tfa': tfa,
		'backup_codes_count': backup_codes_count,
		'recent_attempts': recent_attempts
	}
	
	return render(request, 'accounts/manage_2fa.html', context)


@login_required
@require_http_methods(["POST"])
def disable_2fa(request):
	"""تعطيل المصادقة الثنائية"""
	
	# التحقق من كلمة المرور للأمان
	password = request.POST.get('password')
	
	user = authenticate(username=request.user.username, password=password)
	
	if user is None:
		messages.error(request, 'كلمة المرور غير صحيحة')
		return redirect('accounts:manage_2fa')
	
	if TwoFactorAuthService.disable_2fa(request.user):
		messages.success(request, 'تم تعطيل المصادقة الثنائية')
	else:
		messages.error(request, 'حدث خطأ أثناء التعطيل')
	
	return redirect('accounts:manage_2fa')


@login_required
def regenerate_backup_codes(request):
	"""إعادة إنشاء رموز النسخ الاحتياطي"""
	
	if request.method == 'POST':
		backup_codes = TwoFactorAuthService.regenerate_backup_codes(request.user)
		
		context = {
			'backup_codes': backup_codes
		}
		
		messages.success(request, 'تم إنشاء رموز نسخ احتياطي جديدة')
		return render(request, 'accounts/backup_codes_display.html', context)
	
	return redirect('accounts:manage_2fa')


@login_required
def send_email_otp(request):
	"""إرسال OTP عبر البريد الإلكتروني"""
	
	user = request.user
	
	# إنشاء OTP
	otp = OTPService.generate_otp()
	
	# حفظ في الذاكرة المؤقتة
	OTPService.store_otp(user.id, otp)
	
	# إرسال عبر البريد
	if OTPService.send_email_otp(user, otp):
		return JsonResponse({
			'success': True,
			'message': 'تم إرسال الرمز إلى بريدك الإلكتروني'
		})
	else:
		return JsonResponse({
			'success': False,
			'message': 'فشل إرسال الرمز'
		}, status=500)


@login_required
def login_history(request):
	"""سجل محاولات تسجيل الدخول"""
	
	attempts = LoginAttempt.objects.filter(
		user=request.user
	).order_by('-timestamp')[:50]
	
	context = {
		'attempts': attempts
	}
	
	return render(request, 'accounts/login_history.html', context)


# AJAX APIs

@login_required
def check_2fa_status(request):
	"""التحقق من حالة 2FA (AJAX)"""
	
	is_enabled = TwoFactorAuthService.is_2fa_enabled(request.user)
	backup_codes_count = TwoFactorAuthService.get_remaining_backup_codes_count(request.user)
	
	return JsonResponse({
		'is_enabled': is_enabled,
		'backup_codes_count': backup_codes_count
	})


@login_required
def verify_totp_ajax(request):
	"""التحقق من TOTP عبر AJAX"""
	
	if request.method == 'POST':
		try:
			data = json.loads(request.body)
			token = data.get('token', '').strip()
			
			# للتحقق أثناء الإعداد
			try:
				tfa = TwoFactorAuth.objects.get(user=request.user, is_enabled=False)
				is_valid = TOTPService.verify_token(tfa.totp_secret, token)
				
				return JsonResponse({
					'success': is_valid,
					'message': 'الرمز صحيح' if is_valid else 'الرمز غير صحيح'
				})
			except TwoFactorAuth.DoesNotExist:
				return JsonResponse({
					'success': False,
					'message': 'لم يتم العثور على إعدادات 2FA'
				}, status=404)
		
		except Exception as e:
			return JsonResponse({
				'success': False,
				'message': str(e)
			}, status=500)
	
	return JsonResponse({
		'success': False,
		'message': 'طلب غير صالح'
	}, status=400)
