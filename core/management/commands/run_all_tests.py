import json
import importlib
from django.core.management.base import BaseCommand
from django.core import management


class Command(BaseCommand):
    help = "تشغيل جميع حزم الاختبارات (P1 ثم P2 ثم P3) وإخراج تقرير موحد"

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--json', action='store_true')
        parser.add_argument('--stop-on-fail', action='store_true', help='إيقاف التنفيذ عند أول فشل في حزمة')

    def handle(self, *args, **opts):
        username = opts['username']
        password = opts['password']
        stop_on_fail = opts['stop_on_fail']
        full_report: dict[str, dict] = {}
        order = [
            ('p1', 'run_p1_tests'),
            ('p2', 'run_p2_tests'),
            ('p3', 'run_p3_tests'),
        ]
        total_failed = 0

        for label, cmd in order:
            try:
                # Capture JSON output by invoking the command programmatically
                out_collector: list[str] = []

                class _StdoutCapture:
                    def write(self, *args, **kwargs):  # Django may pass (string,) or (string, ending)
                        if not args:
                            return
                        out_collector.append(args[0])
                    def flush(self):
                        pass

                management.call_command(cmd, username=username, password=password, json=True, stdout=_StdoutCapture())
                raw = ''.join(out_collector)
                data = json.loads(raw)
                full_report[label] = data
                summary = data.get('__summary__', {})
                failed = summary.get('failed', 0)
                total_failed += failed
                if failed and stop_on_fail:
                    break
            except SystemExit as e:  # in case underlying command raises due to failures
                # Attempt to parse what we collected
                try:
                    raw = ''.join(out_collector)
                    data = json.loads(raw)
                    full_report[label] = data
                    summary = data.get('__summary__', {})
                    failed = summary.get('failed', 0)
                    total_failed += failed
                except Exception:
                    full_report[label] = {'__error__': f'فشل تشغيل {cmd}: {e}'}
                    total_failed += 1
                if stop_on_fail:
                    break
            except Exception as e:
                full_report[label] = {'__error__': f'استثناء أثناء تشغيل {cmd}: {e}'}
                total_failed += 1
                if stop_on_fail:
                    break

        # Aggregate summary
        aggregate = {
            'total_failed': total_failed,
            'suites': {k: v.get('__summary__', {}) for k, v in full_report.items() if isinstance(v, dict)},
        }
        full_report['__aggregate__'] = aggregate

        if opts['json']:
            self.stdout.write(json.dumps(full_report, ensure_ascii=False, indent=2))
        else:
            for label in ['p1', 'p2', 'p3']:
                suite = full_report.get(label)
                if not suite:
                    self.stdout.write(f"[{label}] لم يتم التشغيل")
                    continue
                if '__error__' in suite:
                    self.stdout.write(f"[{label}] ERROR: {suite['__error__']}")
                    continue
                summ = suite.get('__summary__', {})
                self.stdout.write(f"[{label}] passed={summ.get('passed')} failed={summ.get('failed')}")
            self.stdout.write(f"TOTAL FAILED: {total_failed}")
        if total_failed:
            raise SystemExit(1)
