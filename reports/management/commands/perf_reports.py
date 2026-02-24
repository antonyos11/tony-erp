"""Management command: perf_reports

Features:
 - Times core report service functions (overview, inventory, full_system).
 - Optional sales / purchases span measurement.
 - Repeat runs to compute min/avg/max.
 - Threshold (--max-avg) + non‑zero exit (2) on breach; --fail-on-warning.
 - JSON output (--json-out) + optional CSV (--emit-csv).
 - History directory (--history-dir) with per-run JSON, CSV, JSONL append, rolling SUMMARY.md.
"""

from __future__ import annotations
import time
import json
from datetime import date, timedelta, datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from reports import services
from typing import Callable, Any

TARGET_FUNCS: list[tuple[str, Callable[..., Any], dict[str, Any]]] = [
    ("overview", services.get_overview_report, {}),
    ("inventory", services.get_inventory_report, {}),
    ("full_system", services.get_full_system_report, {}),
]


class Command(BaseCommand):
    help = "Measure execution time of key report service functions."

    def add_arguments(self, parser):  # noqa: D401
        parser.add_argument('--repeat', type=int, default=1, help='Repeat count for each function (average).')
        parser.add_argument('--sales-span', type=int, default=30, help='Days span for sales/purchases when timing them explicitly.')
        parser.add_argument('--include-sales', action='store_true', help='Include get_sales_report timing.')
        parser.add_argument('--include-purchases', action='store_true', help='Include get_purchases_report timing.')
        parser.add_argument('--json-out', type=str, help='Write results as JSON to given file path.')
        parser.add_argument('--emit-csv', action='store_true', help='Also emit CSV (with json-out or history).')
        parser.add_argument('--history-dir', type=str, help='Directory to store historical runs (created if missing).')
        parser.add_argument('--max-avg', type=float, help='Fail (exit 2) if ANY average time exceeds this many seconds.')
        parser.add_argument('--fail-on-warning', action='store_true', help='Treat any threshold warning as failure (exit 2).')

    def _time_fn(self, fn, repeat: int, **kwargs):
        times: list[float] = []
        for _ in range(repeat):
            t0 = time.perf_counter()
            fn(**kwargs)
            times.append(time.perf_counter() - t0)
        return min(times), sum(times) / len(times), max(times)

    def handle(self, *args, **opts):  # noqa: D401
        repeat = max(1, opts['repeat'])
        results: list[tuple[str, float, float, float]] = []

        # Base targets
        for name, fn, kwargs in TARGET_FUNCS:
            mn, avg, mx = self._time_fn(fn, repeat, **kwargs)
            results.append((name, mn, avg, mx))

        # Optional span-based
        span = opts['sales_span']
        date_to = date.today()
        date_from = date_to - timedelta(days=span)
        if opts.get('include_sales'):
            mn, avg, mx = self._time_fn(services.get_sales_report, repeat, date_from=date_from, date_to=date_to)
            results.append((f'sales[{span}d]', mn, avg, mx))
        if opts.get('include_purchases'):
            mn, avg, mx = self._time_fn(services.get_purchases_report, repeat, date_from=date_from, date_to=date_to)
            results.append((f'purchases[{span}d]', mn, avg, mx))

        # Threshold evaluation
        warnings: list[str] = []
        max_avg = opts.get('max_avg')
        if max_avg is not None:
            for name, _mn, avg, _mx in results:
                if avg > max_avg:
                    warnings.append(f"{name} avg {avg:.3f}s exceeds max {max_avg:.3f}s")

        # Human output
        self.stdout.write('\nReport Service Performance (seconds):')
        width = max(len(r[0]) for r in results) if results else 10
        self.stdout.write(f"{'Function'.ljust(width)}  min     avg     max")
        for name, mn, avg, mx in results:
            self.stdout.write(f"{name.ljust(width)}  {mn:.3f}  {avg:.3f}  {mx:.3f}")
        if warnings:
            self.stdout.write('\nWarnings:')
            for w in warnings:
                self.stdout.write(f" - {w}")

        # Data object
        data = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'repeat': repeat,
            'sales_span_days': span,
            'results': [
                {'function': name, 'min': mn, 'avg': avg, 'max': mx}
                for name, mn, avg, mx in results
            ],
            'warnings': warnings,
            'threshold': max_avg,
        }

        emit_csv = opts.get('emit_csv')

        # Direct JSON output
        json_out = opts.get('json_out')
        if json_out:
            try:
                with open(json_out, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.stdout.write(f"\nJSON saved to {json_out}")
                if emit_csv:
                    self._write_csv(Path(json_out + '.csv'), data)
            except OSError as e:
                raise CommandError(f'Could not write JSON/CSV: {e}')

        # History handling
        history_dir = opts.get('history_dir')
        if history_dir:
            p = Path(history_dir)
            p.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            run_json = p / f'perf_{stamp}.json'
            try:
                with run_json.open('w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                if emit_csv:
                    self._write_csv(p / f'perf_{stamp}.csv', data)
                # Append JSONL
                with (p / 'history.jsonl').open('a', encoding='utf-8') as jf:
                    jf.write(json.dumps(data, ensure_ascii=False) + '\n')
                self._update_summary(p)
                self.stdout.write(f'History saved under {p}')
            except OSError as e:
                raise CommandError(f'History write failed: {e}')

        # Exit status
        if warnings and (opts.get('fail_on_warning') or max_avg is not None):
            raise SystemExit(2)

        self.stdout.write('\nDone.')

    # ---- helpers ----
    def _write_csv(self, path: Path, data: dict):
        try:
            with path.open('w', encoding='utf-8') as cf:
                cf.write('function,min,avg,max\n')
                for r in data['results']:
                    cf.write(f"{r['function']},{r['min']:.6f},{r['avg']:.6f},{r['max']:.6f}\n")
            self.stdout.write(f'CSV saved to {path}')
        except OSError as e:
            raise CommandError(f'Could not write CSV {path}: {e}')

    def _update_summary(self, p: Path):
        try:
            lines = list((p / 'history.jsonl').open('r', encoding='utf-8'))[-10:]
            table = [
                '| Timestamp | Function | Avg (s) | Max (s) |',
                '|-----------|----------|---------|---------|'
            ]
            for ln in lines:
                try:
                    rec = json.loads(ln)
                except Exception:
                    continue
                ts = rec.get('generated_at', '')
                for r in rec.get('results', []):
                    table.append(f"| {ts} | {r['function']} | {r['avg']:.4f} | {r['max']:.4f} |")
            with (p / 'SUMMARY.md').open('w', encoding='utf-8') as sm:
                sm.write('# Performance History (last 10 runs)\n\n')
                sm.write('\n'.join(table) + '\n')
        except Exception:
            pass
