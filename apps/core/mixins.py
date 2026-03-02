"""
Mixins للـ Views — فلترة حسب الفرع
"""
from django.contrib.auth.mixins import LoginRequiredMixin


class BranchFilterMixin:
    """
    يفلتر الـ QuerySet حسب فرع المستخدم.
    لازم الـ Model يكون فيه حقل branch (أو المسار المحدد في branch_field).
    """
    branch_field = 'branch'  # اسم حقل الفرع في الـ Model

    def get_queryset(self):
        qs = super().get_queryset()

        can_see_all = getattr(self.request, 'can_see_all_branches', False)
        current_branch = getattr(self.request, 'current_branch', None)

        if can_see_all:
            # Admin أو من لديه صلاحية — لو اختار فرع يفلتر عليه
            if current_branch:
                return qs.filter(**{self.branch_field: current_branch})
            return qs  # يشوف كل الفروع

        # مستخدم عادي — فرعه فقط
        if current_branch:
            return qs.filter(**{self.branch_field: current_branch})

        return qs.none()  # ما عندوش فرع — لا يرى أي بيانات


class BranchCreateMixin:
    """
    يعيّن الفرع تلقائياً عند إنشاء سجل جديد،
    ويضبط created_by / updated_by.
    """

    def form_valid(self, form):
        if hasattr(form.instance, 'branch') and not form.instance.branch_id:
            form.instance.branch = getattr(self.request, 'current_branch', None)
        if hasattr(form.instance, 'created_by') and not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        if hasattr(form.instance, 'updated_by'):
            form.instance.updated_by = self.request.user
        return super().form_valid(form)


class AdminRequiredMixin(LoginRequiredMixin):
    """يتأكد أن المستخدم admin (superuser أو staff)"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_superuser or request.user.is_staff):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def apply_branch_filter(qs, request, branch_field='branch'):
    """
    دالة مساعدة — تطبّق فلتر الفرع على أي QuerySet.
    استخدم branch_field لتحديد مسار حقل الفرع (مثل 'warehouse__branch').
    """
    branch = getattr(request, 'current_branch', None)
    can_see_all = getattr(request, 'can_see_all_branches', False)

    if can_see_all and not branch:
        return qs  # Admin بدون فلتر — يشوف كل حاجة

    if branch:
        return qs.filter(**{branch_field: branch})

    return qs.none()  # لا توجد بيانات للمستخدم
