from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from .models import Notification


@login_required
def notification_list(request: HttpRequest) -> HttpResponse:
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(qs, 25)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'level': n.level,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            } for n in page_obj
        ]
        return JsonResponse({'results': data, 'num_pages': paginator.num_pages})
    return render(request, 'notifications/list.html', {'page_obj': page_obj, 'notifications': page_obj.object_list})


@login_required
@require_http_methods(["GET", "POST"])
def mark_read(request: HttpRequest, pk: int) -> HttpResponse:
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('notifications:list')


@login_required
@require_http_methods(["GET", "POST"])
def mark_all_read(request: HttpRequest) -> HttpResponse:
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('notifications:list')
