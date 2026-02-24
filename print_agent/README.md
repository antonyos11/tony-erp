# 🖨️ Tony ERP Print Agent - دليل الاستخدام

## نظرة عامة

**Print Agent** هو خدمة محلية تعمل على كمبيوترات الفروع لتمكين الطباعة المباشرة من متصفح الإنترنت إلى الطابعات المحلية (العادية والحرارية).

---

## ✨ المميزات

- ✅ طباعة مباشرة بدون تدخل المستخدم
- ✅ دعم الطابعات الحرارية (ESC/POS)
- ✅ دعم الطابعات العادية (Laser/Inkjet)
- ✅ طباعة HTML, PDF, Text, Raw Commands
- ✅ كشف الطابعات تلقائيًا
- ✅ اتصال آمن عبر WebSocket
- ✅ يعمل على Windows و Linux
- ✅ سهل التثبيت والاستخدام

---

## 📋 المتطلبات

### Windows
- Windows 10/11 أو Windows Server 2016+
- Python 3.8 أو أحدث
- طابعة مثبتة على النظام

### Linux
- Ubuntu 20.04+ أو أي توزيعة حديثة
- Python 3.8+
- CUPS (نظام الطباعة)

---

## 🚀 التثبيت

### على Windows

1. **تحميل المجلد:**
   ```cmd
   نسخ مجلد print_agent إلى: C:\TonyERP\print_agent
   ```

2. **تشغيل التثبيت التلقائي:**
   ```cmd
   cd C:\TonyERP\print_agent
   install_windows.bat
   ```

3. **تشغيل الخدمة:**
   - افتح `start_agent.bat`
   - أو استخدم الاختصار على سطح المكتب

### على Linux

1. **تحميل المجلد:**
   ```bash
   sudo mkdir -p /opt/tony-erp
   sudo cp -r print_agent /opt/tony-erp/
   cd /opt/tony-erp/print_agent
   ```

2. **تشغيل التثبيت:**
   ```bash
   chmod +x install_linux.sh
   ./install_linux.sh
   ```

3. **تشغيل الخدمة:**
   ```bash
   sudo systemctl start tony-print-agent
   ```

---

## 🧪 اختبار النظام

1. **تأكد من تشغيل الخدمة**
   
2. **افتح ملف الاختبار:**
   - افتح `test_print.html` في المتصفح
   - أو افتح: `http://localhost/print_agent/test_print.html`

3. **جرب الطباعة:**
   - اضغط "طباعة اختبارية"
   - يجب أن تطبع الطابعة صفحة اختبار

---

## 💻 استخدام في نظام Django

### 1. إضافة JavaScript للصفحات

أضف هذا الكود في `base.html` أو قالب الفواتير:

```html
<script>
// الاتصال بـ Print Agent
let printWS = null;

function connectPrintAgent() {
    printWS = new WebSocket('ws://localhost:9876');
    
    printWS.onopen = () => {
        console.log('✓ متصل بخدمة الطباعة');
    };
    
    printWS.onerror = () => {
        console.error('✗ خطأ في الاتصال بخدمة الطباعة');
    };
    
    printWS.onclose = () => {
        console.log('✗ انقطع الاتصال - إعادة المحاولة...');
        setTimeout(connectPrintAgent, 5000);
    };
    
    printWS.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === 'print_success') {
            alert('✓ تمت الطباعة بنجاح!');
        } else if (data.event === 'error') {
            alert('خطأ: ' + data.error);
        }
    };
}

// الاتصال عند تحميل الصفحة
window.addEventListener('load', connectPrintAgent);

// وظيفة الطباعة
function printInvoice(invoiceId) {
    if (!printWS || printWS.readyState !== WebSocket.OPEN) {
        alert('⚠️ خدمة الطباعة غير متصلة!');
        return;
    }
    
    // جلب محتوى الفاتورة
    fetch(`/api/invoices/${invoiceId}/print-html/`)
        .then(response => response.text())
        .then(html => {
            // إرسال للطباعة
            printWS.send(JSON.stringify({
                action: 'print',
                type: 'html',
                printer: 'default',
                content: html
            }));
        })
        .catch(error => {
            console.error('خطأ:', error);
            alert('فشل تحميل الفاتورة');
        });
}
</script>
```

### 2. إنشاء API للطباعة في Django

في `views.py`:

```python
from django.http import HttpResponse
from django.template.loader import render_to_string

def invoice_print_html(request, invoice_id):
    """إرجاع HTML للطباعة"""
    invoice = Invoice.objects.get(id=invoice_id)
    
    html = render_to_string('invoices/print_template.html', {
        'invoice': invoice,
        'items': invoice.items.all(),
        'company': request.user.company,
    })
    
    return HttpResponse(html, content_type='text/html; charset=utf-8')
```

في `urls.py`:

```python
urlpatterns = [
    path('api/invoices/<int:invoice_id>/print-html/', 
         invoice_print_html, 
         name='invoice_print_html'),
]
```

### 3. قالب الطباعة

أنشئ `templates/invoices/print_template.html`:

```html
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <style>
        @page { 
            size: A4; 
            margin: 10mm; 
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 12pt;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        .company-name {
            font-size: 24pt;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;
        }
        th {
            background-color: #f2f2f2;
        }
        .total-row {
            font-weight: bold;
            font-size: 14pt;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ company.name }}</div>
        <div>{{ company.address }}</div>
        <div>السجل التجاري: {{ company.cr_number }}</div>
        <div>الرقم الضريبي: {{ company.vat_number }}</div>
    </div>
    
    <h2>فاتورة ضريبية</h2>
    
    <div>
        <strong>رقم الفاتورة:</strong> {{ invoice.invoice_number }}<br>
        <strong>التاريخ:</strong> {{ invoice.date|date:"d/m/Y" }}<br>
        <strong>الكاشير:</strong> {{ invoice.cashier.get_full_name }}
    </div>
    
    <table>
        <thead>
            <tr>
                <th>الصنف</th>
                <th>الكمية</th>
                <th>السعر</th>
                <th>المجموع</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.product.name }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ item.unit_price|floatformat:2 }}</td>
                <td>{{ item.total|floatformat:2 }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="3">المجموع الفرعي</td>
                <td>{{ invoice.subtotal|floatformat:2 }}</td>
            </tr>
            <tr>
                <td colspan="3">ضريبة القيمة المضافة (15%)</td>
                <td>{{ invoice.tax_amount|floatformat:2 }}</td>
            </tr>
            <tr class="total-row">
                <td colspan="3">الإجمالي</td>
                <td>{{ invoice.grand_total|floatformat:2 }}</td>
            </tr>
        </tfoot>
    </table>
    
    <div style="text-align: center; margin-top: 40px;">
        <p>شكراً لتعاملكم معنا</p>
    </div>
</body>
</html>
```

### 4. زر الطباعة في واجهة نقاط البيع

```html
<button onclick="printInvoice({{ invoice.id }})" class="btn btn-primary">
    🖨️ طباعة الفاتورة
</button>
```

---

## 🔧 إعدادات متقدمة

### تغيير المنفذ (Port)

افتح `agent.py` وعدّل:

```python
agent = PrintAgent(host='localhost', port=9876)  # غير 9876 للمنفذ المطلوب
```

### تشغيل كخدمة Windows Service

استخدم **NSSM** (Non-Sucking Service Manager):

```cmd
# تحميل NSSM
# https://nssm.cc/download

nssm install TonyPrintAgent "C:\Python\python.exe" "C:\TonyERP\print_agent\agent.py"
nssm set TonyPrintAgent AppDirectory "C:\TonyERP\print_agent"
nssm start TonyPrintAgent
```

---

## 🐛 حل المشاكل

### المشكلة: "لا يمكن الاتصال بـ Print Agent"

**الحل:**
1. تأكد من تشغيل `agent.py`
2. تحقق من Firewall (فتح Port 9876)
3. تأكد من عدم استخدام Port من برنامج آخر

### المشكلة: "الطابعة لا تستجيب"

**الحل:**
1. تأكد من تثبيت الطابعة على Windows
2. اطبع صفحة تجريبية من Windows
3. أعد تشغيل Print Agent

### المشكلة: "خطأ في تثبيت pywin32"

**الحل:**
```cmd
pip install --upgrade pip
pip install pywin32
python -m pywin32_postinstall -install
```

---

## 📞 الدعم الفني

للمساعدة والاستفسارات:
- راجع ملف `print_agent.log` للأخطاء
- جرب ملف الاختبار `test_print.html`
- تأكد من تشغيل الخدمة بصلاحيات كافية

---

## 📝 ملاحظات مهمة

1. ⚠️ **الأمان:** الخدمة تستمع على `localhost` فقط (آمن)
2. ✅ **الأداء:** الطباعة فورية (< 1 ثانية)
3. 🔄 **الموثوقية:** الخدمة تعيد الاتصال تلقائيًا عند الانقطاع
4. 💾 **السجلات:** كل عمليات الطباعة مسجلة في `print_agent.log`

---

**تم بناء النظام بواسطة Tony ERP Team** 🚀
