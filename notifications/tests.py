from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from .models import Notification


User = get_user_model()


class NotificationTests(TestCase):
    """اختبارات أساسية لنظام الإشعارات."""

    def setUp(self):
        self.user = User.objects.create_user(username="user1", password="pw")
        self.client = Client()

    def test_create_notification_and_str(self):
        note = Notification.objects.create(
            user=self.user,
            title="Test",
            message="Hello",
            level="info",
        )
        self.assertIn("Test", str(note))
        self.assertFalse(note.is_read)

    def test_mark_read_query_helpers(self):
        Notification.objects.create(user=self.user, title="A", message="1", level="info")
        Notification.objects.create(user=self.user, title="B", message="2", level="warning")
        unread = Notification.objects.filter(user=self.user, is_read=False)
        self.assertEqual(unread.count(), 2)
        unread.update(is_read=True)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_notification_list_ajax_and_mark_all_read_view(self):
        n1 = Notification.objects.create(user=self.user, title="A", message="1", level="info")
        Notification.objects.create(user=self.user, title="B", message="2", level="warning")
        self.client.login(username="user1", password="pw")
        # طلب AJAX لقائمة الإشعارات
        response = self.client.get(
            "/notifications/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)

        # تعليم الكل كمقروء عبر view
        response2 = self.client.post(
            "/notifications/mark-all/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_mark_single_notification_read_view(self):
        n = Notification.objects.create(user=self.user, title="A", message="1", level="info")
        self.client.login(username="user1", password="pw")
        response = self.client.post(
            f"/notifications/{n.pk}/read/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

