/**
 * نظام الطباعة الصامتة للإيصالات الحرارية
 * Silent Thermal Receipt Printing System
 * 
 * هذا الملف يوفر طباعة تلقائية مباشرة على الطابعة الحرارية
 * بدون فتح نوافذ حوار أو انتظار من المستخدم
 */

const SilentPrint = {
    // إعدادات الطابعة
    settings: {
        printerName: null,      // اسم الطابعة (null = الافتراضية)
        paperWidth: 80,         // عرض الورق بالملم
        autoCut: true,          // قص تلقائي
        openDrawer: false,      // فتح درج النقود
        copies: 1               // عدد النسخ
    },
    
    // طباعة إيصال مباشرة
    printReceipt: function(orderId, options = {}) {
        const settings = { ...this.settings, ...options };
        
        console.log('🖨️ بدء الطباعة الصامتة للطلب:', orderId);
        
        // إنشاء iframe مخفي
        let printFrame = document.getElementById('silentPrintFrame');
        if (!printFrame) {
            printFrame = document.createElement('iframe');
            printFrame.id = 'silentPrintFrame';
            printFrame.style.cssText = 'position:fixed;left:-9999px;top:0;width:80mm;height:0;border:0;visibility:hidden;';
            document.body.appendChild(printFrame);
        }
        
        // رابط الإيصال الحراري
        const receiptUrl = `/pos/order/${orderId}/receipt/?thermal=1&auto=1&silent=1`;
        
        return new Promise((resolve, reject) => {
            printFrame.onload = function() {
                try {
                    // تطبيق إعدادات الطباعة
                    const frameWindow = printFrame.contentWindow;
                    
                    // انتظار تحميل المحتوى
                    setTimeout(() => {
                        // طباعة صامتة
                        frameWindow.print();
                        
                        console.log('✅ تم إرسال أمر الطباعة للطلب:', orderId);
                        
                        // تنظيف بعد الطباعة
                        setTimeout(() => {
                            printFrame.src = 'about:blank';
                        }, 2000);
                        
                        resolve({ success: true, orderId: orderId });
                    }, 300);
                    
                } catch (error) {
                    console.error('❌ خطأ في الطباعة:', error);
                    reject(error);
                }
            };
            
            printFrame.onerror = function(error) {
                console.error('❌ خطأ في تحميل الإيصال:', error);
                reject(error);
            };
            
            // تحميل الإيصال
            printFrame.src = receiptUrl;
        });
    },
    
    // طباعة مباشرة من بيانات HTML
    printHTML: function(htmlContent, options = {}) {
        return new Promise((resolve, reject) => {
            let printFrame = document.getElementById('silentPrintFrame');
            if (!printFrame) {
                printFrame = document.createElement('iframe');
                printFrame.id = 'silentPrintFrame';
                printFrame.style.cssText = 'position:fixed;left:-9999px;top:0;width:80mm;height:0;border:0;visibility:hidden;';
                document.body.appendChild(printFrame);
            }
            
            const frameDoc = printFrame.contentDocument || printFrame.contentWindow.document;
            frameDoc.open();
            frameDoc.write(htmlContent);
            frameDoc.close();
            
            setTimeout(() => {
                try {
                    printFrame.contentWindow.print();
                    resolve({ success: true });
                } catch (error) {
                    reject(error);
                }
            }, 500);
        });
    },
    
    // إنشاء محتوى إيصال HTML
    createReceiptHTML: function(data) {
        return `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: 80mm auto; margin: 0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; font-size: 12px; width: 80mm; }
        .receipt { padding: 5mm; }
        .header { text-align: center; border-bottom: 2px dashed #000; padding-bottom: 10px; margin-bottom: 10px; }
        .company { font-size: 16px; font-weight: bold; }
        .branch { font-size: 12px; color: #333; }
        .info { margin: 10px 0; font-size: 11px; }
        .info-row { display: flex; justify-content: space-between; margin: 3px 0; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th { background: #eee; padding: 5px; font-size: 10px; text-align: right; }
        td { padding: 5px; font-size: 11px; border-bottom: 1px dotted #ccc; }
        .totals { border-top: 2px solid #000; border-bottom: 2px solid #000; padding: 10px 0; margin: 10px 0; }
        .total-row { display: flex; justify-content: space-between; margin: 4px 0; }
        .grand-total { font-size: 16px; font-weight: bold; margin-top: 8px; padding-top: 8px; border-top: 1px dashed #000; }
        .footer { text-align: center; margin-top: 15px; font-size: 11px; }
        .thanks { font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="receipt">
        <div class="header">
            <div class="company">${data.companyName || 'Tony ERP'}</div>
            <div class="branch">${data.branchName || ''}</div>
        </div>
        
        <div class="info">
            <div class="info-row"><span>رقم الفاتورة:</span><span>${data.orderNumber || data.orderId}</span></div>
            <div class="info-row"><span>التاريخ:</span><span>${data.date || new Date().toLocaleDateString('ar-EG')}</span></div>
            <div class="info-row"><span>الوقت:</span><span>${data.time || new Date().toLocaleTimeString('ar-EG', {hour: '2-digit', minute: '2-digit'})}</span></div>
            ${data.cashierName ? `<div class="info-row"><span>الكاشير:</span><span>${data.cashierName}</span></div>` : ''}
        </div>
        
        <table>
            <thead>
                <tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>
            </thead>
            <tbody>
                ${(data.items || []).map(item => `
                    <tr>
                        <td>${item.name}</td>
                        <td style="text-align:center">${item.qty || item.quantity}</td>
                        <td style="text-align:center">${item.price}</td>
                        <td style="text-align:left">${item.total || (item.qty * item.price)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        
        <div class="totals">
            <div class="total-row"><span>المجموع:</span><span>${data.subtotal || data.total} ج.م</span></div>
            ${data.discount ? `<div class="total-row"><span>الخصم:</span><span style="color:red">-${data.discount} ج.م</span></div>` : ''}
            <div class="total-row grand-total"><span>الإجمالي:</span><span>${data.total} ج.م</span></div>
        </div>
        
        <div class="info">
            <div class="info-row"><span>المدفوع:</span><span>${data.paid || data.total} ج.م</span></div>
            ${data.change && data.change > 0 ? `<div class="info-row"><span>الباقي:</span><span>${data.change} ج.م</span></div>` : ''}
        </div>
        
        <div class="footer">
            <div class="thanks">شكراً لتعاملكم معنا! 🙏</div>
        </div>
    </div>
    <script>
        setTimeout(function() { window.print(); }, 100);
    </script>
</body>
</html>`;
    },
    
    // اختبار الطباعة
    test: function() {
        const testData = {
            companyName: 'Tony ERP',
            branchName: 'اختبار الطباعة',
            orderId: 'TEST-' + Date.now(),
            orderNumber: 'TEST-001',
            date: new Date().toLocaleDateString('ar-EG'),
            time: new Date().toLocaleTimeString('ar-EG', {hour: '2-digit', minute: '2-digit'}),
            cashierName: 'مدير النظام',
            items: [
                { name: 'منتج تجريبي 1', qty: 2, price: 100, total: 200 },
                { name: 'منتج تجريبي 2', qty: 1, price: 150, total: 150 }
            ],
            subtotal: 350,
            discount: 0,
            total: 350,
            paid: 400,
            change: 50
        };
        
        const html = this.createReceiptHTML(testData);
        return this.printHTML(html);
    }
};

// تصدير للاستخدام العام
window.SilentPrint = SilentPrint;

// رسالة تأكيد التحميل
console.log('✅ نظام الطباعة الصامتة جاهز - SilentPrint');
