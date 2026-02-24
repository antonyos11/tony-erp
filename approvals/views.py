from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import ApprovalRequest
from .services import get_approvers

@login_required
def approval_list(request):
    qs = ApprovalRequest.objects.all()
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    search = request.GET.get('q')
    if search:
        qs = qs.filter(Q(reason__icontains=search) | Q(id__icontains=search))
    return render(request, 'approvals/list.html', {'approvals': qs[:200]})

@login_required
def approval_detail(request, pk):
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    return render(request, 'approvals/detail.html', {'approval': approval})

@login_required
def approve_request(request, pk):
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    # يجب أن يكون الطلب عبر POST لضمان وجود الملاحظة (حتى لو كانت فارغة)
    if request.method != 'POST':
        messages.error(request, 'استخدم النموذج لإرسال قرار الموافقة.')
        return redirect('approvals:detail', pk=approval.pk)
    if not (request.user.is_superuser or request.user in get_approvers(approval.amount, approval.current_level)):
        messages.error(request, 'ليست لديك صلاحية الموافقة لهذا المستوى/المبلغ.')
        return redirect('approvals:detail', pk=approval.pk)
    note = request.POST.get('note', '').strip()
    if approval.approve(request.user, note=note):
        messages.success(request, f'تمت الموافقة على الطلب #{approval.id}')
    else:
        messages.error(request, 'تعذر الموافقة (ربما ليس بالحالة المناسبة).')
    return redirect('approvals:detail', pk=approval.pk)

@login_required
def reject_request(request, pk):
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method != 'POST':
        messages.error(request, 'استخدم النموذج لإرسال قرار الرفض.')
        return redirect('approvals:detail', pk=approval.pk)
    if not (request.user.is_superuser or request.user in get_approvers(approval.amount, approval.current_level)):
        messages.error(request, 'ليست لديك صلاحية الرفض لهذا الطلب.')
        return redirect('approvals:detail', pk=approval.pk)
    note = request.POST.get('note', '').strip()
    if approval.reject(request.user, note=note):
        messages.warning(request, f'تم رفض الطلب #{approval.id}')
    else:
        messages.error(request, 'تعذر الرفض (ربما ليس بالحالة المناسبة).')
    return redirect('approvals:detail', pk=approval.pk)


@login_required
def settings(request):
    """إعدادات نظام الاعتمادات"""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    
    User = get_user_model()
    
    context = {
        'total_users': User.objects.count(),
        'total_groups': Group.objects.count(),
        'groups': Group.objects.all()[:10],
        'superusers': User.objects.filter(is_superuser=True)[:10],
    }
    return render(request, 'approvals/settings.html', context)
