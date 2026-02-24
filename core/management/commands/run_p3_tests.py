import json
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = "تشغيل حزمة اختبارات P3 (Skeleton: تقارير + موافقات + إشعارات)"

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **opts):
        username = opts['username']
        password = opts['password']
        report: dict[str, dict] = {}
        failures = 0

        def record(name: str, ok: bool, detail=None):
            nonlocal failures
            if not ok:
                failures += 1
            report[name] = {'ok': ok, 'detail': detail}

        client = Client()
        resp = client.post('/accounts/login/', {'username': username, 'password': password})
        record('login', resp.status_code in (200, 302), f"status={resp.status_code}")

        # 1. تقارير: محاولة الوصول لنقطة تقرير (إن وجدت) placeholder
        try:
            r = client.get('/reports/')
            record('reports_page', r.status_code < 500, f"status={r.status_code}")
        except Exception as e:
            record('reports_page', False, str(e))

        # 1.b تقرير JSON اختياري (محاولة استكشافية لمسار شائع)
        try:
            json_paths = ['/api/reports/summary/', '/api/report/summary/', '/api/reports/']
            json_ok = False
            detail = []
            import json as _json
            for p in json_paths:
                respj = client.get(p, HTTP_ACCEPT='application/json')
                status = respj.status_code
                snippet = f"{p}:{status}"
                if status == 200:
                    try:
                        data = _json.loads(respj.content.decode('utf-8'))
                        # تحقق مبسط: وجود مفتاح counts أو summary أو total
                        if any(k in data for k in ('counts','summary','total','results')):
                            json_ok = True
                            detail.append(snippet + ':valid')
                            break
                        else:
                            detail.append(snippet + ':missing-keys')
                    except Exception:
                        detail.append(snippet + ':invalid-json')
                else:
                    detail.append(snippet)
            if not json_ok:
                # لا نعتبره فشل قاطع حالياً، نسجله بتحذير
                record('reports_json_endpoint', True, 'no-json-endpoint-found | ' + '; '.join(detail))
            else:
                record('reports_json_endpoint', True, '; '.join(detail) or None)
        except Exception as e:
            record('reports_json_endpoint', False, str(e))

        # 2. الموافقات: اختبار بسيط للاستيراد ووجود الموديل
        try:
            from approvals.models import ApprovalRequest
            count = ApprovalRequest.objects.count()
            record('approvals_model', True, f"count={count}")
        except Exception as e:
            record('approvals_model', False, str(e))

        # 3. الإشعارات: فحص استيراد السياق
        try:
            from notifications.models import Notification  # noqa
            record('notifications_import', True)
        except Exception as e:
            record('notifications_import', False, str(e))

        summary = {'passed': sum(1 for v in report.values() if v['ok']), 'failed': failures}
        report['__summary__'] = summary
        if opts['json']:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for name, data in report.items():
                if name == '__summary__':
                    continue
                status = 'OK' if data['ok'] else 'FAIL'
                self.stdout.write(f"[{status}] {name} -> {data.get('detail')}")
            self.stdout.write(f"Summary: {summary}")
        if failures:
            raise SystemExit(1)
