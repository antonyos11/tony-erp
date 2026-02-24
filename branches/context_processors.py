"""
Context Processor موحد للفروع
يستخدم جدول Branch مباشرة بدلاً من Showroom
"""
from .models import Branch, BranchStaff

SESSION_KEY = 'ACTIVE_BRANCH_ID'
ALL_BRANCHES_KEY = 'SHOW_ALL_BRANCHES'


def branch_context(request):
    """Context processor للفروع - يظهر في القائمة المنسدلة"""
    if not request.user.is_authenticated:
        return {}
    
    # التحقق من وجود session
    has_session = hasattr(request, 'session')
    
    # التحقق أولاً من GET parameter
    branch_param = request.GET.get('showroom') or request.GET.get('branch')
    
    # التحقق من تعيين الفروع للمستخدم
    assigned = BranchStaff.objects.filter(user=request.user, is_active=True)
    has_branch_assignment = assigned.exists()
    
    # معالجة اختيار "جميع الفروع" أو فرع محدد
    if has_session:
        if branch_param == 'all':
            if request.user.is_superuser or (request.user.is_staff and not has_branch_assignment):
                request.session[ALL_BRANCHES_KEY] = True
                if SESSION_KEY in request.session:
                    del request.session[SESSION_KEY]
                request.session.modified = True
        elif branch_param and branch_param.isdigit():
            branch_id = int(branch_param)
            # التحقق من أن الموظف لديه صلاحية الوصول لهذا الفرع
            if request.user.is_superuser or (request.user.is_staff and not has_branch_assignment) or assigned.filter(branch_id=branch_id).exists():
                # إلغاء وضع "جميع الفروع" عند اختيار فرع محدد
                if ALL_BRANCHES_KEY in request.session:
                    del request.session[ALL_BRANCHES_KEY]
                request.session[SESSION_KEY] = branch_id
                request.session.modified = True
    
    # التحقق من وضع "جميع الفروع"
    show_all_branches = getattr(request, 'show_all_branches', False) or (has_session and request.session.get(ALL_BRANCHES_KEY, False))
    
    active_id = getattr(request, 'active_branch_id', None) or (has_session and request.session.get(SESSION_KEY))

    # تحديد الفروع المتاحة للمستخدم
    if request.user.is_superuser or (request.user.is_staff and not has_branch_assignment):
        # المدير العام أو الموظف الإداري غير المعين لفرع محدد - يرى كل الفروع
        branches = list(Branch.objects.filter(is_active=True).order_by('branch_type', 'code'))
    else:
        # الموظفين المعينين في فروع محددة - فقط فروعهم
        # حتى لو is_staff=True، يلتزم بالفروع المعينة له
        can_cross = assigned.filter(can_cross_access=True).exists()
        if can_cross:
            branches = list(Branch.objects.filter(is_active=True).order_by('branch_type', 'code'))
        else:
            branch_ids = assigned.values_list('branch_id', flat=True)
            branches = list(Branch.objects.filter(id__in=branch_ids, is_active=True).order_by('branch_type', 'code'))

    active = None
    if active_id and not show_all_branches:
        active = next((b for b in branches if b.id == active_id), None)
    
    # إذا لم يتم اختيار فرع وليس في وضع "جميع الفروع"، اختر أول فرع تلقائياً
    if not active and not show_all_branches and branches:
        active = branches[0]
        if hasattr(request, 'session'):
            request.session[SESSION_KEY] = active.id
    
    # للتوافق مع الـ templates القديمة
    return {
        # الأسماء الجديدة
        'current_branch': active,
        'user_branches': branches,
        'show_all_branches': show_all_branches,
        'can_view_all_branches': request.user.is_superuser or (request.user.is_staff and not has_branch_assignment),
        
        # الأسماء القديمة للتوافق (Showroom)
        'current_showroom': active,
        'user_showrooms': branches,
        'show_all_showrooms': show_all_branches,
        'can_view_all_showrooms': request.user.is_superuser or (request.user.is_staff and not has_branch_assignment),
        'single_showroom_mode': len(branches) <= 1,
    }
