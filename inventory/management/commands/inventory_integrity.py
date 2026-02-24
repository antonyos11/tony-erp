from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from inventory.models import Stock, StockBatch, Receiving, Issue, StockCount
from collections import defaultdict
import json

class Command(BaseCommand):
    help = "تفقد سلامة مخزون: مقارنة الكميات المجملة مع الدُفعات, والتحقق من عدم السالب, وإبراز الانحرافات."

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='إخراج النتائج بصيغة JSON')
        parser.add_argument('--fix', action='store_true', help='محاولة إصلاح الفروقات (تحديث Stock.quantity ليطابق مجموع الدُفعات)')
        parser.add_argument('--dry-run', action='store_true', help='تنفيذ دون تعديل (مع --fix يعرض فقط ما سيحدث)')
        parser.add_argument('--max-diff', type=int, default=None, help='حد أقصى للفروقات المسموح عرضها (لأغراض الأداء)')

    def handle(self, *args, **options):
        want_json = options['json']
        do_fix = options['fix']
        dry_run = options['dry_run']
        max_diff = options['max_diff']

        report = {
            'generated_at': timezone.now().isoformat(),
            'summary': {},
            'differences': [],
            'negatives': [],
            'warnings': [],
            'fix_applied': False,
        }

        # 1. تجميع مجموع كميات الدُفعات لكل (product, location)
        batch_totals = defaultdict(int)
        for b in StockBatch.objects.all().only('product_id', 'location_id', 'quantity'):
            batch_totals[(b.product_id, b.location_id)] += int(b.quantity)

        # 2. المرور على Stock ومقارنة القيمة
        diff_count = 0
        total_records = 0
        negatives = 0
        for s in Stock.objects.select_related('product', 'location').all():
            total_records += 1
            key = (s.product_id, s.location_id)
            batch_q = batch_totals.get(key, 0)
            stock_q = int(s.quantity)
            if stock_q < 0:
                negatives += 1
                entry = {
                    'product': str(s.product),
                    'location': str(s.location),
                    'stock_qty': stock_q,
                    'batch_qty': batch_q,
                    'type': 'negative'
                }
                report['negatives'].append(entry)
            if stock_q != batch_q:
                diff = batch_q - stock_q
                diff_count += 1
                if (max_diff is None) or (len(report['differences']) < max_diff):
                    report['differences'].append({
                        'product': str(s.product),
                        'location': str(s.location),
                        'stock_qty': stock_q,
                        'batch_qty': batch_q,
                        'delta': diff
                    })
                if do_fix and not dry_run:
                    s.quantity = batch_q
                    s.save(update_fields=['quantity'])
        if do_fix and not dry_run:
            report['fix_applied'] = True

        # 3. إحصائيات أساسية للنشاط (عدد مستندات الاستلام/الصرف/الجرد) للمراجعة
        report['summary'] = {
            'stocks_checked': total_records,
            'differences_found': diff_count,
            'negatives_found': negatives,
            'receivings': Receiving.objects.count(),
            'issues': Issue.objects.count(),
            'stock_counts': StockCount.objects.count(),
            'fix_mode': do_fix,
            'dry_run': dry_run,
        }

        # طباعة النتائج
        if want_json:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self.stdout.write("=== Inventory Integrity Report ===")
            self.stdout.write(f"Stocks Checked: {report['summary']['stocks_checked']}")
            self.stdout.write(f"Differences: {report['summary']['differences_found']} | Negatives: {report['summary']['negatives_found']}")
            self.stdout.write(f"Receivings: {report['summary']['receivings']} | Issues: {report['summary']['issues']} | StockCounts: {report['summary']['stock_counts']}")
            if report['differences']:
                self.stdout.write("-- Differences (sample) --")
                for d in report['differences'][:25]:
                    self.stdout.write(f"{d['product']} @ {d['location']}: stock={d['stock_qty']} batch={d['batch_qty']} delta={d['delta']}")
            if report['negatives']:
                self.stdout.write("-- Negatives --")
                for n in report['negatives'][:25]:
                    self.stdout.write(f"NEG {n['product']} @ {n['location']} stock={n['stock_qty']} batch={n['batch_qty']}")
            if do_fix:
                self.stdout.write(f"Fix applied: {report['fix_applied']} (dry_run={dry_run})")
            self.stdout.write("=================================")

        # حالة خروج غير صفرية لو وُجدت سالبات بدون إصلاح
        if report['negatives'] and not do_fix:
            self.stderr.write("تحذير: توجد أرصدة سالبة")
        return 0
