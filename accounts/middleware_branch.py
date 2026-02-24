"""
Middleware لتصفية البيانات حسب الفرع
======================================
يقوم بتعيين الفرع الحالي في الـ request تلقائياً
ويتيح للمستخدم تبديل الفرع عبر header أو session.
"""

import logging

logger = logging.getLogger(__name__)


class BranchFilterMiddleware:
    """
    Middleware لإدارة الفرع الحالي للمستخدم
    يضيف request.current_branch و request.user_branches
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_branch = None
        request.user_branches = []

        if hasattr(request, 'user') and request.user.is_authenticated:
            self._set_branch_context(request)

        response = self.get_response(request)
        return response

    def _set_branch_context(self, request):
        """تعيين سياق الفرع في الطلب"""
        from accounts.services import PermissionService

        try:
            user_branches = PermissionService.get_user_branches(request.user)
            request.user_branches = list(user_branches) if user_branches else []

            branch_id = (
                request.headers.get('X-Branch-ID') or
                request.session.get('current_branch_id')
            )

            if branch_id:
                try:
                    branch_id = int(branch_id)
                    if PermissionService.can_user_access_branch(
                        request.user, branch_id, 'view'
                    ):
                        from branches.models import Branch
                        try:
                            request.current_branch = Branch.objects.get(
                                pk=branch_id, is_active=True
                            )
                            request.session['current_branch_id'] = branch_id
                        except Branch.DoesNotExist:
                            pass
                    else:
                        logger.warning(
                            f"المستخدم {request.user} حاول الوصول "
                            f"لفرع {branch_id} بدون صلاحية"
                        )
                except (ValueError, TypeError):
                    pass

            if not request.current_branch:
                default_branch = PermissionService.get_default_branch(request.user)
                if default_branch:
                    request.current_branch = default_branch
                    request.session['current_branch_id'] = default_branch.pk

        except Exception as e:
            logger.error(f"خطأ في BranchFilterMiddleware: {e}")
