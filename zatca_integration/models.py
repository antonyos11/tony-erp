"""
ZATCA E-Invoicing Phase 2 Implementation
تطبيق الفوترة الإلكترونية - هيئة الزكاة والضريبة والجمارك - المرحلة الثانية

المتطلبات:
- QR Code on invoice
- XML invoice format (UBL 2.1)
- Digital signature
- Invoice hashing
- Real-time reporting to ZATCA
"""

from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal
import hashlib
import base64
from datetime import datetime


class ZATCAConfiguration(models.Model):
    """إعدادات الربط مع هيئة الزكاة"""
    
    ENVIRONMENT_CHOICES = [
        ('sandbox', 'بيئة تجريبية'),
        ('simulation', 'بيئة محاكاة'),
        ('production', 'بيئة إنتاج'),
    ]
    
    company = models.OneToOneField('core.Company', on_delete=models.CASCADE, verbose_name='الشركة')
    
    # معلومات التسجيل
    vat_number = models.CharField(
        'الرقم الضريبي',
        max_length=15,
        validators=[RegexValidator(r'^\d{15}$', 'يجب أن يكون 15 رقم')]
    )
    crn = models.CharField('رقم السجل التجاري', max_length=50)
    
    # بيئة العمل
    environment = models.CharField('البيئة', max_length=20, choices=ENVIRONMENT_CHOICES, default='sandbox')
    
    # بيانات الاتصال بـ ZATCA
    api_base_url = models.URLField('API Base URL', default='https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal')
    compliance_csid = models.TextField('Compliance CSID', blank=True)
    production_csid = models.TextField('Production CSID', blank=True)
    
    # الشهادات الرقمية
    certificate = models.TextField('الشهادة الرقمية (Certificate)', blank=True)
    private_key = models.TextField('المفتاح الخاص (Private Key)', blank=True)
    certificate_password = models.CharField('كلمة مرور الشهادة', max_length=255, blank=True)
    
    # الحالة
    is_active = models.BooleanField('نشط', default=False)
    is_certified = models.BooleanField('معتمد من ZATCA', default=False)
    certification_date = models.DateTimeField('تاريخ الاعتماد', null=True, blank=True)
    
    # معلومات إضافية
    seller_name = models.CharField('اسم البائع', max_length=200, blank=True)
    building_number = models.CharField('رقم المبنى', max_length=10, blank=True)
    street_name = models.CharField('اسم الشارع', max_length=200, blank=True)
    district = models.CharField('الحي', max_length=100, blank=True)
    city = models.CharField('المدينة', max_length=100, blank=True)
    postal_code = models.CharField('الرمز البريدي', max_length=10, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'إعدادات ZATCA'
        verbose_name_plural = 'إعدادات ZATCA'
    
    def __str__(self):
        return f"ZATCA Config - {self.company.name}"


class EInvoice(models.Model):
    """الفاتورة الإلكترونية"""
    
    INVOICE_TYPE_CHOICES = [
        ('B2B', 'فاتورة ضريبية - B2B'),
        ('B2C', 'فاتورة ضريبية مبسطة - B2C'),
        ('credit_note', 'إشعار دائن'),
        ('debit_note', 'إشعار مدين'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('pending', 'قيد الإرسال'),
        ('reported', 'تم الإبلاغ'),
        ('cleared', 'تم التخليص'),
        ('rejected', 'مرفوض'),
    ]
    
    # ربط مع الفاتورة الأصلية
    invoice = models.OneToOneField('sales.Invoice', on_delete=models.CASCADE, verbose_name='الفاتورة')
    
    # معلومات ZATCA
    uuid = models.UUIDField('UUID', unique=True)
    invoice_counter = models.IntegerField('رقم تسلسلي')
    invoice_type = models.CharField('نوع الفاتورة', max_length=20, choices=INVOICE_TYPE_CHOICES)
    
    # التجزئة والتشفير
    invoice_hash = models.CharField('Hash', max_length=255, blank=True)
    previous_invoice_hash = models.CharField('Previous Hash', max_length=255, blank=True)
    
    # QR Code
    qr_code = models.TextField('QR Code', blank=True)
    qr_code_image = models.ImageField('صورة QR Code', upload_to='zatca/qr/', blank=True)
    
    # XML
    xml_invoice = models.TextField('XML Invoice', blank=True)
    signed_xml = models.TextField('Signed XML', blank=True)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # استجابة ZATCA
    zatca_response = models.JSONField('ZATCA Response', default=dict, blank=True)
    reported_at = models.DateTimeField('تاريخ الإبلاغ', null=True, blank=True)
    cleared_at = models.DateTimeField('تاريخ التخليص', null=True, blank=True)
    
    # الأخطاء
    error_message = models.TextField('رسالة الخطأ', blank=True)
    validation_errors = models.JSONField('أخطاء التحقق', default=list, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'فاتورة إلكترونية'
        verbose_name_plural = 'فواتير إلكترونية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"E-Invoice {self.invoice.invoice_number}"
    
    def generate_qr_code(self):
        """توليد QR Code"""
        # TLV Format (Tag-Length-Value)
        # Tag 1: Seller Name
        # Tag 2: VAT Number
        # Tag 3: Invoice Date
        # Tag 4: Total with VAT
        # Tag 5: VAT Amount
        
        seller_name = self.invoice.company.name
        vat_number = self.invoice.company.tax_number
        invoice_date = self.invoice.invoice_date.isoformat()
        total = str(self.invoice.total_amount)
        vat = str(self.invoice.tax_amount)
        
        def tlv_encode(tag, value):
            """Encode value in TLV format"""
            value_bytes = value.encode('utf-8')
            length = len(value_bytes)
            return bytes([tag, length]) + value_bytes
        
        qr_data = b''
        qr_data += tlv_encode(1, seller_name)
        qr_data += tlv_encode(2, vat_number)
        qr_data += tlv_encode(3, invoice_date)
        qr_data += tlv_encode(4, total)
        qr_data += tlv_encode(5, vat)
        
        # Base64 encode
        self.qr_code = base64.b64encode(qr_data).decode('utf-8')
        self.save()
        
        return self.qr_code
    
    def generate_hash(self):
        """توليد Hash للفاتورة"""
        # استخدام SHA256
        data = f"{self.uuid}{self.invoice.invoice_number}{self.invoice.invoice_date}{self.invoice.total_amount}"
        hash_object = hashlib.sha256(data.encode('utf-8'))
        self.invoice_hash = hash_object.hexdigest()
        self.save()
        
        return self.invoice_hash
    
    def generate_xml_invoice(self):
        """توليد XML بصيغة UBL 2.1"""
        # هذا مثال مبسط - يحتاج تطوير كامل لـ UBL 2.1
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:ID>{self.invoice.invoice_number}</cbc:ID>
    <cbc:UUID>{self.uuid}</cbc:UUID>
    <cbc:IssueDate>{self.invoice.invoice_date}</cbc:IssueDate>
    <cbc:InvoiceTypeCode name="{self.invoice_type}">{self.invoice_type}</cbc:InvoiceTypeCode>
    
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN">{self.invoice.company.registration_number}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>{self.invoice.company.tax_number}</cbc:CompanyID>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingSupplierParty>
    
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="SAR">{self.invoice.subtotal}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">{self.invoice.total_amount}</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="SAR">{self.invoice.total_amount}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">{self.invoice.tax_amount}</cbc:TaxAmount>
    </cac:TaxTotal>
</Invoice>"""
        
        self.xml_invoice = xml
        self.save()
        
        return xml


class EInvoiceLog(models.Model):
    """سجل إرسال الفواتير لـ ZATCA"""
    
    ACTION_CHOICES = [
        ('compliance_check', 'فحص التوافق'),
        ('report', 'إبلاغ'),
        ('clearance', 'تخليص'),
    ]
    
    einvoice = models.ForeignKey(EInvoice, on_delete=models.CASCADE, related_name='logs')
    
    action = models.CharField('الإجراء', max_length=20, choices=ACTION_CHOICES)
    request_data = models.JSONField('بيانات الطلب', default=dict)
    response_data = models.JSONField('بيانات الاستجابة', default=dict)
    
    success = models.BooleanField('نجح', default=False)
    error_message = models.TextField('رسالة الخطأ', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'سجل فاتورة إلكترونية'
        verbose_name_plural = 'سجلات الفواتير الإلكترونية'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.einvoice.invoice.invoice_number}"
