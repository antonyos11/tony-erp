"""
عرض رقم الفاتورة التالي
يستخدم لمعرفة الرقم الذي سيُستخدم في الفاتورة القادمة
"""
from django.utils import timezone


def get_next_invoice_number():
    """
    احصل على رقم الفاتورة التالي الذي سيتم توليده
    بدون إنشاء فاتورة فعلية
    """
    now = timezone.now()
    prefix = f"INV-{now.strftime('%Y%m')}"
    
    # الحصول على الرقم التسلسلي التالي بدون زيادة العداد
    try:
        from sales.models import Invoice
        # البحث عن آخر فاتورة في هذا الشهر
        last_invoice = Invoice.objects.filter(
            number__startswith=prefix
        ).order_by('-number').first()
        
        if last_invoice:
            # استخراج الرقم التسلسلي من آخر فاتورة
            try:
                last_seq = int(last_invoice.number.split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1
            
        next_number = f"{prefix}-{str(next_seq).zfill(6)}"
        return next_number
        
    except Exception as e:
        return f"{prefix}-000001"


def get_next_tax_invoice_number(invoice_type='sales'):
    """
    احصل على رقم الفاتورة الضريبية التالي
    
    Args:
        invoice_type: نوع الفاتورة (sales, purchase, sales_return, purchase_return)
    """
    from taxes.models import TaxInvoice
    
    prefix = {
        'sales': 'TAX-S',
        'sales_return': 'TAX-SR',
        'purchase': 'TAX-P',
        'purchase_return': 'TAX-PR',
    }.get(invoice_type, 'TAX')
    
    year_month = timezone.now().strftime('%Y%m')
    last = TaxInvoice.objects.filter(
        invoice_number__startswith=f'{prefix}-{year_month}'
    ).order_by('-id').first()
    
    if last:
        try:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        except:
            seq = 1
    else:
        seq = 1
    
    next_number = f'{prefix}-{year_month}-{seq:05d}'
    return next_number


def preview_invoice_numbers():
    """
    عرض ملخص بأرقام الفواتير التالية لجميع الأنواع
    """
    return {
        'sales_invoice': get_next_invoice_number(),
        'tax_sales': get_next_tax_invoice_number('sales'),
        'tax_sales_return': get_next_tax_invoice_number('sales_return'),
        'tax_purchase': get_next_tax_invoice_number('purchase'),
        'tax_purchase_return': get_next_tax_invoice_number('purchase_return'),
    }
