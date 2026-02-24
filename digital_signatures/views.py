"""
Views للتوقيعات الرقمية
"""

import json
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.core.files.base import ContentFile

from .models import (
    SignatureProfile, SignatureRequest, Signer, SignatureField,
    Signature, SignatureAuditLog, SignatureTemplate
)


@login_required
def dashboard(request):
    """لوحة التوقيعات"""
    pending_requests = SignatureRequest.objects.filter(
        signers__user=request.user,
        signers__is_signed=False,
        status='pending'
    ).distinct()
    
    sent_requests = SignatureRequest.objects.filter(
        requester=request.user
    ).order_by('-created_at')[:10]
    
    recent_signed = SignatureRequest.objects.filter(
        signers__user=request.user,
        signers__is_signed=True
    ).order_by('-signers__signed_at')[:10]
    
    stats = {
        'pending': pending_requests.count(),
        'sent': SignatureRequest.objects.filter(requester=request.user, status='pending').count(),
        'completed': SignatureRequest.objects.filter(requester=request.user, status='signed').count(),
    }
    
    return render(request, 'digital_signatures/dashboard.html', {
        'pending_requests': pending_requests,
        'sent_requests': sent_requests,
        'recent_signed': recent_signed,
        'stats': stats,
    })


@login_required
def my_signature(request):
    """توقيعي"""
    profile, created = SignatureProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        initials_data = request.POST.get('initials_data')
        
        if signature_data:
            # حفظ التوقيع كصورة
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            profile.signature_image.save(
                f'signature_{request.user.id}.{ext}',
                ContentFile(base64.b64decode(imgstr)),
                save=False
            )
            profile.signature_data = signature_data
        
        if initials_data:
            format, imgstr = initials_data.split(';base64,')
            ext = format.split('/')[-1]
            profile.initials_image.save(
                f'initials_{request.user.id}.{ext}',
                ContentFile(base64.b64decode(imgstr)),
                save=False
            )
            profile.initials_data = initials_data
        
        if 'stamp_image' in request.FILES:
            profile.stamp_image = request.FILES['stamp_image']
        
        profile.save()
        messages.success(request, 'تم حفظ التوقيع بنجاح')
    
    return render(request, 'digital_signatures/my_signature.html', {
        'profile': profile,
    })


@login_required
def create_request(request):
    """إنشاء طلب توقيع"""
    if request.method == 'POST':
        sig_request = SignatureRequest.objects.create(
            requester=request.user,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            document=request.FILES.get('document'),
            message=request.POST.get('message', ''),
            priority=request.POST.get('priority', 'normal'),
        )
        
        # إضافة الموقعين
        signers_data = request.POST.getlist('signers[]')
        for i, email in enumerate(signers_data):
            if email.strip():
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                user = User.objects.filter(email=email.strip()).first()
                Signer.objects.create(
                    request=sig_request,
                    user=user,
                    email=email.strip(),
                    order=i
                )
        
        # سجل
        SignatureAuditLog.objects.create(
            request=sig_request,
            user=request.user,
            action='created',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, 'تم إنشاء طلب التوقيع بنجاح')
        return redirect('digital_signatures:request_detail', uuid=sig_request.uuid)
    
    templates = SignatureTemplate.objects.filter(
        created_by=request.user,
        is_active=True
    )
    
    return render(request, 'digital_signatures/create_request.html', {
        'templates': templates,
    })


@login_required
def request_detail(request, uuid):
    """تفاصيل طلب التوقيع"""
    sig_request = get_object_or_404(SignatureRequest, uuid=uuid)
    
    # التحقق من الصلاحية
    is_requester = sig_request.requester == request.user
    is_signer = sig_request.signers.filter(user=request.user).exists()
    
    if not (is_requester or is_signer):
        messages.error(request, 'ليس لديك صلاحية لعرض هذا الطلب')
        return redirect('digital_signatures:dashboard')
    
    # سجل العرض
    SignatureAuditLog.objects.create(
        request=sig_request,
        user=request.user,
        action='viewed',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    current_signer = sig_request.signers.filter(user=request.user).first()
    
    return render(request, 'digital_signatures/request_detail.html', {
        'request': sig_request,
        'is_requester': is_requester,
        'is_signer': is_signer,
        'current_signer': current_signer,
    })


@login_required
def sign_document(request, uuid):
    """توقيع المستند"""
    sig_request = get_object_or_404(SignatureRequest, uuid=uuid, status='pending')
    signer = get_object_or_404(Signer, request=sig_request, user=request.user, is_signed=False)
    
    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        
        if not signature_data:
            return JsonResponse({'success': False, 'error': 'التوقيع مطلوب'})
        
        # إنشاء حقل توقيع إذا لم يكن موجوداً
        field, created = SignatureField.objects.get_or_create(
            request=sig_request,
            signer=signer,
            field_type='signature',
            defaults={'is_required': True}
        )
        
        # حفظ التوقيع
        Signature.objects.create(
            field=field,
            signer=signer,
            signature_data=signature_data,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # تحديث حالة الموقع
        signer.is_signed = True
        signer.signed_at = timezone.now()
        signer.save()
        
        # تحديث الحقل
        field.value = signature_data
        field.is_filled = True
        field.filled_at = timezone.now()
        field.save()
        
        # سجل
        SignatureAuditLog.objects.create(
            request=sig_request,
            user=request.user,
            action='signed',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # التحقق من اكتمال جميع التوقيعات
        if not sig_request.signers.filter(is_signed=False, role='signer').exists():
            sig_request.status = 'signed'
            sig_request.completed_at = timezone.now()
            sig_request.save()
            
            SignatureAuditLog.objects.create(
                request=sig_request,
                user=request.user,
                action='completed'
            )
        
        return JsonResponse({'success': True})
    
    profile, _ = SignatureProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'digital_signatures/sign_document.html', {
        'request': sig_request,
        'signer': signer,
        'profile': profile,
    })


@login_required
@require_http_methods(['POST'])
def reject_document(request, uuid):
    """رفض المستند"""
    sig_request = get_object_or_404(SignatureRequest, uuid=uuid, status='pending')
    signer = get_object_or_404(Signer, request=sig_request, user=request.user, is_signed=False)
    
    try:
        data = json.loads(request.body)
        
        signer.is_rejected = True
        signer.rejection_reason = data.get('reason', '')
        signer.save()
        
        sig_request.status = 'rejected'
        sig_request.save()
        
        SignatureAuditLog.objects.create(
            request=sig_request,
            user=request.user,
            action='rejected',
            details=data.get('reason', ''),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def send_reminder(request, uuid):
    """إرسال تذكير"""
    sig_request = get_object_or_404(SignatureRequest, uuid=uuid, requester=request.user)
    
    unsigned = sig_request.signers.filter(is_signed=False)
    
    for signer in unsigned:
        signer.reminder_count += 1
        signer.save()
        
        # إرسال الإشعار
        # TODO: إرسال بريد إلكتروني
    
    SignatureAuditLog.objects.create(
        request=sig_request,
        user=request.user,
        action='reminder_sent',
        details=f'تم إرسال تذكير لـ {unsigned.count()} موقع'
    )
    
    return JsonResponse({
        'success': True,
        'count': unsigned.count()
    })


@login_required
def download_signed(request, uuid):
    """تحميل المستند الموقع"""
    sig_request = get_object_or_404(SignatureRequest, uuid=uuid, status='signed')
    
    # التحقق من الصلاحية
    is_authorized = (
        sig_request.requester == request.user or
        sig_request.signers.filter(user=request.user).exists()
    )
    
    if not is_authorized:
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('digital_signatures:dashboard')
    
    SignatureAuditLog.objects.create(
        request=sig_request,
        user=request.user,
        action='downloaded',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # إرجاع المستند
    response = HttpResponse(sig_request.document, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{sig_request.title}_signed.pdf"'
    return response


@login_required
def templates_list(request):
    """قائمة القوالب"""
    templates = SignatureTemplate.objects.filter(created_by=request.user)
    
    return render(request, 'digital_signatures/templates.html', {
        'templates': templates,
    })


# Views with ID (for backward compatibility)
@login_required
def sign_document_by_id(request, id):
    """توقيع المستند بالـ ID"""
    sig_request = get_object_or_404(SignatureRequest, id=id, status='pending')
    return sign_document(request, sig_request.uuid)


@login_required
@require_http_methods(['POST'])
def reject_document_by_id(request, id):
    """رفض المستند بالـ ID"""
    sig_request = get_object_or_404(SignatureRequest, id=id, status='pending')
    return reject_document(request, sig_request.uuid)


@login_required
def download_signed_by_id(request, id):
    """تحميل المستند بالـ ID"""
    sig_request = get_object_or_404(SignatureRequest, id=id)
    return download_signed(request, sig_request.uuid)


@login_required
def view_document(request, id):
    """عرض المستند"""
    sig_request = get_object_or_404(SignatureRequest, id=id)
    
    is_authorized = (
        sig_request.requester == request.user or
        sig_request.signers.filter(user=request.user).exists()
    )
    
    if not is_authorized:
        messages.error(request, 'ليس لديك صلاحية')
        return redirect('digital_signatures:dashboard')
    
    SignatureAuditLog.objects.create(
        request=sig_request,
        user=request.user,
        action='viewed',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'digital_signatures/view_document.html', {
        'request': sig_request,
    })


@login_required
def verify_document(request, id):
    """التحقق من صحة المستند"""
    sig_request = get_object_or_404(SignatureRequest, id=id)
    
    signatures = Signature.objects.filter(field__request=sig_request)
    audit_log = SignatureAuditLog.objects.filter(request=sig_request).order_by('-timestamp')
    
    return render(request, 'digital_signatures/verify_document.html', {
        'request': sig_request,
        'signatures': signatures,
        'audit_log': audit_log,
    })