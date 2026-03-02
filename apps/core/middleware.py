"""
Middleware لتحديد الفرع النشط للمستخدم
"""
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse


class BranchMiddleware(MiddlewareMixin):
    """
    يحدد الفرع النشط للمستخدم ويضعه في request.current_branch
    - لو المستخدم معين على فرع → الفرع ده
    - لو المستخدم عنده صلاحية "يرى فروع أخرى" → يقدر يغير الفرع من الـ session
    - لو admin → يشوف كل الفروع
    """

    def process_request(self, request):
        request.current_branch = None
        request.can_see_all_branches = False

        if not request.user.is_authenticated:
            return

        # Admin يشوف كل حاجة
        if request.user.is_superuser or request.user.is_staff:
            request.can_see_all_branches = True
            # لو اختار فرع معين من الـ session
            branch_id = request.session.get('active_branch_id')
            if branch_id:
                from apps.core.models import Branch
                try:
                    request.current_branch = Branch.objects.get(
                        id=branch_id, is_active=True
                    )
                except Branch.DoesNotExist:
                    request.session.pop('active_branch_id', None)
            return

        # المستخدم العادي — فرعه المحدد
        request.current_branch = getattr(request.user, 'branch', None)

        # التحقق من صلاحية رؤية فروع أخرى عبر الـ roles
        try:
            from apps.authorization.models import UserRole
            user_role_qs = UserRole.objects.filter(
                user=request.user
            ).select_related('role')
            for user_role in user_role_qs:
                if getattr(user_role.role, 'can_see_all_branches', False):
                    request.can_see_all_branches = True
                    branch_id = request.session.get('active_branch_id')
                    if branch_id:
                        from apps.core.models import Branch
                        try:
                            request.current_branch = Branch.objects.get(
                                id=branch_id, is_active=True
                            )
                        except Branch.DoesNotExist:
                            request.session.pop('active_branch_id', None)
                    break
        except Exception:
            pass


# ══════════════════════════════════════════════════════
# SetupWizardMiddleware — تحويل لمعالج الإعداد الأولي
# ══════════════════════════════════════════════════════

class SetupWizardMiddleware(MiddlewareMixin):
    """
    Sprint 24 — عند أول تشغيل للنظام (setup_completed=False)
    يُحوِّل المدير العام تلقائياً لمعالج الإعداد الأولي.
    """

    # مسارات يُسمح بها دون إعداد
    ALLOWED_PATHS_PREFIXES = (
        '/admin/',
        '/accounts/',
        '/static/',
        '/media/',
        '/setup/',
        '/favicon',
    )

    def process_request(self, request):
        if not request.user.is_authenticated:
            return
        if not request.user.is_superuser:
            return

        # تجاهل المسارات المسموح بها
        path = request.path
        for prefix in self.ALLOWED_PATHS_PREFIXES:
            if path.startswith(prefix):
                return

        try:
            from apps.core.models import Company
            company = Company.objects.filter(code='MAIN').first()
            if company and not company.setup_completed:
                wizard_url = reverse('core:setup_wizard')
                if path != wizard_url:
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect(f"{wizard_url}?step=1")
        except Exception:
            pass
