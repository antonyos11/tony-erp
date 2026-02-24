"""
Views لنظام السمات
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import Theme, UserThemePreference


@login_required
def theme_settings(request):
    """إعدادات السمة"""
    preference, created = UserThemePreference.objects.get_or_create(user=request.user)
    themes = Theme.objects.filter(is_active=True)
    
    if request.method == 'POST':
        theme_id = request.POST.get('theme')
        if theme_id:
            preference.theme = Theme.objects.filter(id=theme_id).first()
        
        preference.mode = request.POST.get('mode', 'auto')
        preference.compact_mode = request.POST.get('compact_mode') == 'on'
        preference.sidebar_collapsed = request.POST.get('sidebar_collapsed') == 'on'
        preference.font_size = request.POST.get('font_size', 'medium')
        preference.auto_switch_enabled = request.POST.get('auto_switch_enabled') == 'on'
        
        preference.save()
        messages.success(request, 'تم حفظ إعدادات السمة بنجاح')
    
    return render(request, 'theme_system/settings.html', {
        'preference': preference,
        'themes': themes,
    })


@login_required
@require_http_methods(['POST'])
def toggle_dark_mode(request):
    """تبديل الوضع المظلم"""
    preference, _ = UserThemePreference.objects.get_or_create(user=request.user)
    
    if preference.mode == 'dark':
        preference.mode = 'light'
    else:
        preference.mode = 'dark'
    
    preference.save()
    
    return JsonResponse({
        'success': True,
        'mode': preference.mode
    })


@login_required
@require_http_methods(['POST'])
def toggle_compact_mode(request):
    """تبديل الوضع المضغوط"""
    preference, _ = UserThemePreference.objects.get_or_create(user=request.user)
    preference.compact_mode = not preference.compact_mode
    preference.save()
    
    return JsonResponse({
        'success': True,
        'compact_mode': preference.compact_mode
    })


@login_required
@require_http_methods(['POST'])
def toggle_sidebar(request):
    """تبديل الشريط الجانبي"""
    preference, _ = UserThemePreference.objects.get_or_create(user=request.user)
    preference.sidebar_collapsed = not preference.sidebar_collapsed
    preference.save()
    
    return JsonResponse({
        'success': True,
        'sidebar_collapsed': preference.sidebar_collapsed
    })


@login_required
def get_theme_css(request):
    """الحصول على CSS السمة"""
    preference, _ = UserThemePreference.objects.get_or_create(user=request.user)
    
    # تحديد السمة
    current_mode = preference.get_current_mode()
    
    if preference.theme:
        theme = preference.theme
    else:
        # البحث عن سمة افتراضية حسب الوضع
        theme = Theme.objects.filter(
            theme_type=current_mode,
            is_default=True
        ).first() or Theme.objects.filter(is_default=True).first()
    
    if theme:
        css = theme.to_css_vars()
    else:
        css = get_default_css(current_mode)
    
    # إضافة CSS للوضع المضغوط
    if preference.compact_mode:
        css += """
        .compact-mode {
            --spacing-sm: 0.25rem;
            --spacing-md: 0.5rem;
            --spacing-lg: 0.75rem;
        }
        .compact-mode .card { padding: 0.5rem; }
        .compact-mode .btn { padding: 0.25rem 0.5rem; font-size: 0.875rem; }
        """
    
    return HttpResponse(css, content_type='text/css')


def get_default_css(mode):
    """CSS افتراضي"""
    if mode == 'dark':
        return """
        :root {
            --primary-color: #0d6efd;
            --secondary-color: #6c757d;
            --accent-color: #9b59b6;
            --background-color: #1a1a2e;
            --surface-color: #16213e;
            --card-color: #0f3460;
            --text-primary: #eaeaea;
            --text-secondary: #b0b0b0;
            --text-muted: #6c757d;
            --sidebar-bg: #0f0f23;
            --sidebar-text: #ffffff;
            --sidebar-active: #0d6efd;
            --header-bg: #16213e;
            --header-text: #ffffff;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --info-color: #17a2b8;
        }
        body { background-color: var(--background-color); color: var(--text-primary); }
        .card { background-color: var(--card-color); border-color: #2a2a4a; }
        .table { color: var(--text-primary); }
        .form-control { background-color: var(--surface-color); color: var(--text-primary); border-color: #2a2a4a; }
        .form-control:focus { background-color: var(--surface-color); color: var(--text-primary); }
        .modal-content { background-color: var(--card-color); }
        .dropdown-menu { background-color: var(--surface-color); }
        .dropdown-item { color: var(--text-primary); }
        .dropdown-item:hover { background-color: var(--card-color); }
        """
    else:
        return """
        :root {
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --accent-color: #9b59b6;
            --background-color: #f4f6f9;
            --surface-color: #ffffff;
            --card-color: #ffffff;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --text-muted: #adb5bd;
            --sidebar-bg: #343a40;
            --sidebar-text: #ffffff;
            --sidebar-active: #007bff;
            --header-bg: #ffffff;
            --header-text: #212529;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --info-color: #17a2b8;
        }
        """


@login_required
def preview_theme(request, theme_id):
    """معاينة سمة"""
    theme = Theme.objects.filter(id=theme_id, is_active=True).first()
    
    if theme:
        return HttpResponse(theme.to_css_vars(), content_type='text/css')
    
    return HttpResponse('', content_type='text/css')
