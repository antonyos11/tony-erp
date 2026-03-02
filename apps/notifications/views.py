"""
Views — الإشعارات
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages

from .models import Notification, NotificationSetting


class NotificationListView(LoginRequiredMixin, ListView):
    """قائمة كل الإشعارات مع فلترة"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        notification_type = self.request.GET.get('type')
        category = self.request.GET.get('category')
        is_read = self.request.GET.get('is_read')

        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        if category:
            qs = qs.filter(category=category)
        if is_read == '0':
            qs = qs.filter(is_read=False)
        elif is_read == '1':
            qs = qs.filter(is_read=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_unread'] = Notification.objects.filter(user=self.request.user, is_read=False).count()
        ctx['notification_types'] = Notification.NOTIFICATION_TYPES
        ctx['notification_categories'] = Notification.NOTIFICATION_CATEGORIES
        ctx['selected_type'] = self.request.GET.get('type', '')
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_is_read'] = self.request.GET.get('is_read', '')
        return ctx


class MarkReadView(LoginRequiredMixin, View):
    """تعليم إشعار كمقروء (AJAX POST)"""

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': pk})

        next_url = request.POST.get('next') or 'notifications:notification_list'
        return redirect(next_url)


class MarkAllReadView(LoginRequiredMixin, View):
    """تعليم كل الإشعارات كمقروءة"""

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'updated': updated})
        messages.success(request, f'تم تعليم {updated} إشعار كمقروء')
        return redirect('notifications:notification_list')


class NotificationSettingsView(LoginRequiredMixin, View):
    """إعدادات الإشعارات"""
    template_name = 'notifications/notification_settings.html'

    def get(self, request):
        from django.shortcuts import render
        settings_obj, _ = NotificationSetting.objects.get_or_create(user=request.user)
        return render(request, self.template_name, {'settings': settings_obj})

    def post(self, request):
        settings_obj, _ = NotificationSetting.objects.get_or_create(user=request.user)
        settings_obj.stock_alerts = request.POST.get('stock_alerts') == 'on'
        settings_obj.invoice_alerts = request.POST.get('invoice_alerts') == 'on'
        settings_obj.production_alerts = request.POST.get('production_alerts') == 'on'
        settings_obj.hr_alerts = request.POST.get('hr_alerts') == 'on'
        settings_obj.financial_alerts = request.POST.get('financial_alerts') == 'on'
        settings_obj.email_notifications = request.POST.get('email_notifications') == 'on'
        settings_obj.save()
        messages.success(request, 'تم حفظ إعدادات الإشعارات')
        return redirect('notifications:settings')


# ══════════════════════════════════════════════════════
# عدد الإشعارات غير المقروءة (AJAX)
# ══════════════════════════════════════════════════════

class UnreadCountView(LoginRequiredMixin, View):
    """إرجاع عدد الإشعارات غير المقروءة كـ JSON"""

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return JsonResponse({'count': count})


# ══════════════════════════════════════════════════════
# حذف إشعار
# ══════════════════════════════════════════════════════

class DeleteNotificationView(LoginRequiredMixin, View):
    """حذف إشعار واحد"""

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'deleted', 'id': pk})
        messages.success(request, 'تم حذف الإشعار')
        return redirect('notifications:notification_list')


# ══════════════════════════════════════════════════════
# مسح كل الإشعارات المقروءة
# ══════════════════════════════════════════════════════

class ClearAllNotificationsView(LoginRequiredMixin, View):
    """حذف كل الإشعارات المقروءة"""

    def post(self, request):
        deleted, _ = Notification.objects.filter(
            user=request.user, is_read=True
        ).delete()
        messages.success(request, f'تم حذف {deleted} إشعار مقروء')
        return redirect('notifications:notification_list')
