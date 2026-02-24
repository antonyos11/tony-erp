from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal

from .models import ApprovalRequest, ApprovalAction
from accounting.models import JournalEntry


User = get_user_model()


class ApprovalFlowTests(TestCase):
    """اختبارات بسيطة لتأكد من منطق طلبات الموافقة."""

    def setUp(self):
        self.user = User.objects.create_user(username="approver", password="pw")
        self.requester = User.objects.create_user(username="requester", password="pw2")
        self.client = Client()
        # نستخدم قيد محاسبي كمثال على object محمي بالموافقة
        self.entry = JournalEntry.objects.create(description="Test entry")
        self.ct = ContentType.objects.get_for_model(JournalEntry)

    def test_approval_request_clean_levels_validation(self):
        req = ApprovalRequest(
            requested_by=self.requester,
            content_type=self.ct,
            object_id=self.entry.pk,
            amount=Decimal("100.00"),
            required_levels=0,
        )
        with self.assertRaises(Exception):
            req.full_clean()

    def test_basic_approve_and_reject_flow(self):
        req = ApprovalRequest.objects.create(
            requested_by=self.requester,
            content_type=self.ct,
            object_id=self.entry.pk,
            amount=Decimal("200.00"),
            required_levels=1,
        )

        # approve
        ok = req.approve(self.user, note="ok")
        self.assertTrue(ok)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.Status.APPROVED)
        self.assertEqual(ApprovalAction.objects.filter(approval=req).count(), 1)

        # لا يمكن الموافقة مرة أخرى على نفس الطلب النهائي
        second = req.approve(self.user)
        self.assertFalse(second)

    def test_approve_via_view_as_superuser(self):
        """تجربة مسار الموافقة عبر الـ view مع superuser (يتجاوز صلاحيات get_approvers)."""
        superuser = User.objects.create_superuser(username="admin", password="pw3", email="admin@example.com")
        req = ApprovalRequest.objects.create(
            requested_by=self.requester,
            content_type=self.ct,
            object_id=self.entry.pk,
            amount=Decimal("300.00"),
            required_levels=1,
        )
        self.client.login(username="admin", password="pw3")
        response = self.client.post(f"/approvals/{req.pk}/approve/", {"note": "ok"})
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.Status.APPROVED)

    def test_reject_via_view_as_superuser(self):
        req = ApprovalRequest.objects.create(
            requested_by=self.requester,
            content_type=self.ct,
            object_id=self.entry.pk,
            amount=Decimal("400.00"),
            required_levels=1,
        )
        superuser = User.objects.create_superuser(username="admin2", password="pw4", email="admin2@example.com")
        self.client.login(username="admin2", password="pw4")
        response = self.client.post(f"/approvals/{req.pk}/reject/", {"note": "no"})
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.Status.REJECTED)


