from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from core.models import AuditLog

class ManagementCommandsTests(TestCase):
    def test_explain_queries_model(self):
        out = StringIO()
        call_command('explain_queries', '--model', 'core.AuditLog', '--limit', '0', stdout=out)
        data = out.getvalue()
        self.assertIn('EXPLAIN', data.upper())
        self.assertTrue(len(data.splitlines()) >= 2)

    def test_archive_audit_logs_no_logs(self):
        out = StringIO()
        call_command('archive_audit_logs', '--days', '999999', stdout=out)
        self.assertIn('No logs to archive', out.getvalue())

    def test_archive_audit_logs_with_log_and_delete(self):
        log = AuditLog.objects.create(action=AuditLog.ACTION_CREATE)
        out = StringIO()
        call_command('archive_audit_logs', '--days', '0', '--delete', stdout=out)
        content = out.getvalue()
        self.assertIn('Archived 1 logs', content)
        self.assertFalse(AuditLog.objects.filter(id=log.id).exists())
