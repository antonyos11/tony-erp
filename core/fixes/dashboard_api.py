"""
Tony ERP - Dashboard Stats API Endpoint
يوفر API موحد لبيانات Dashboard عبر AJAX
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

from .dashboard_fix import DashboardDataService


@login_required
@require_GET
@never_cache
def dashboard_stats_api(request):
    """
    API endpoint لبيانات Dashboard الموحدة
    GET /api/dashboard/stats/
    """
    # تحديد الفرع
    showroom_id = None
    show_all = False
    try:
        from showrooms.mixins import get_active_showroom_id, is_all_showrooms_mode
        showroom_id = get_active_showroom_id(request)
        show_all = is_all_showrooms_mode(request)
    except Exception:
        pass

    service = DashboardDataService(showroom_id=showroom_id, show_all=show_all)
    stats = service.get_all_stats()
    return JsonResponse(stats)
