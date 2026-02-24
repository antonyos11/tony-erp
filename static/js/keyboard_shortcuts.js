// نظام اختصارات لوحة المفاتيح - JavaScript
// Keyboard Shortcuts Handler

class KeyboardShortcutsHandler {
    constructor(module = 'general') {
        this.module = module;
        this.shortcuts = {};
        this.enabled = true;
        this.init();
    }
    
    init() {
        // تحميل الاختصارات من السيرفر أو من التكوين
        this.loadShortcuts();
        
        // الاستماع لأحداث لوحة المفاتيح
        document.addEventListener('keydown', this.handleKeyPress.bind(this));
        
        // عرض مساعدة الاختصارات
        this.createHelpDialog();
    }
    
    loadShortcuts() {
        // الاختصارات العامة
        this.shortcuts = {
            'Ctrl+S': { action: 'save', description: 'حفظ' },
            'Ctrl+N': { action: 'new', description: 'جديد' },
            'Ctrl+F': { action: 'search', description: 'بحث' },
            'Ctrl+P': { action: 'print', description: 'طباعة' },
            'Escape': { action: 'cancel', description: 'إلغاء' },
            'F3': { action: 'searchAccount', description: 'البحث في الحسابات' },
            'F4': { action: 'calculator', description: 'الآلة الحاسبة' },
            'F5': { action: 'newInvoice', description: 'فاتورة جديدة' }
        };
        
        // اختصارات خاصة بالوحدة
        if (this.module === 'accounting') {
            Object.assign(this.shortcuts, {
                'Ctrl+D': { action: 'duplicate', description: 'نسخ' },
                'F2': { action: 'nextField', description: 'الحقل التالي' },
                'F3': { action: 'searchAccount', description: 'بحث عن حساب' },
                'F4': { action: 'calculator', description: 'آلة حاسبة' },
                'Ctrl+T': { action: 'saveTemplate', description: 'حفظ كقالب' },
                'Ctrl+L': { action: 'loadTemplate', description: 'تحميل قالب' }
            });
        } else if (this.module === 'invoices') {
            Object.assign(this.shortcuts, {
                'F5': { action: 'addItem', description: 'إضافة صنف' },
                'F6': { action: 'scanBarcode', description: 'مسح باركود' },
                'F7': { action: 'selectCustomer', description: 'اختيار عميل' },
                'F8': { action: 'payment', description: 'الدفع' },
                'F9': { action: 'discount', description: 'خصم' },
                'F12': { action: 'submit', description: 'إنهاء وحفظ' }
            });
        } else if (this.module === 'pos') {
            Object.assign(this.shortcuts, {
                'F1': { action: 'cash', description: 'نقدي' },
                'F2': { action: 'card', description: 'بطاقة' },
                'F3': { action: 'change', description: 'حساب الباقي' },
                'F4': { action: 'hold', description: 'تعليق' },
                'F5': { action: 'recall', description: 'استرجاع' },
                'F8': { action: 'cancelItem', description: 'إلغاء صنف' },
                'F9': { action: 'cancelAll', description: 'إلغاء الكل' },
                'F12': { action: 'printReceipt', description: 'طباعة' }
            });
        }
    }
    
    handleKeyPress(event) {
        if (!this.enabled) return;
        
        // تكوين مفتاح الاختصار
        let shortcut = '';
        if (event.ctrlKey) shortcut += 'Ctrl+';
        if (event.altKey) shortcut += 'Alt+';
        if (event.shiftKey) shortcut += 'Shift+';
        
        // إضافة المفتاح الأساسي
        if (event.key.startsWith('F') && event.key.length <= 3) {
            shortcut += event.key;
        } else {
            shortcut += event.key.toUpperCase();
        }
        
        // التحقق من وجود الاختصار
        const config = this.shortcuts[shortcut];
        if (config) {
            event.preventDefault();
            this.executeAction(config.action);
        }
    }
    
    executeAction(action) {
        console.log('تنفيذ الإجراء:', action);
        
        // إطلاق حدث مخصص
        const customEvent = new CustomEvent('shortcut-action', {
            detail: { action: action, module: this.module }
        });
        document.dispatchEvent(customEvent);
        
        // تنفيذ الإجراءات المباشرة
        switch(action) {
            case 'save':
                this.triggerSave();
                break;
            case 'print':
                this.triggerPrint();
                break;
            case 'help':
                // Check if ContextualHelp is available
                if (window.contextualHelp && typeof window.contextualHelp.showGeneralHelp === 'function') {
                    window.contextualHelp.showGeneralHelp();
                } else {
                    this.showHelp();
                }
                break;
            case 'newInvoice':
                 window.location.href = '/sales/new/';
                 break;
            case 'cancel':
                this.triggerCancel();
                break;
            case 'search':
                this.triggerSearch();
                break;
            case 'calculator':
                this.showCalculator();
                break;
            case 'nextField':
                this.focusNextField();
                break;
            case 'new':
                this.triggerNew();
                break;
            case 'searchAccount':
                this.triggerSearchAccount();
                break;
            // إضافة المزيد من الإجراءات حسب الحاجة
        }
    }
    
    triggerSave() {
        // البحث عن زر الحفظ والنقر عليه
        const saveBtn = document.querySelector('button[type="submit"], .btn-save, #save-btn');
        if (saveBtn) {
            saveBtn.click();
        } else {
             // Fallback for Ctrl+S if no button found
             // prevent default browser save
             console.log("Save action triggered but no save button found");
        }
    }
    
    triggerNew() {
        // فاتورة جديدة أو عنصر جديد
         window.location.href = '/sales/new/';
    }

    triggerSearchAccount() {
        // F3 - البحث في الحسابات
        // نحاول نوصل لحقل البحث او نفتح مودال
        // هنا سنفترض وجود حقل بحث عن حساب او نقوم بالتوجه لصفحة الحسابات
        // او نقوم بفتح قائمة الحسابات
        // حسب السياق الحالي، سنقوم بفتح شاشة الحسابات
        window.location.href = '/accounting/accounts/';
    }

    triggerPrint() {
        const printBtn = document.querySelector('.btn-print, #print-btn');
        if (printBtn) {
            printBtn.click();
        } else {
            window.print();
        }
    }
    
    triggerCancel() {
        const cancelBtn = document.querySelector('.btn-cancel, #cancel-btn');
        if (cancelBtn) {
            cancelBtn.click();
        }
    }
    
    triggerSearch() {
        const searchInput = document.querySelector('input[type="search"], #search-input');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    showCalculator() {
        // فتح آلة حاسبة منبثقة
        if (!document.getElementById('calculator-widget')) {
            this.createCalculator();
        }
        document.getElementById('calculator-widget').style.display = 'block';
    }
    
    focusNextField() {
        const activeElement = document.activeElement;
        if (activeElement.tagName === 'INPUT' || activeElement.tagName === 'SELECT') {
            const form = activeElement.closest('form');
            if (form) {
                const inputs = Array.from(form.querySelectorAll('input, select, textarea'));
                const currentIndex = inputs.indexOf(activeElement);
                if (currentIndex < inputs.length - 1) {
                    inputs[currentIndex + 1].focus();
                }
            }
        }
    }
    
    createHelpDialog() {
        // إنشاء نافذة المساعدة
        const helpDialog = document.createElement('div');
        helpDialog.id = 'shortcuts-help';
        helpDialog.className = 'modal fade';
        helpDialog.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">اختصارات لوحة المفاتيح</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>الاختصار</th>
                                    <th>الوصف</th>
                                </tr>
                            </thead>
                            <tbody id="shortcuts-list"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(helpDialog);
    }
    
    showHelp() {
        // ملء قائمة الاختصارات
        const list = document.getElementById('shortcuts-list');
        list.innerHTML = '';
        
        Object.entries(this.shortcuts).forEach(([key, config]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><kbd>${key}</kbd></td>
                <td>${config.description}</td>
            `;
            list.appendChild(row);
        });
        
        // عرض النافذة
        const modal = new bootstrap.Modal(document.getElementById('shortcuts-help'));
        modal.show();
    }
    
    createCalculator() {
        const calc = document.createElement('div');
        calc.id = 'calculator-widget';
        calc.className = 'calculator-widget';
        calc.innerHTML = `
            <div class="calculator">
                <div class="calculator-header">
                    <span>آلة حاسبة</span>
                    <button onclick="document.getElementById('calculator-widget').style.display='none'">&times;</button>
                </div>
                <input type="text" id="calc-display" readonly>
                <div class="calculator-buttons">
                    <button onclick="calcAppend('7')">7</button>
                    <button onclick="calcAppend('8')">8</button>
                    <button onclick="calcAppend('9')">9</button>
                    <button onclick="calcAppend('+')">+</button>
                    <button onclick="calcAppend('4')">4</button>
                    <button onclick="calcAppend('5')">5</button>
                    <button onclick="calcAppend('6')">6</button>
                    <button onclick="calcAppend('-')">-</button>
                    <button onclick="calcAppend('1')">1</button>
                    <button onclick="calcAppend('2')">2</button>
                    <button onclick="calcAppend('3')">3</button>
                    <button onclick="calcAppend('*')">×</button>
                    <button onclick="calcAppend('0')">0</button>
                    <button onclick="calcAppend('.')">.</button>
                    <button onclick="calcClear()">C</button>
                    <button onclick="calcAppend('/')">/</button>
                    <button onclick="calcEqual()" class="btn-equal">=</button>
                </div>
            </div>
        `;
        document.body.appendChild(calc);
    }
    
    enable() {
        this.enabled = true;
    }
    
    disable() {
        this.enabled = false;
    }
}

// دوال الآلة الحاسبة
function calcAppend(value) {
    document.getElementById('calc-display').value += value;
}

function calcClear() {
    document.getElementById('calc-display').value = '';
}

function calcEqual() {
    try {
        const result = eval(document.getElementById('calc-display').value);
        document.getElementById('calc-display').value = result;
    } catch(e) {
        document.getElementById('calc-display').value = 'خطأ';
    }
}

// تصدير
window.KeyboardShortcutsHandler = KeyboardShortcutsHandler;

// تفعيل تلقائي
document.addEventListener('DOMContentLoaded', () => {
    // تحديد الوحدة بناءً على الرابط
    let module = 'general';
    const path = window.location.pathname;
    
    if (path.includes('/accounting/')) {
        module = 'accounting';
    } else if (path.includes('/sales/') || path.includes('/invoices/')) {
        module = 'invoices';
    } else if (path.includes('/pos/')) {
        module = 'pos';
    }
    
    // تهيئة المعالج
    if (!window.shortcutsHandler) {
        window.shortcutsHandler = new KeyboardShortcutsHandler(module);
        console.log('Keyboard Shortcuts Initialized for module:', module);
    }
});

