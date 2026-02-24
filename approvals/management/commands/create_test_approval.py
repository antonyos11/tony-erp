from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from approvals.services import create_approval_for
from approvals.models import ApprovalRequest
from django.contrib.contenttypes.models import ContentType

class DummyObject:
    # كائن بسيط في الذاكرة فقط لاختبار GenericForeignKey (لن يُحفظ)
    pk = 1
    id = 1

class Command(BaseCommand):
    help = 'إنشاء طلب موافقة تجريبي (للاختبار).'

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('لا يوجد مستخدمون.'))
            return
        # نستخدم ContentType لنموذج موجود (User) كمرجع وهمي لسهولة الاختبار
        ct = ContentType.objects.get_for_model(User)
        approval = ApprovalRequest.objects.create(
            content_type=ct,
            object_id=user.pk,
            requested_by=user,
            amount=500,
            reason='موافقة تجريبية',
            required_levels=1,
        )
        self.stdout.write(self.style.SUCCESS(f'إنشاء طلب موافقة تجريبي #{approval.id}'))
