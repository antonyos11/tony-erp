"""
Context Processors — RITA ERP
يضيف بيانات الفرع لكل الـ Templates
"""


def branch_context(request):
    """
    يضيف بيانات الفرع الحالي لكل الـ Templates تلقائياً
    """
    from apps.core.models import Branch

    context = {
        'current_branch': getattr(request, 'current_branch', None),
        'can_see_all_branches': getattr(request, 'can_see_all_branches', False),
    }

    if getattr(request, 'can_see_all_branches', False):
        context['all_branches'] = Branch.objects.filter(is_active=True).order_by('name')

    return context


def notification_context(request):
    """يضيف عدد الإشعارات غير المقروءة وآخر الإشعارات لكل الـ Templates"""
    if request.user.is_authenticated:
        from apps.notifications.models import Notification
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user, is_read=False)[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent,
        }
    return {}


def dynamic_menu(request):
    """
    يبني القائمة الجانبية ديناميكياً حسب صلاحيات المستخدم
    Sprint 22A
    """
    if not request.user.is_authenticated:
        return {'sidebar_menu': []}

    from apps.authorization.services.menu_builder import MenuBuilder
    from apps.authorization.services.permission_engine import PermissionEngine

    menu = MenuBuilder.build_menu(request.user)
    user_permissions = PermissionEngine.get_user_permissions(request.user)
    max_discount = PermissionEngine.get_max_discount(request.user)

    # user_permissions قد يكون set أو dict حسب النموذج المستخدم
    if isinstance(user_permissions, set):
        can_view_cost = 'view_cost_price' in user_permissions or request.user.is_superuser
        can_view_profit = 'view_profit' in user_permissions or request.user.is_superuser
    else:
        can_view_cost = request.user.is_superuser or bool(
            user_permissions.get('accounts', {}).get('view_cost')
            or user_permissions.get('inventory', {}).get('view_cost')
        )
        can_view_profit = request.user.is_superuser or bool(
            user_permissions.get('sales', {}).get('view_profit')
        )

    # Sprint 23 — عدد طلبات الاعتماد المعلقة
    try:
        from apps.authorization.models import ApprovalRequest
        pending_approvals = ApprovalRequest.objects.filter(status='pending').count()
    except Exception:
        pending_approvals = 0

    return {
        'sidebar_menu': menu,
        'user_permissions': user_permissions,
        'user_max_discount': max_discount,
        'can_view_cost': can_view_cost,
        'can_view_profit': can_view_profit,
        'pending_approvals': pending_approvals,
    }



def company_context(request):
    """يضيف بيانات الشركة الرئيسية لكل الـ Templates — Sprint 24"""
    try:
        from apps.core.models import Company
        company = Company.objects.filter(code='MAIN').first()
        return {'main_company': company}
    except Exception:
        return {'main_company': None}
