from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalRequest
from users.models import UserRole

def create_approval_for(obj, requested_by: User, amount=None, reason='', required_levels=1):
    ct = ContentType.objects.get_for_model(obj.__class__)
    return ApprovalRequest.objects.create(
        content_type=ct,
        object_id=obj.pk,
        requested_by=requested_by,
        amount=amount,
        reason=reason,
        required_levels=required_levels
    )

def get_approvers(amount: float | int | None, current_level: int):
    amount = amount or 0
    roles = UserRole.objects.filter(can_approve=True, approval_level__gte=current_level)
    qs = User.objects.filter(profile__role__in=roles, is_active=True).distinct()
    if amount > 0:
        # max_approval_amount == 0 treated as unlimited
        qs = [u for u in qs if getattr(u.profile.role, 'max_approval_amount', 0) == 0 or u.profile.role.max_approval_amount >= amount]
    return list(qs)