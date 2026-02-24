from django.utils.deprecation import MiddlewareMixin
from .models import Showroom, ShowroomEmployee
from django.utils import timezone

SESSION_KEY = 'ACTIVE_SHOWROOM_ID'
ALL_SHOWROOMS_KEY = 'SHOW_ALL_SHOWROOMS'

class ActiveShowroomMiddleware(MiddlewareMixin):
    """Middleware لتثبيت معرف المعرض الحالي في الجلسة (من ?showroom= أو أول معرض مسموح)."""
    def process_request(self, request):
        if not request.user.is_authenticated:
            return
        
        # اختيار مباشر عبر GET ?showroom=
        sid = request.GET.get('showroom')
        
        # التحقق من اختيار "جميع الفروع"
        if sid == 'all':
            if request.user.is_superuser or request.user.is_staff:
                request.session[ALL_SHOWROOMS_KEY] = True
                request.session.modified = True  # Force session save
                if SESSION_KEY in request.session:
                    del request.session[SESSION_KEY]
                request.show_all_showrooms = True
                request.active_showroom_id = None
                return
        elif sid and sid.isdigit():
            # إلغاء وضع "جميع الفروع" عند اختيار فرع محدد
            if ALL_SHOWROOMS_KEY in request.session:
                del request.session[ALL_SHOWROOMS_KEY]
            if self._user_has_showroom(request.user, int(sid)):
                request.session[SESSION_KEY] = int(sid)
        
        # التحقق من وضع "جميع الفروع" في الجلسة
        if request.session.get(ALL_SHOWROOMS_KEY):
            request.show_all_showrooms = True
            request.active_showroom_id = None
            return
        else:
            request.show_all_showrooms = False
        
        # عدم وجود معامل showroom في طلبات /api/ => إزالة أي قيمة سابقة لفرض العزل حتى يتم اختيارها صراحة
        if request.path.startswith('/api/') and 'showroom' not in request.GET:
            if SESSION_KEY in request.session:
                del request.session[SESSION_KEY]
        # تحقق من الجلسة الحالية
        active_id = request.session.get(SESSION_KEY)
        # سياسة جديدة: لا نقوم بالتعيين التلقائي لأول معرض داخل واجهات /api/ إلا إذا أرسله العميل صراحة
        if not active_id or not self._user_has_showroom(request.user, active_id):
            # سياسة جديدة: لا يتم التعيين التلقائي إطلاقاً، يتطلب تحديد صريح (?showroom=) أو جلسة سابقة
            request.active_showroom_id = None
            # تعيين تلقائي لأول معرض متاح (ليس في واجهات API)
            if not request.path.startswith('/api/'):
                first = self._first_showroom(request.user)
                if first:
                    request.session[SESSION_KEY] = first.id
                    request.active_showroom_id = first.id
            return
        request.active_showroom_id = active_id

    def _user_has_showroom(self, user, showroom_id):
        if user.is_superuser:
            return Showroom.objects.filter(id=showroom_id).exists()
        assigns = ShowroomEmployee.objects.filter(user=user, active=True)
        # مدير/مشرف المعرض يقتصر على معارضه حتى لو كان can_cross_access=True
        if assigns.filter(role__in=['manager', 'supervisor']).exists():
            return assigns.filter(showroom_id=showroom_id).exists()
        if assigns.filter(can_cross_access=True).exists():
            return True
        return assigns.filter(showroom_id=showroom_id).exists()

    def _first_showroom(self, user):
        if user.is_superuser:
            return Showroom.objects.order_by('code').first()
        emp = ShowroomEmployee.objects.filter(user=user, active=True).select_related('showroom').first()
        if emp:
            return emp.showroom
        return None

    def __call__(self, request):
        response = self.get_response(request)
        # وضع فلاغ للاستخدام في القوالب لإخفاء القائمة عند وجود معرض واحد فقط
        try:
            if hasattr(request, 'user') and request.user.is_authenticated:
                from .models import ShowroomEmployee
                if not request.session.get('active_showroom_id'):
                    pass
                assigns = ShowroomEmployee.objects.filter(user=request.user, active=True)
                request.single_showroom_mode = assigns.count() == 1
            else:
                request.single_showroom_mode = False
        except Exception:
            request.single_showroom_mode = False
        return response
