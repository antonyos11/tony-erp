"""
أمر إدارة لفحص صحة البيانات وسلامة العلاقات
يكتشف المشاكل في البيانات ويقترح الإصلاحات

الاستخدام:
    python manage.py check_data_integrity
    python manage.py check_data_integrity --fix
    python manage.py check_data_integrity --app=sales
"""

from django.core.management.base import BaseCommand
from django.db import connection, models
from django.apps import apps
from django.utils import timezone
from decimal import Decimal
import time


class Command(BaseCommand):
    help = 'فحص صحة البيانات وسلامة العلاقات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح المشاكل المكتشفة تلقائياً',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='فحص تطبيق محدد فقط',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل إضافية',
        )

    def handle(self, *args, **options):
        self.fix_mode = options['fix']
        self.verbose = options['verbose']
        self.specific_app = options.get('app')
        
        self.issues_found = 0
        self.issues_fixed = 0
        
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('فحص صحة البيانات - Tony ERP'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60 + '\n'))
        
        start_time = time.time()
        
        # فحوصات البيانات
        self.check_orphan_records()
        self.check_accounting_balance()
        self.check_inventory_consistency()
        self.check_invoice_totals()
        self.check_payment_amounts()
        self.check_duplicate_records()
        self.check_date_consistency()
        
        elapsed = time.time() - start_time
        
        # ملخص النتائج
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.MIGRATE_HEADING('ملخص النتائج:'))
        self.stdout.write('-' * 30)
        
        if self.issues_found == 0:
            self.stdout.write(self.style.SUCCESS('✓ لم يتم العثور على مشاكل'))
        else:
            self.stdout.write(f'  المشاكل المكتشفة: {self.issues_found}')
            if self.fix_mode:
                self.stdout.write(self.style.SUCCESS(f'  المشاكل المصلحة: {self.issues_fixed}'))
        
        self.stdout.write(f'\n✓ اكتمل في {elapsed:.2f} ثانية')

    def check_orphan_records(self):
        """فحص السجلات اليتيمة (بدون علاقات صالحة)"""
        self.stdout.write(self.style.HTTP_INFO('\n🔗 فحص السجلات اليتيمة:'))
        self.stdout.write('-' * 40)
        
        checks = [
            # (النموذج، الحقل، النموذج المرتبط)
            ('sales.InvoiceItem', 'invoice', 'sales.Invoice'),
            ('sales.InvoiceItem', 'product', 'inventory.Product'),
            ('purchases.PurchaseItem', 'bill', 'purchases.PurchaseBill'),
            ('purchases.PurchaseItem', 'product', 'inventory.Product'),
            ('accounting.JournalEntryItem', 'journal_entry', 'accounting.JournalEntry'),
            ('accounting.JournalEntryItem', 'account', 'accounting.Account'),
            ('inventory.Stock', 'product', 'inventory.Product'),
            ('inventory.Stock', 'location', 'inventory.Location'),
        ]
        
        for model_path, field_name, related_path in checks:
            if self.specific_app and not model_path.startswith(self.specific_app):
                continue
            
            try:
                Model = apps.get_model(model_path)
                RelatedModel = apps.get_model(related_path)
                
                # البحث عن سجلات بعلاقات مكسورة
                field = Model._meta.get_field(field_name)
                if field.null:
                    continue  # تجاهل الحقول الاختيارية
                
                orphans = Model.objects.filter(
                    **{f'{field_name}__isnull': True}
                ).count()
                
                if orphans > 0:
                    self.issues_found += orphans
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ {model_path}: {orphans} سجل بدون {field_name} صالح'
                    ))
                    
                    if self.fix_mode:
                        Model.objects.filter(**{f'{field_name}__isnull': True}).delete()
                        self.issues_fixed += orphans
                        self.stdout.write(self.style.SUCCESS(f'    ✓ تم حذف {orphans} سجل'))
                        
            except Exception as e:
                if self.verbose:
                    self.stdout.write(f'  تخطي {model_path}: {e}')
        
        self.stdout.write(self.style.SUCCESS('  ✓ اكتمل فحص السجلات اليتيمة'))

    def check_accounting_balance(self):
        """فحص توازن القيود المحاسبية"""
        self.stdout.write(self.style.HTTP_INFO('\n⚖️ فحص توازن القيود المحاسبية:'))
        self.stdout.write('-' * 40)
        
        if self.specific_app and self.specific_app != 'accounting':
            self.stdout.write('  تخطي (ليس التطبيق المحدد)')
            return
        
        try:
            from accounting.models import JournalEntry, JournalEntryItem
            from django.db.models import Sum, Q
            
            # فحص القيود غير المتوازنة
            entries = JournalEntry.objects.annotate(
                total_debit=Sum('items__amount', filter=Q(items__type='debit')),
                total_credit=Sum('items__amount', filter=Q(items__type='credit'))
            ).exclude(
                total_debit=models.F('total_credit')
            ).filter(
                total_debit__isnull=False,
                total_credit__isnull=False
            )
            
            unbalanced = list(entries)
            
            if unbalanced:
                self.issues_found += len(unbalanced)
                for entry in unbalanced[:5]:  # عرض أول 5 فقط
                    diff = entry.total_debit - entry.total_credit
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ قيد {entry.number}: مدين={entry.total_debit}, دائن={entry.total_credit}, فرق={diff}'
                    ))
                
                if len(unbalanced) > 5:
                    self.stdout.write(f'  ... و {len(unbalanced) - 5} قيود أخرى')
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ جميع القيود متوازنة'))
                
        except Exception as e:
            self.stdout.write(f'  خطأ: {e}')

    def check_inventory_consistency(self):
        """فحص اتساق المخزون"""
        self.stdout.write(self.style.HTTP_INFO('\n📦 فحص اتساق المخزون:'))
        self.stdout.write('-' * 40)
        
        if self.specific_app and self.specific_app != 'inventory':
            self.stdout.write('  تخطي (ليس التطبيق المحدد)')
            return
        
        try:
            from inventory.models import Stock
            
            # فحص المخزون السالب
            negative_stock = Stock.objects.filter(quantity__lt=0)
            negative_count = negative_stock.count()
            
            if negative_count > 0:
                self.issues_found += negative_count
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {negative_count} سجل مخزون بكمية سالبة'
                ))
                
                if self.verbose:
                    for stock in negative_stock[:5]:
                        self.stdout.write(f'    - {stock.product}: {stock.quantity} في {stock.location}')
                
                if self.fix_mode:
                    # تصفير المخزون السالب (يجب مراجعة السبب يدوياً)
                    negative_stock.update(quantity=0)
                    self.issues_fixed += negative_count
                    self.stdout.write(self.style.SUCCESS(f'    ✓ تم تصفير {negative_count} سجل'))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ لا يوجد مخزون سالب'))
                
            # فحص السجلات المكررة
            from django.db.models import Count
            duplicates = Stock.objects.values('product', 'location').annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            dup_count = duplicates.count()
            if dup_count > 0:
                self.issues_found += dup_count
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {dup_count} حالة تكرار في سجلات المخزون'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ لا يوجد تكرار في سجلات المخزون'))
                
        except Exception as e:
            self.stdout.write(f'  خطأ: {e}')

    def check_invoice_totals(self):
        """فحص إجماليات الفواتير"""
        self.stdout.write(self.style.HTTP_INFO('\n🧾 فحص إجماليات الفواتير:'))
        self.stdout.write('-' * 40)
        
        if self.specific_app and self.specific_app != 'sales':
            self.stdout.write('  تخطي (ليس التطبيق المحدد)')
            return
        
        try:
            from sales.models import Invoice
            from django.db.models import Sum, F
            
            # فحص الفواتير بإجماليات غير صحيحة
            invoices = Invoice.objects.annotate(
                calculated_total=Sum(F('items__quantity') * F('items__price'))
            ).exclude(
                cached_total=F('calculated_total')
            ).filter(
                calculated_total__isnull=False
            )
            
            mismatch_count = invoices.count()
            
            if mismatch_count > 0:
                self.issues_found += mismatch_count
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {mismatch_count} فاتورة بإجمالي غير صحيح'
                ))
                
                if self.fix_mode:
                    for invoice in invoices:
                        invoice.cached_total = invoice.calculated_total
                        invoice.save(update_fields=['cached_total'])
                    self.issues_fixed += mismatch_count
                    self.stdout.write(self.style.SUCCESS(f'    ✓ تم تصحيح {mismatch_count} فاتورة'))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ جميع إجماليات الفواتير صحيحة'))
                
        except Exception as e:
            self.stdout.write(f'  خطأ: {e}')

    def check_payment_amounts(self):
        """فحص مبالغ الدفعات"""
        self.stdout.write(self.style.HTTP_INFO('\n💰 فحص مبالغ الدفعات:'))
        self.stdout.write('-' * 40)
        
        if self.specific_app and self.specific_app != 'sales':
            self.stdout.write('  تخطي (ليس التطبيق المحدد)')
            return
        
        try:
            from sales.models import Invoice, InvoicePayment
            from django.db.models import Sum
            
            # فحص الفواتير بمبلغ مدفوع أكبر من الإجمالي
            overpaid = Invoice.objects.filter(
                paid__gt=models.F('cached_total') - models.F('discount')
            ).exclude(is_deleted=True)
            
            overpaid_count = overpaid.count()
            
            if overpaid_count > 0:
                self.issues_found += overpaid_count
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {overpaid_count} فاتورة بمبلغ مدفوع أكبر من المستحق'
                ))
                
                if self.verbose:
                    for inv in overpaid[:5]:
                        self.stdout.write(f'    - {inv.number}: مدفوع={inv.paid}, إجمالي={inv.total}')
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ جميع مبالغ الدفعات صحيحة'))
                
            # فحص الدفعات السالبة
            negative_payments = InvoicePayment.objects.filter(amount__lt=0)
            neg_count = negative_payments.count()
            
            if neg_count > 0:
                self.issues_found += neg_count
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {neg_count} دفعة بمبلغ سالب'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ لا توجد دفعات سالبة'))
                
        except Exception as e:
            self.stdout.write(f'  خطأ: {e}')

    def check_duplicate_records(self):
        """فحص السجلات المكررة"""
        self.stdout.write(self.style.HTTP_INFO('\n🔄 فحص السجلات المكررة:'))
        self.stdout.write('-' * 40)
        
        checks = [
            ('accounting.Account', 'code'),
            ('inventory.Product', 'sku'),
            ('inventory.Product', 'barcode'),
            ('sales.Invoice', 'number'),
            ('purchases.PurchaseBill', 'number'),
            ('purchases.PurchaseOrder', 'number'),
            ('hr.Employee', 'employee_id'),
            ('hr.Employee', 'national_id'),
        ]
        
        for model_path, field in checks:
            if self.specific_app and not model_path.startswith(self.specific_app):
                continue
            
            try:
                Model = apps.get_model(model_path)
                from django.db.models import Count
                
                duplicates = Model.objects.values(field).annotate(
                    count=Count('id')
                ).filter(count__gt=1).exclude(**{f'{field}__isnull': True}).exclude(**{field: ''})
                
                dup_count = duplicates.count()
                
                if dup_count > 0:
                    self.issues_found += dup_count
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ {model_path}.{field}: {dup_count} قيمة مكررة'
                    ))
                    
            except Exception as e:
                if self.verbose:
                    self.stdout.write(f'  تخطي {model_path}: {e}')
        
        self.stdout.write(self.style.SUCCESS('  ✓ اكتمل فحص التكرارات'))

    def check_date_consistency(self):
        """فحص اتساق التواريخ"""
        self.stdout.write(self.style.HTTP_INFO('\n📅 فحص اتساق التواريخ:'))
        self.stdout.write('-' * 40)
        
        from datetime import date, timedelta
        
        future_date = date.today() + timedelta(days=365)
        past_date = date(2000, 1, 1)
        
        checks = [
            ('sales.Invoice', 'date'),
            ('purchases.PurchaseBill', 'date'),
            ('accounting.JournalEntry', 'date'),
            ('hr.Employee', 'hire_date'),
        ]
        
        for model_path, field in checks:
            if self.specific_app and not model_path.startswith(self.specific_app):
                continue
            
            try:
                Model = apps.get_model(model_path)
                
                # تواريخ مستقبلية غريبة
                future_records = Model.objects.filter(**{f'{field}__gt': future_date})
                future_count = future_records.count()
                
                if future_count > 0:
                    self.issues_found += future_count
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ {model_path}: {future_count} سجل بتاريخ مستقبلي بعيد'
                    ))
                
                # تواريخ قديمة جداً
                old_records = Model.objects.filter(**{f'{field}__lt': past_date})
                old_count = old_records.count()
                
                if old_count > 0:
                    self.issues_found += old_count
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ {model_path}: {old_count} سجل بتاريخ قديم جداً'
                    ))
                    
            except Exception as e:
                if self.verbose:
                    self.stdout.write(f'  تخطي {model_path}: {e}')
        
        self.stdout.write(self.style.SUCCESS('  ✓ اكتمل فحص التواريخ'))
