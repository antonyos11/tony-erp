from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.apps import apps


class Command(BaseCommand):
    help = 'تصفير جميع البيانات في النظام للبدء من جديد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='تأكيد الحذف بدون سؤال',
        )
        parser.add_argument(
            '--keep-users',
            action='store_true',
            help='الاحتفاظ بالمستخدمين وبيانات تسجيل الدخول',
        )
        parser.add_argument(
            '--keep-company',
            action='store_true',
            help='الاحتفاظ ببيانات الشركة',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('=' * 60))
            self.stdout.write(self.style.WARNING('⚠️  تحذير: سيتم حذف جميع البيانات في النظام!'))
            self.stdout.write(self.style.WARNING('=' * 60))
            self.stdout.write('')
            self.stdout.write('سيتم حذف:')
            self.stdout.write('  - جميع المنتجات والمخزون')
            self.stdout.write('  - جميع فواتير المبيعات والمشتريات')
            self.stdout.write('  - جميع العملاء والموردين')
            self.stdout.write('  - جميع الحركات المالية')
            self.stdout.write('  - جميع البيانات الأخرى')
            self.stdout.write('')
            
            confirm = input('هل أنت متأكد؟ اكتب "نعم" للتأكيد: ')
            if confirm != 'نعم':
                self.stdout.write(self.style.ERROR('تم إلغاء العملية'))
                return

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🚀 بدء تصفير النظام...'))
        self.stdout.write('')

        # قائمة الجداول التي لا يجب حذفها
        excluded_tables = [
            'django_migrations',
            'django_content_type',
            'auth_permission',
            'django_session',
        ]
        
        if options['keep_users']:
            excluded_tables.extend([
                'auth_user',
                'auth_group',
                'auth_user_groups',
                'auth_user_user_permissions',
                'accounts_customuser',
                'users_customuser',
            ])
            self.stdout.write('  ℹ️  الاحتفاظ بالمستخدمين')
        
        if options['keep_company']:
            excluded_tables.extend([
                'core_company',
                'core_companysettings',
            ])
            self.stdout.write('  ℹ️  الاحتفاظ ببيانات الشركة')

        # الحصول على جميع الموديلات
        deleted_count = 0
        
        # ترتيب الحذف حسب الأولوية (البنود أولاً ثم الرئيسية)
        priority_apps = [
            # بنود الفواتير والمستندات أولاً
            ('sales', ['InvoiceItem', 'InvoicePayment', 'Invoice', 'Quotation', 'QuotationItem']),
            ('purchases', ['PurchaseItem', 'PurchaseOrderItem', 'Purchase', 'PurchaseOrder']),
            ('inventory', ['StockTransferItem', 'StockCountItem', 'ReceivingItem', 'IssueItem', 
                          'RequisitionItem', 'StockBatch', 'Stock', 'StockTransfer', 
                          'StockCount', 'Receiving', 'Issue', 'Requisition', 'Product', 'Category', 'Location']),
            ('pos', ['POSOrderItem', 'POSOrder', 'POSSession']),
            ('accounting', ['JournalEntryLine', 'JournalEntry', 'AccountTransaction']),
            ('partners', ['Customer', 'Supplier']),
            ('crm', ['Lead', 'Opportunity', 'Contact']),
        ]

        with transaction.atomic():
            # حذف حسب الأولوية أولاً
            for app_label, models in priority_apps:
                for model_name in models:
                    try:
                        model = apps.get_model(app_label, model_name)
                        count = model.objects.count()
                        if count > 0:
                            model.objects.all().delete()
                            self.stdout.write(f'  ✅ {app_label}.{model_name}: حذف {count} سجل')
                            deleted_count += count
                    except LookupError:
                        pass
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ {app_label}.{model_name}: {e}'))

            # حذف باقي الموديلات
            all_models = apps.get_models()
            
            for model in all_models:
                table_name = model._meta.db_table
                app_label = model._meta.app_label
                model_name = model.__name__
                
                # تخطي الجداول المستثناة
                if table_name in excluded_tables:
                    continue
                
                # تخطي جداول Django الأساسية
                if app_label in ['admin', 'contenttypes', 'sessions']:
                    continue
                
                # تخطي إذا كانت محذوفة بالفعل
                try:
                    count = model.objects.count()
                    if count > 0:
                        model.objects.all().delete()
                        self.stdout.write(f'  ✅ {app_label}.{model_name}: حذف {count} سجل')
                        deleted_count += count
                except Exception as e:
                    # تجاهل الأخطاء للجداول غير الموجودة
                    pass

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✨ تم تصفير النظام بنجاح!'))
        self.stdout.write(self.style.SUCCESS(f'   إجمالي السجلات المحذوفة: {deleted_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('يمكنك الآن البدء في استخدام النظام من جديد.')
        self.stdout.write('لإنشاء مخازن جديدة: python3 manage.py create_sample_warehouses')
