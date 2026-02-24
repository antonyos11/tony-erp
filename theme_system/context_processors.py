"""
Context Processor للسمات
"""

from .models import UserThemePreference, Theme


def theme_context(request):
    """إضافة معلومات السمة للسياق"""
    if request.user.is_authenticated:
        try:
            preference = UserThemePreference.objects.get(user=request.user)
            current_mode = preference.get_current_mode()
        except UserThemePreference.DoesNotExist:
            preference = None
            current_mode = 'light'
        
        return {
            'theme_preference': preference,
            'current_theme_mode': current_mode,
            'is_dark_mode': current_mode == 'dark',
            'is_compact_mode': preference.compact_mode if preference else False,
            'sidebar_collapsed': preference.sidebar_collapsed if preference else False,
        }
    
    return {
        'theme_preference': None,
        'current_theme_mode': 'light',
        'is_dark_mode': False,
        'is_compact_mode': False,
        'sidebar_collapsed': False,
    }
