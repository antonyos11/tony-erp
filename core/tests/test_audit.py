from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings

from core.models import Company, AuditLog, AppSettings


@override_settings(TESTING=False)
class AuditLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u1', password='p1')
        self.client.force_login(self.user)

    def test_create_logs_with_initial_values(self):
        company = Company.objects.create(name='C1')
        log = AuditLog.objects.filter(model_name='Company', object_id=str(company.pk), action='create').first()
        self.assertIsNotNone(log)
        self.assertIn('name', log.changes)
        self.assertEqual(log.changes['name'].get('new'), 'C1')

    def test_update_logs_with_field_diff(self):
        company = Company.objects.create(name='C2')
        company.name = 'C2-updated'
        company.save()
        log = AuditLog.objects.filter(model_name='Company', object_id=str(company.pk), action='update').first()
        self.assertIsNotNone(log)
        self.assertIn('name', log.changes)
        self.assertEqual(log.changes['name'].get('old'), 'C2')
        self.assertEqual(log.changes['name'].get('new'), 'C2-updated')

    def test_delete_logs_recorded(self):
        company = Company.objects.create(name='C3')
        pk = company.pk
        company.delete()
        log = AuditLog.objects.filter(model_name='Company', object_id=str(pk), action='delete').first()
        self.assertIsNotNone(log)


@override_settings(TESTING=False)
class AuditMaskingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u2', password='p2')
        self.client.force_login(self.user)

    @override_settings(AUDITLOG_SENSITIVE_FIELDS=["tax_id"])
    def test_masking_via_settings_on_create(self):
        company = Company.objects.create(name='S1', tax_id='TX-123')
        log = AuditLog.objects.filter(model_name='Company', object_id=str(company.pk), action='create').first()
        self.assertIsNotNone(log)
        # Value should be masked
        self.assertIn('tax_id', log.changes)
        self.assertEqual(log.changes['tax_id'].get('new'), '***')

    def test_masking_via_appsettings_on_create(self):
        cfg = AppSettings.get()
        cfg.audit_sensitive_fields = ['phone']
        cfg.save()
        company = Company.objects.create(name='S2', phone='555-9999')
        log = AuditLog.objects.filter(model_name='Company', object_id=str(company.pk), action='create').first()
        self.assertIsNotNone(log)
        self.assertIn('phone', log.changes)
        self.assertEqual(log.changes['phone'].get('new'), '***')

    @override_settings(AUDITLOG_SENSITIVE_FIELDS=["tax_id"])
    def test_masking_on_update(self):
        company = Company.objects.create(name='M1', tax_id='OLD-TX')
        company.tax_id = 'NEW-TX'
        company.save()
        log = AuditLog.objects.filter(model_name='Company', object_id=str(company.pk), action='update').first()
        self.assertIsNotNone(log)
        self.assertIn('tax_id', log.changes)
        self.assertEqual(log.changes['tax_id'].get('old'), '***')
        self.assertEqual(log.changes['tax_id'].get('new'), '***')


class AuditLogsViewExportTests(TestCase):
    def setUp(self):
        user_cls = get_user_model()
        self.user = user_cls.objects.create_user('exporter', password='p')
        perm = Permission.objects.get(codename='view_auditlog')
        self.user.user_permissions.add(perm)
        self.client.force_login(self.user)
        Company.objects.create(name='Export Co')

    def test_csv_export(self):
        resp = self.client.get('/audit-logs/?format=csv')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp.headers.get('Content-Type', ''))
        self.assertIn('attachment; filename="audit_logs.csv"', resp.headers.get('Content-Disposition', ''))
        body = resp.content.decode('utf-8')
        lines = body.splitlines()
        header = lines[0] if 'created_at' in lines[0] else (lines[1] if len(lines) > 1 else '')
        self.assertIn('created_at,action,user,app_label,model_name,object_id,object_repr,ip_address,user_agent,changes', header)

    def test_print_view(self):
        resp = self.client.get('/audit-logs/?format=print')
        self.assertEqual(resp.status_code, 200)

    def test_xlsx_export(self):
        resp = self.client.get('/audit-logs/?format=xlsx')
        self.assertEqual(resp.status_code, 200)
        ct = resp.headers.get('Content-Type', '')
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', ct)
        self.assertTrue(resp.content[:2] == b'PK')


@override_settings(TESTING=False)
class AuditAlertTests(TestCase):
    def setUp(self):
        user_cls = get_user_model()
        self.user = user_cls.objects.create_user('alerter', password='p')
        self.client.force_login(self.user)

    def test_alert_rule_triggers_send_task(self):
        cfg = AppSettings.get()
        cfg.audit_alert_rules = [{
            'name': 'NameUpdateAlert',
            'action': 'update',
            'app_label': 'core',
            'model_name': 'company',
            'fields_any': ['name'],
            'contains': {'name': 'AlertCo'}
        }]
        cfg.save()
        company = Company.objects.create(name='X')
        with patch('core.tasks.send_audit_alert.delay') as mock_delay:
            company.name = 'AlertCo'
            company.save()
            self.assertTrue(mock_delay.called, 'send_audit_alert.delay should be called when rule matches')
            args, kwargs = mock_delay.call_args
            self.assertEqual(kwargs or {}, {})
            self.assertEqual(len(args), 2)
            self.assertIsInstance(args[0], int)
            self.assertEqual(args[1], 'NameUpdateAlert')
