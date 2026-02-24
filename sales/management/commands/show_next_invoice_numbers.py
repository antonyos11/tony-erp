"""
Django management command لعرض أرقام الفواتير التالية
الاستخدام: python manage.py show_next_invoice_numbers
"""
from django.core.management.base import BaseCommand
from sales.next_invoice_number import preview_invoice_numbers


class Command(BaseCommand):
    help = 'عرض أرقام الفواتير التالية التي سيتم توليدها'

    def handle(self, *args, **options):
        """تنفيذ الأمر"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('أرقام الفواتير التالية'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
        
        try:
            numbers = preview_invoice_numbers()
            
            # عرض الأرقام بتنسيق جميل
            self.stdout.write(self.style.WARNING('فواتير المبيعات:'))
            self.stdout.write(f'  → الرقم التالي: {self.style.SUCCESS(numbers["sales_invoice"])}\n')
            
            self.stdout.write(self.style.WARNING('الفواتير الضريبية - مبيعات:'))
            self.stdout.write(f'  → الرقم التالي: {self.style.SUCCESS(numbers["tax_sales"])}\n')
            
            self.stdout.write(self.style.WARNING('الفواتير الضريبية - مرتجع مبيعات:'))
            self.stdout.write(f'  → الرقم التالي: {self.style.SUCCESS(numbers["tax_sales_return"])}\n')
            
            self.stdout.write(self.style.WARNING('الفواتير الضريبية - مشتريات:'))
            self.stdout.write(f'  → الرقم التالي: {self.style.SUCCESS(numbers["tax_purchase"])}\n')
            
            self.stdout.write(self.style.WARNING('الفواتير الضريبية - مرتجع مشتريات:'))
            self.stdout.write(f'  → الرقم التالي: {self.style.SUCCESS(numbers["tax_purchase_return"])}\n')
            
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('✓ تم عرض جميع الأرقام بنجاح'))
            self.stdout.write(self.style.WARNING('\nملاحظة: هذه الأرقام تقديرية وقد تتغير عند إنشاء فواتير جديدة\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ حدث خطأ: {str(e)}\n'))
            raise
