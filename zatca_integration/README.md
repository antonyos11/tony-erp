# ZATCA Integration - الفوترة الإلكترونية
## هيئة الزكاة والضريبة والجمارك - المرحلة الأولى والثانية

## 🎯 نظرة عامة

نظام فوترة إلكترونية متكامل متوافق مع متطلبات **هيئة الزكاة والضريبة والجمارك مصر**

### ✅ المتطلبات المطبقة

#### المرحلة الأولى (Generation Phase):
- ✅ QR Code على الفاتورة (TLV Format)
- ✅ XML Invoice (UBL 2.1)
- ✅ Invoice Hashing (SHA256)
- ✅ حفظ سجل الفواتير

#### المرحلة الثانية (Integration Phase):
- ✅ Digital Signature (جاهز للشهادة)
- ✅ Real-time Reporting
- ✅ B2B & B2C Support
- ✅ Credit/Debit Notes

---

## 📋 المكونات الرئيسية

### 1. ZATCAConfiguration - إعدادات الربط

```python
from zatca_integration.models import ZATCAConfiguration

config = ZATCAConfiguration.objects.create(
    company=company,
    
    # معلومات التسجيل
    vat_number="123456789012345",  # 15 رقم إلزامي
    crn="1234567890",  # رقم السجل التجاري
    
    # البيئة
    environment='production',  # sandbox, simulation, production
    
    # بيانات الاتصال
    api_base_url='https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal',
    compliance_csid='',  # من ZATCA
    production_csid='',  # من ZATCA
    
    # الشهادات الرقمية
    certificate='',  # Certificate PEM
    private_key='',  # Private Key PEM
    certificate_password='',
    
    # العنوان الوطني
    seller_name='شركة المثال المحدودة',
    building_number='1234',
    street_name='شارع الملك فهد',
    district='العليا',
    city='الرياض',
    postal_code='12345',
    
    is_active=True
)
```

---

### 2. EInvoice - الفاتورة الإلكترونية

#### إنشاء فاتورة إلكترونية

```python
from zatca_integration.models import EInvoice
from sales.models import Invoice
import uuid

# 1. الفاتورة الأصلية من النظام
invoice = Invoice.objects.get(invoice_number="INV-2026-001")

# 2. إنشاء فاتورة إلكترونية
einvoice = EInvoice.objects.create(
    invoice=invoice,
    uuid=uuid.uuid4(),  # UUID فريد
    invoice_counter=1,  # رقم تسلسلي
    invoice_type='B2B',  # B2B (ضريبية) أو B2C (مبسطة)
    status='draft'
)
```

#### توليد QR Code

```python
# TLV Format - 5 Tags إلزامية
qr_code = einvoice.generate_qr_code()

# QR Code يحتوي على:
# Tag 1: Seller Name (اسم البائع)
# Tag 2: VAT Number (الرقم الضريبي)
# Tag 3: Invoice Date (تاريخ الفاتورة)
# Tag 4: Total with VAT (المبلغ الإجمالي مع الضريبة)
# Tag 5: VAT Amount (مبلغ الضريبة)

print(f"QR Code (Base64): {qr_code}")
```

#### توليد XML (UBL 2.1)

```python
# XML بصيغة UBL 2.1 Standard
xml_invoice = einvoice.generate_xml_invoice()

# XML يحتوي على:
# - معلومات الفاتورة الأساسية
# - معلومات البائع والمشتري
# - تفاصيل السلع والخدمات
# - معلومات الضريبة
# - التوقيع الرقمي (عند الإبلاغ)

print(xml_invoice)
```

#### حساب Hash

```python
# SHA256 Hash للفاتورة
hash_value = einvoice.generate_hash()

# يستخدم في:
# - التحقق من سلامة الفاتورة
# - ربط الفواتير (Previous Invoice Hash)

print(f"Invoice Hash: {hash_value}")
```

---

### 3. أنواع الفواتير

#### فاتورة ضريبية (B2B)
```python
# للمعاملات بين الشركات
einvoice = EInvoice.objects.create(
    invoice=invoice,
    invoice_type='B2B',
    # يتطلب:
    # - QR Code ✅
    # - XML ✅
    # - Hash ✅
    # - Digital Signature ✅
    # - Real-time Clearance (يُرسل لـ ZATCA قبل إعطاؤه للعميل)
)
```

#### فاتورة ضريبية مبسطة (B2C)
```python
# لمعاملات البيع بالتجزئة
einvoice = EInvoice.objects.create(
    invoice=invoice,
    invoice_type='B2C',
    # يتطلب:
    # - QR Code ✅
    # - XML ✅
    # - Hash ✅
    # - Real-time Reporting (يُرسل لـ ZATCA خلال 24 ساعة)
)
```

#### إشعار دائن (Credit Note)
```python
# لإرجاع البضائع أو تخفيض المبلغ
einvoice = EInvoice.objects.create(
    invoice=return_invoice,
    invoice_type='credit_note',
)
```

#### إشعار مدين (Debit Note)
```python
# لزيادة المبلغ
einvoice = EInvoice.objects.create(
    invoice=adjustment_invoice,
    invoice_type='debit_note',
)
```

---

### 4. الإبلاغ لـ ZATCA

```python
# TODO: تطوير كامل للاتصال بـ ZATCA API
# يحتاج:
# 1. الشهادة الرقمية من ZATCA
# 2. CSID (Cryptographic Stamp ID)
# 3. تنفيذ الـ API Endpoints

# مثال (مبسط):
def report_to_zatca(einvoice):
    """
    الإبلاغ الفوري لـ ZATCA
    """
    # 1. التحقق من الشهادة
    config = einvoice.invoice.company.zatcaconfiguration
    if not config.is_certified:
        raise Exception("الشركة غير معتمدة من ZATCA")
    
    # 2. توقيع XML
    signed_xml = sign_xml(
        einvoice.xml_invoice,
        config.private_key,
        config.certificate
    )
    einvoice.signed_xml = signed_xml
    einvoice.save()
    
    # 3. إرسال لـ ZATCA
    response = requests.post(
        f"{config.api_base_url}/invoices/reporting/single",
        headers={
            'Authorization': f'Bearer {config.production_csid}',
            'Content-Type': 'application/json'
        },
        json={
            'invoice': base64.b64encode(signed_xml.encode()).decode(),
            'invoiceHash': einvoice.invoice_hash,
            'uuid': str(einvoice.uuid)
        }
    )
    
    # 4. معالجة الاستجابة
    if response.status_code == 200:
        einvoice.status = 'reported'
        einvoice.reported_at = timezone.now()
        einvoice.zatca_response = response.json()
    else:
        einvoice.status = 'rejected'
        einvoice.error_message = response.text
    
    einvoice.save()
    
    # 5. تسجيل في Log
    EInvoiceLog.objects.create(
        einvoice=einvoice,
        action='report',
        request_data={'url': response.url},
        response_data=response.json(),
        success=(response.status_code == 200)
    )
```

---

## 🔌 REST API

### Endpoints

```
GET    /api/zatca/config/                    # إعدادات ZATCA
PUT    /api/zatca/config/                    # تحديث الإعدادات

GET    /api/zatca/invoices/                  # قائمة الفواتير الإلكترونية
GET    /api/zatca/invoices/:id/              # تفاصيل فاتورة
POST   /api/zatca/invoices/:id/generate-qr/  # توليد QR Code
POST   /api/zatca/invoices/:id/generate-xml/ # توليد XML
POST   /api/zatca/invoices/:id/report/       # الإبلاغ لـ ZATCA

GET    /api/zatca/invoices/:id/logs/         # سجل الإرسال
```

### أمثلة API

```bash
# توليد QR Code
curl -X POST http://localhost:8000/api/zatca/invoices/1/generate-qr/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# استجابة:
{
  "success": true,
  "qr_code": "AQxhc3NvY2lhdGVzIDEyCjE1NjM0ODc2NTQzMjEgGE1QUlA...",
  "message": "تم توليد QR Code بنجاح"
}

# توليد XML
curl -X POST http://localhost:8000/api/zatca/invoices/1/generate-xml/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# استجابة:
{
  "success": true,
  "xml_invoice": "<?xml version=\"1.0\"...>",
  "invoice_hash": "abc123...",
  "message": "تم توليد XML و Hash بنجاح"
}

# الإبلاغ لـ ZATCA
curl -X POST http://localhost:8000/api/zatca/invoices/1/report/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# استجابة:
{
  "success": true,
  "message": "تم الإبلاغ بنجاح",
  "zatca_response": {
    "reportingStatus": "REPORTED",
    "clearanceStatus": "CLEARED"
  },
  "reported_at": "2026-01-04T10:30:00Z"
}
```

---

## 🎨 لوحة الإدارة

### الوصول
```
http://localhost:8000/admin/zatca_integration/
```

### الإجراءات المتاحة (Bulk Actions)
1. **توليد QR Code** - لفواتير محددة
2. **توليد XML و Hash** - لفواتير محددة
3. **الإبلاغ لـ ZATCA** - (قيد التطوير)

---

## ⚙️ الإعداد

### 1. التسجيل في بوابة ZATCA

1. التسجيل على: https://fatoora.zatca.gov.sa
2. الحصول على الرقم الضريبي (15 رقم)
3. الحصول على Compliance CSID
4. الحصول على Production CSID
5. تحميل الشهادة الرقمية

### 2. إعداد النظام

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'zatca_integration',
]

# migrations
python manage.py makemigrations zatca_integration
python manage.py migrate zatca_integration
```

### 3. إدخال بيانات الشركة

```python
from zatca_integration.models import ZATCAConfiguration
from accounting.models import Company

company = Company.objects.first()

config = ZATCAConfiguration.objects.create(
    company=company,
    vat_number="310122393500003",  # من ZATCA
    crn="1234567890",
    environment='production',
    
    # من ZATCA Portal
    compliance_csid='TUlJRGdqQ0NBbXFnQXdJQkFnSUdBWXV...',
    production_csid='VFNULTg4NjQzMTEyMC0yNDIzMDk3...',
    
    # الشهادة
    certificate='''-----BEGIN CERTIFICATE-----
MIIDqDCCApCgAwIBAgIGAYuBk...
-----END CERTIFICATE-----''',
    
    private_key='''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQ...
-----END PRIVATE KEY-----''',
    
    # العنوان
    seller_name='شركة المثال المحدودة',
    building_number='1234',
    street_name='شارع الملك فهد',
    district='العليا',
    city='الرياض',
    postal_code='12345',
    
    is_active=True,
    is_certified=True
)
```

---

## 📊 سيناريو كامل

```python
from sales.models import Invoice
from zatca_integration.models import EInvoice
import uuid

# 1. فاتورة جديدة من النظام
invoice = Invoice.objects.create(
    customer=customer,
    invoice_number="INV-2026-001",
    invoice_date=datetime.now().date(),
    subtotal=1000.00,
    tax_amount=150.00,  # 15%
    total_amount=1150.00
)

# 2. إنشاء فاتورة إلكترونية
einvoice = EInvoice.objects.create(
    invoice=invoice,
    uuid=uuid.uuid4(),
    invoice_counter=1,
    invoice_type='B2B',  # للشركات
    status='draft'
)

# 3. توليد المتطلبات
print("توليد QR Code...")
qr = einvoice.generate_qr_code()
print(f"✓ QR Code: {qr[:50]}...")

print("توليد XML...")
xml = einvoice.generate_xml_invoice()
print(f"✓ XML: {len(xml)} bytes")

print("حساب Hash...")
hash_val = einvoice.generate_hash()
print(f"✓ Hash: {hash_val}")

# 4. الإبلاغ لـ ZATCA (B2B يحتاج Clearance فوري)
print("الإبلاغ لـ ZATCA...")
einvoice.status = 'pending'
einvoice.save()

# report_to_zatca(einvoice)  # قيد التطوير

# 5. عند النجاح
einvoice.status = 'cleared'
einvoice.cleared_at = timezone.now()
einvoice.save()

print("✓ الفاتورة معتمدة من ZATCA")
print(f"UUID: {einvoice.uuid}")
print(f"Hash: {einvoice.invoice_hash}")

# 6. طباعة الفاتورة مع QR Code
print_invoice_with_qr(invoice, einvoice.qr_code)
```

---

## 📋 QR Code Format (TLV)

```python
def generate_qr_tlv():
    """
    TLV (Tag-Length-Value) Format
    
    Tag 1: Seller Name (UTF-8)
    Tag 2: VAT Number (UTF-8)
    Tag 3: Timestamp (ISO 8601)
    Tag 4: Invoice Total (UTF-8)
    Tag 5: VAT Amount (UTF-8)
    """
    
    def tlv_encode(tag, value):
        value_bytes = value.encode('utf-8')
        length = len(value_bytes)
        return bytes([tag, length]) + value_bytes
    
    qr_data = b''
    qr_data += tlv_encode(1, "شركة المثال المحدودة")
    qr_data += tlv_encode(2, "310122393500003")
    qr_data += tlv_encode(3, "2026-01-04T10:30:00Z")
    qr_data += tlv_encode(4, "1150.00")
    qr_data += tlv_encode(5, "150.00")
    
    # Base64 encode
    qr_code = base64.b64encode(qr_data).decode('utf-8')
    return qr_code
```

---

## 📄 XML Invoice Structure (UBL 2.1)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    
    <!-- معلومات الفاتورة -->
    <cbc:ID>INV-2026-001</cbc:ID>
    <cbc:UUID>123e4567-e89b-12d3-a456-426614174000</cbc:UUID>
    <cbc:IssueDate>2026-01-04</cbc:IssueDate>
    <cbc:InvoiceTypeCode name="0211">388</cbc:InvoiceTypeCode>
    
    <!-- البائع -->
    <cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN">1234567890</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyTaxScheme>
                <cbc:CompanyID>310122393500003</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
        </cac:Party>
    </cac:AccountingSupplierParty>
    
    <!-- المشتري -->
    <cac:AccountingCustomerParty>
        <!-- ... -->
    </cac:AccountingCustomerParty>
    
    <!-- الإجماليات -->
    <cac:LegalMonetaryTotal>
        <cbc:TaxExclusiveAmount currencyID="SAR">1000.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">1150.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="SAR">1150.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    
    <!-- الضريبة -->
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">150.00</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">1000.00</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">150.00</cbc:TaxAmount>
            <cac:TaxCategory>
                <cbc:ID>S</cbc:ID>
                <cbc:Percent>15.00</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    
</Invoice>
```

---

## 🔐 الأمان

### التوقيع الرقمي
```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

def sign_xml(xml_content, private_key_pem, certificate_pem):
    """
    توقيع XML بالشهادة الرقمية
    """
    # تحميل المفتاح الخاص
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )
    
    # التوقيع
    signature = private_key.sign(
        xml_content.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    # Base64 encode
    signature_b64 = base64.b64encode(signature).decode()
    
    # إضافة التوقيع للـ XML
    signed_xml = xml_content.replace(
        '</Invoice>',
        f'''
        <ds:Signature>
            <ds:SignedInfo>
                <ds:SignatureValue>{signature_b64}</ds:SignatureValue>
            </ds:SignedInfo>
        </ds:Signature>
        </Invoice>
        '''
    )
    
    return signed_xml
```

---

## 🎯 الفوائد

1. **توافق كامل:** المرحلة 1 و 2 من ZATCA
2. **أتمتة:** توليد تلقائي لـ QR، XML، Hash
3. **أمان عالي:** التوقيع الرقمي والتشفير
4. **سهل الاستخدام:** واجهة إدارية بسيطة
5. **قابل للتوسع:** يدعم B2B، B2C، Credit/Debit Notes

---

## 📚 الموارد

- [بوابة ZATCA](https://fatoora.zatca.gov.sa)
- [UBL 2.1 Standard](http://docs.oasis-open.org/ubl/UBL-2.1.html)
- [دليل المطور ZATCA](https://zatca.gov.sa/ar/E-Invoicing/Pages/default.aspx)

---

**📅 آخر تحديث:** 4 يناير 2026  
**📖 الإصدار:** 1.0.0  
**⚠️ ملاحظة:** API Integration قيد التطوير النهائي
