from .models import Showroom, ShowroomEmployee
from .middleware import SESSION_KEY, ALL_SHOWROOMS_KEY

def showroom_context(request):
    if not request.user.is_authenticated:
        return {}
    
    # التحقق من وجود session
    has_session = hasattr(request, 'session')
    
    # التحقق أولاً من GET parameter
    showroom_param = request.GET.get('showroom')
    
    # معالجة اختيار "جميع الفروع" أو فرع محدد
    if has_session:
        if showroom_param == 'all':
            if request.user.is_superuser or request.user.is_staff:
                request.session[ALL_SHOWROOMS_KEY] = True
                if SESSION_KEY in request.session:
                    del request.session[SESSION_KEY]
                request.session.modified = True
        elif showroom_param and showroom_param.isdigit():
            # إلغاء وضع "جميع الفروع" عند اختيار فرع محدد
            if ALL_SHOWROOMS_KEY in request.session:
                del request.session[ALL_SHOWROOMS_KEY]
            request.session[SESSION_KEY] = int(showroom_param)
            request.session.modified = True
    
    # التحقق من وضع "جميع الفروع" - من الـ request أو الـ session
    show_all_showrooms = getattr(request, 'show_all_showrooms', False) or (has_session and request.session.get(ALL_SHOWROOMS_KEY, False))
    
    active_id = getattr(request, 'active_showroom_id', None) or (has_session and request.session.get(SESSION_KEY))

    assigned = ShowroomEmployee.objects.filter(user=request.user, active=True)
    if request.user.is_superuser:
        qs = list(Showroom.objects.all().order_by('showroom_type', 'code'))
    elif assigned.filter(role__in=['manager', 'supervisor']).exists():
        qs = list(Showroom.objects.filter(id__in=assigned.values_list('showroom_id', flat=True)).order_by('showroom_type', 'code'))
    elif assigned.filter(can_cross_access=True).exists():
        qs = list(Showroom.objects.all().order_by('showroom_type', 'code'))
    else:
        qs = list(Showroom.objects.filter(id__in=assigned.values_list('showroom_id', flat=True)).order_by('showroom_type', 'code'))

    active = None
    if active_id and not show_all_showrooms:
        active = next((s for s in qs if s.id == active_id), None)
    
    # إذا لم يتم اختيار فرع وليس في وضع "جميع الفروع"، اختر أول فرع تلقائياً
    if not active and not show_all_showrooms and qs:
        active = qs[0]
        # حفظ في الجلسة
        if hasattr(request, 'session'):
            request.session[SESSION_KEY] = active.id
    
    return {
        'current_showroom': active,
        'user_showrooms': qs,
        'single_showroom_mode': getattr(request, 'single_showroom_mode', False),
        'show_all_showrooms': show_all_showrooms,
        'can_view_all_showrooms': request.user.is_superuser or request.user.is_staff,
    }
