/**
 * QZ Tray - نظام الطباعة المباشرة على XPrinter
 * Direct thermal printing system for POS
 */

// إعدادات الطباعة الحرارية
const ThermalPrinter = {
    // اسم الطابعة (يمكن تغييره)
    printerName: null, // null = الطابعة الافتراضية
    
    // عرض الورق بالملم
    paperWidth: 80,
    
    // أوامر ESC/POS
    ESC: '\x1B',
    GS: '\x1D',
    
    // تهيئة QZ Tray
    init: async function() {
        if (typeof qz === 'undefined') {
            console.warn('QZ Tray غير محمّل - استخدام طباعة المتصفح');
            return false;
        }
        
        try {
            if (!qz.websocket.isActive()) {
                // تعطيل تحذيرات الاتصال في console
                const originalWarn = console.warn;
                const originalError = console.error;
                console.warn = () => {};
                console.error = () => {};
                
                await qz.websocket.connect();
                
                // استعادة console
                console.warn = originalWarn;
                console.error = originalError;
                
                console.log('✅ تم الاتصال بـ QZ Tray');
            }
            return true;
        } catch (err) {
            // لا تطبع الخطأ إلا إذا كان مهماً
            // console.warn('⚠️ QZ Tray غير متاح:', err.message);
            return false;
        }
    },
    
    // البحث عن الطابعات المتاحة
    getPrinters: async function() {
        try {
            await this.init();
            const printers = await qz.printers.find();
            console.log('الطابعات المتاحة:', printers);
            return printers;
        } catch (err) {
            console.error('خطأ:', err);
            return [];
        }
    },
    
    // البحث عن طابعة XPrinter
    findXPrinter: async function() {
        const printers = await this.getPrinters();
        const keywords = ['xp-80', 'xp80', 'xprinter', 'pos', 'thermal', 'receipt'];
        
        for (const printer of printers) {
            const name = printer.toLowerCase();
            for (const keyword of keywords) {
                if (name.includes(keyword)) {
                    console.log('✅ تم العثور على طابعة حرارية:', printer);
                    return printer;
                }
            }
        }
        
        // إذا لم نجد طابعة حرارية، نرجع الأولى
        return printers.length > 0 ? printers[0] : null;
    },
    
    // طباعة إيصال مباشرة
    printReceipt: async function(receiptData) {
        const qzAvailable = await this.init();
        
        if (!qzAvailable) {
            // استخدام طباعة المتصفح كبديل
            return this.browserPrint(receiptData.orderId);
        }
        
        try {
            // البحث عن الطابعة
            const printer = this.printerName || await this.findXPrinter();
            
            if (!printer) {
                console.error('لم يتم العثور على طابعة');
                return this.browserPrint(receiptData.orderId);
            }
            
            // بناء أوامر ESC/POS
            const commands = this.buildReceiptCommands(receiptData);
            
            // إعداد الطباعة
            const config = qz.configs.create(printer, {
                encoding: 'UTF-8'
            });
            
            // إرسال للطابعة
            await qz.print(config, [{
                type: 'raw',
                format: 'command',
                flavor: 'plain',
                data: commands
            }]);
            
            console.log('✅ تم طباعة الإيصال بنجاح');
            return { success: true, printer: printer };
            
        } catch (err) {
            console.error('خطأ في الطباعة:', err);
            return this.browserPrint(receiptData.orderId);
        }
    },
    
    // بناء أوامر ESC/POS للإيصال
    buildReceiptCommands: function(data) {
        let cmd = '';
        
        // تهيئة الطابعة
        cmd += this.ESC + '@';  // Reset
        
        // توسيط + حجم كبير للعنوان
        cmd += this.ESC + 'a1';  // Center
        cmd += this.GS + '!1';   // Double height
        cmd += (data.companyName || 'Tony ERP') + '\n';
        cmd += this.GS + '!0';   // Normal
        
        if (data.branchName) {
            cmd += data.branchName + '\n';
        }
        
        // خط فاصل
        cmd += '================================\n';
        
        // معلومات الفاتورة (يمين)
        cmd += this.ESC + 'a0';  // Right align
        cmd += 'فاتورة رقم: ' + (data.orderNumber || data.orderId) + '\n';
        cmd += 'التاريخ: ' + (data.date || new Date().toLocaleString('ar-EG')) + '\n';
        
        if (data.customerName) {
            cmd += 'العميل: ' + data.customerName + '\n';
        }
        if (data.cashierName) {
            cmd += 'الكاشير: ' + data.cashierName + '\n';
        }
        
        cmd += '--------------------------------\n';
        
        // المنتجات
        if (data.items && data.items.length > 0) {
            cmd += this.ESC + 'E1';  // Bold on
            cmd += 'الصنف           الكمية    السعر\n';
            cmd += this.ESC + 'E0';  // Bold off
            cmd += '--------------------------------\n';
            
            for (const item of data.items) {
                const name = (item.name || '').substring(0, 15).padEnd(15);
                const qty = String(item.qty || 1).padStart(4);
                const price = String(item.total || item.price || 0).padStart(8);
                cmd += name + qty + price + '\n';
            }
        }
        
        cmd += '--------------------------------\n';
        
        // الإجماليات
        cmd += this.ESC + 'E1';  // Bold
        cmd += 'المجموع:                ' + (data.subtotal || data.total || 0) + '\n';
        
        if (data.discount && data.discount > 0) {
            cmd += 'الخصم:                 -' + data.discount + '\n';
        }
        if (data.tax && data.tax > 0) {
            cmd += 'الضريبة:               ' + data.tax + '\n';
        }
        
        cmd += '================================\n';
        cmd += this.GS + '!1';   // Double
        cmd += 'الإجمالي:       ' + (data.total || 0) + ' ج.م\n';
        cmd += this.GS + '!0';   // Normal
        cmd += this.ESC + 'E0';  // Bold off
        cmd += '================================\n';
        
        // المدفوع والباقي
        if (data.paid) {
            cmd += 'المدفوع:               ' + data.paid + '\n';
            const change = (parseFloat(data.paid) - parseFloat(data.total)).toFixed(2);
            if (change > 0) {
                cmd += 'الباقي:                ' + change + '\n';
            }
        }
        
        // التذييل
        cmd += '\n';
        cmd += this.ESC + 'a1';  // Center
        cmd += 'شكراً لتعاملكم معنا\n';
        cmd += 'نتمنى لكم يوماً سعيداً\n';
        cmd += '\n\n\n';
        
        // قص الورق
        cmd += this.GS + 'V\x01';  // Partial cut
        
        return cmd;
    },
    
    // طباعة عبر المتصفح (fallback)
    browserPrint: function(orderId) {
        console.log('📄 استخدام طباعة المتصفح...');
        
        const printWindow = window.open(
            `/pos/order/${orderId}/receipt/?thermal=1&auto=1`,
            'print_receipt',
            'width=350,height=600,scrollbars=yes'
        );
        
        if (printWindow) {
            printWindow.onload = function() {
                setTimeout(() => printWindow.print(), 300);
            };
            return { success: true, method: 'browser' };
        }
        
        return { success: false, error: 'تعذر فتح نافذة الطباعة' };
    },
    
    // اختبار الطباعة
    testPrint: async function() {
        const testData = {
            orderId: 'TEST',
            companyName: 'Tony ERP',
            branchName: 'اختبار الطباعة',
            orderNumber: 'TEST-001',
            date: new Date().toLocaleString('ar-EG'),
            items: [
                { name: 'منتج تجريبي 1', qty: 2, price: 100, total: 200 },
                { name: 'منتج تجريبي 2', qty: 1, price: 150, total: 150 }
            ],
            subtotal: 350,
            tax: 52.50,
            total: 402.50,
            paid: 500
        };
        
        return await this.printReceipt(testData);
    }
};

// تصدير للاستخدام العام
window.ThermalPrinter = ThermalPrinter;

// محاولة التهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    ThermalPrinter.init().then(available => {
        if (available) {
            console.log('✅ QZ Tray جاهز للطباعة المباشرة');
        } else {
            console.log('ℹ️ سيتم استخدام طباعة المتصفح');
        }
    });
});
