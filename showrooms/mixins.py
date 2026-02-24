from .models import ShowroomEmployee
from rest_framework.exceptions import PermissionDenied
from .permissions import showroom_has_action


def get_active_showroom_id(request):
    """Unified helper to obtain the active showroom id from request/middleware/session.
    Priority order:
      1. request.active_showroom_id attribute set by middleware
      2. session['ACTIVE_SHOWROOM_ID'] (official session key)
      3. session['active_showroom_id'] (legacy / test fallback)
      4. request.GET['showroom'] if present and numeric (as last resort in test contexts)
    Returns None if "all showrooms" mode is active.
    """
    if not request:
        return None
    # التحقق من وضع "جميع الفروع" - في هذه الحالة نرجع None
    if is_all_showrooms_mode(request):
        return None
    sid = getattr(request, 'active_showroom_id', None)
    if sid:
        return sid
    sess = getattr(request, 'session', None)
    if sess:
        sid = sess.get('ACTIVE_SHOWROOM_ID') or sess.get('active_showroom_id')
        if sid:
            return sid
    # last-resort GET param (tests bypassing middleware)
    showroom_param = getattr(request, 'GET', {}).get('showroom') if hasattr(request, 'GET') else None
    if showroom_param and str(showroom_param).isdigit():
        return int(showroom_param)
    return None


def is_all_showrooms_mode(request):
    """التحقق إذا كان المستخدم في وضع 'جميع الفروع'."""
    if not request:
        return False
    # التحقق من الخاصية المباشرة
    if getattr(request, 'show_all_showrooms', False):
        return True
    # التحقق من الجلسة
    sess = getattr(request, 'session', None)
    if sess and sess.get('SHOW_ALL_SHOWROOMS', False):
        return True
    return False


def get_user_showroom_ids(request):
    """الحصول على قائمة معرفات الفروع المتاحة للمستخدم.
    مفيد عند الحاجة لفلترة البيانات لعدة فروع.
    """
    if not request or not request.user.is_authenticated:
        return []
    user = request.user
    if user.is_superuser:
        from .models import Showroom
        return list(Showroom.objects.values_list('id', flat=True))
    assigned = ShowroomEmployee.objects.filter(user=user, active=True)
    if assigned.filter(can_cross_access=True).exists():
        from .models import Showroom
        return list(Showroom.objects.values_list('id', flat=True))
    return list(assigned.values_list('showroom_id', flat=True))

class ActiveShowroomScopedQuerysetMixin:
    """Mixin لفلترة queryset حسب المعرض النشط.
    يتوقع وجود request.active_showroom_id (يوفره middleware) ويضيف حماية منع الوصول العرضي.
    - لو المستخدم superuser أو لديه can_cross_access يترك كل شيء (إلا إذا أُجبر).
    - يمكن ضبط الحقول المحتملة للاسم الأجنبي عبر SHOWROOM_FIELD_CANDIDATES.
    """
    SHOWROOM_FIELD_CANDIDATES = [
    # Generic direct FK names
    'showroom', 'showroom_id',
    # Reverse OneToOne on Location now uses related_name='showroom_link'
    'showroom_link', 'showroom_link__id',
    'location__showroom_link', 'location__showroom_link__id',
        'pos_session__showroom', 'pos_session__showroom_id',
    ]
    force_scope = True  # لو True يفرض دائماً حتى لو المستخدم cross access

    def get_base_queryset(self):  # يسمح للـ view بتعريف get_queryset ثم نطبق التحجيم
        return super().get_queryset()

    def get_queryset(self):
        qs = self.get_base_queryset()
        request = getattr(self, 'request', None)
        if not request:
            return qs
        active_id = get_active_showroom_id(request)
        if not active_id:
            return qs
        user = request.user
        if user.is_superuser and not self.force_scope:
            return qs
        # تحقق من صلاحية cross_access (إلغاء العزل إن وُجد ورُفع force_scope)
        if not self.force_scope:
            if ShowroomEmployee.objects.filter(user=user, can_cross_access=True, active=True).exists():
                return qs
        # حاول إيجاد أول حقل صالح
        for field in self.SHOWROOM_FIELD_CANDIDATES:
            try:
                return qs.filter(**{field: active_id})
            except Exception:
                continue
        return qs  # fallback silent إذا لم نجد حقلاً

def scope_queryset_to_active_showroom(request, queryset, showroom_field_candidates=None, respect_all_mode=True):
    """وظيفة مساعدة لعزل أي QuerySet حسب المعرض النشط خارج سياق DRF mixin.
    تحاول تطبيق أول حقل متاح من الحقول المحتملة.
    
    Args:
        request: طلب HTTP
        queryset: الـ QuerySet المراد فلترته
        showroom_field_candidates: قائمة أسماء الحقول المحتملة للفلترة
        respect_all_mode: إذا True ولم يُختر فرع محدد، يرجع كل البيانات (جميع الفروع)
    
    Returns:
        QuerySet مفلتر أو كامل حسب الوضع
    """
    if showroom_field_candidates is None:
        showroom_field_candidates = ActiveShowroomScopedQuerysetMixin.SHOWROOM_FIELD_CANDIDATES
    
    # التحقق من وضع "جميع الفروع"
    if respect_all_mode and is_all_showrooms_mode(request):
        # في وضع جميع الفروع للمدراء - عرض كل البيانات
        return queryset
    
    sid = get_active_showroom_id(request)
    if not sid:
        # لا يوجد فرع محدد ولا وضع "جميع الفروع"
        # للمدراء: عرض كل البيانات، لغيرهم: فلترة حسب فروعهم المتاحة
        if request and request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return queryset
            # فلترة للفروع المتاحة للمستخدم
            user_showroom_ids = get_user_showroom_ids(request)
            if user_showroom_ids:
                for field in showroom_field_candidates:
                    try:
                        return queryset.filter(**{f'{field}__in': user_showroom_ids})
                    except Exception:
                        continue
        return queryset
    
    for field in showroom_field_candidates:
        try:
            return queryset.filter(**{field: sid})
        except Exception:
            continue
    return queryset

class ShowroomActionPermissionMixin:
    required_module = None
    required_action = 'view'

    def check_showroom_permission(self):
        sid = get_active_showroom_id(self.request)
        if not sid or not self.required_module:
            return
        if not showroom_has_action(self.request.user, sid, self.required_module, self.required_action):
            raise PermissionDenied('لا تملك صلاحية إجراء هذا الفعل في المعرض الحالي')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.check_showroom_permission()
