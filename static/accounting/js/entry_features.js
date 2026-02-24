/**
 * ميزات نموذج تسجيل الإيراد/المنصرف المتقدمة
 * Tony ERP - Accounting Module
 * 
 * الميزات المتضمنة:
 * 1. الحفظ التلقائي
 * 2. القوالب المحفوظة
 * 3. حساب الضريبة التلقائي
 * 4. البحث الذكي للحسابات
 * 5. اختصارات لوحة المفاتيح
 * 6. النسخ من فاتورة
 * 7. الحسابات السريعة
 * 8. التذكيرات الذكية
 * 9. سحب وإفلات المرفقات
 * 10. التصدير والطباعة
 * 11. سجل التغييرات
 * 12. تنبيهات الحد الائتماني
 */

(function() {
    'use strict';

    // تهيئة الوحدة
    const EntryFeatures = {
        config: {
            autosaveInterval: 10000, // 10 ثواني
            taxRate: 0.15, // 15% ضريبة القيمة المضافة
            csrfToken: null,
            entryType: 'revenue',
        },
        
        state: {
            isDirty: false,
            lastSavedData: null,
            autosaveTimer: null,
            calcValue: '0',
            attachments: [],
        },

        init: function() {
            console.log('🚀 تهيئة ميزات نموذج الإيراد/المنصرف...');
            
            // استخراج CSRF token
            const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfInput) {
                this.config.csrfToken = csrfInput.value;
            }
            
            // تحديد نوع القيد
            const entryTypeInput = document.querySelector('[data-entry-type]');
            if (entryTypeInput) {
                this.config.entryType = entryTypeInput.dataset.entryType;
            }
            
            // تهيئة جميع الميزات
            this.initAutosave();
            this.initTemplates();
            this.initTaxCalculator();
            this.initSmartSearch();
            this.initKeyboardShortcuts();
            this.initCopyFromInvoice();
            this.initQuickCalculator();
            this.initSmartReminders();
            this.initAttachments();
            this.initExportOptions();
            this.initChangeHistory();
            this.initCreditAlerts();
            this.initHelpButton();
            
            // ميزات جديدة محسّنة
            this.initDraftRestoreBanner();
            this.initLastChoicesMemory();
            this.initAccountValidation();
            this.initDuplicateDetection();
            this.initTemplateManagement();
            this.initRecentEntriesCopy();
            this.initAttachmentsPreview();
            this.initEnhancedKeyboardShortcuts();
            
            // مراقبة التغييرات
            this.watchFormChanges();
            
            console.log('✅ تم تهيئة جميع الميزات بنجاح');
        },

        // ==================== 1. الحفظ التلقائي ====================
        initAutosave: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            // إنشاء مؤشر الحفظ
            const indicator = document.createElement('div');
            indicator.className = 'autosave-indicator';
            indicator.innerHTML = '<i class="bi bi-check-circle"></i><span>تم الحفظ تلقائياً</span>';
            document.body.appendChild(indicator);
            
            // بدء المؤقت
            this.state.autosaveTimer = setInterval(() => {
                if (this.state.isDirty) {
                    this.performAutosave();
                }
            }, this.config.autosaveInterval);
        },

        performAutosave: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => data[key] = value);
            
            // عرض حالة الحفظ
            const indicator = document.querySelector('.autosave-indicator');
            if (indicator) {
                indicator.classList.add('show', 'saving');
                indicator.innerHTML = '<div class="autosave-spinner"></div><span>جاري الحفظ...</span>';
            }
            
            // حفظ في LocalStorage
            const storageKey = `entry_draft_${this.config.entryType}`;
            localStorage.setItem(storageKey, JSON.stringify({
                data: data,
                timestamp: Date.now()
            }));
            
            // إرسال للخادم (اختياري)
            fetch('/accounting/api/autosave/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken,
                },
                body: JSON.stringify(data)
            }).catch(() => {
                // التجاهل في حالة عدم توفر الـ API
            }).finally(() => {
                setTimeout(() => {
                    if (indicator) {
                        indicator.classList.remove('saving');
                        indicator.innerHTML = '<i class="bi bi-check-circle"></i><span>تم الحفظ تلقائياً</span>';
                        setTimeout(() => indicator.classList.remove('show'), 2000);
                    }
                }, 500);
            });
            
            this.state.isDirty = false;
            this.state.lastSavedData = data;
        },

        // استعادة المسودة
        restoreDraft: function() {
            const storageKey = `entry_draft_${this.config.entryType}`;
            const saved = localStorage.getItem(storageKey);
            
            if (saved) {
                const { data, timestamp } = JSON.parse(saved);
                const age = Date.now() - timestamp;
                
                // استعادة فقط إذا كان أقل من ساعة
                if (age < 3600000) {
                    if (confirm('يوجد مسودة محفوظة. هل تريد استعادتها؟')) {
                        Object.keys(data).forEach(key => {
                            const input = document.querySelector(`[name="${key}"]`);
                            if (input) input.value = data[key];
                        });
                    }
                }
            }
        },

        // ==================== 2. القوالب المحفوظة ====================
        initTemplates: function() {
            const container = document.querySelector('.templates-section');
            if (!container) return;
            
            // تحميل القوالب المحفوظة
            this.loadTemplates();
            
            // زر حفظ قالب جديد
            const saveBtn = container.querySelector('.save-template-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => this.saveAsTemplate());
            }
        },

        loadTemplates: function() {
            const templates = JSON.parse(localStorage.getItem('entry_templates') || '[]');
            const list = document.querySelector('.templates-list');
            if (!list) return;
            
            // قوالب افتراضية
            const defaultTemplates = [
                { id: 'rent', name: 'إيجار شهري', icon: 'bi-building', data: { description: 'إيجار شهر ' } },
                { id: 'salary', name: 'رواتب', icon: 'bi-people', data: { description: 'رواتب شهر ' } },
                { id: 'utilities', name: 'خدمات', icon: 'bi-lightning', data: { description: 'فواتير خدمات ' } },
            ];
            
            const allTemplates = [...defaultTemplates, ...templates];
            
            allTemplates.forEach(template => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'template-btn';
                btn.innerHTML = `<i class="${template.icon || 'bi-file-text'}"></i>${template.name}`;
                btn.addEventListener('click', () => this.applyTemplate(template));
                
                // إدراج قبل زر الحفظ
                const saveBtn = list.querySelector('.save-template-btn');
                if (saveBtn) {
                    list.insertBefore(btn, saveBtn);
                } else {
                    list.appendChild(btn);
                }
            });
        },

        applyTemplate: function(template) {
            if (template.data) {
                Object.keys(template.data).forEach(key => {
                    const input = document.querySelector(`[name="${key}"]`);
                    if (input) {
                        input.value = template.data[key];
                        input.dispatchEvent(new Event('change'));
                    }
                });
            }
            this.showToast(`تم تطبيق قالب "${template.name}"`, 'success');
        },

        saveAsTemplate: function() {
            const name = prompt('أدخل اسم القالب:');
            if (!name) return;
            
            const form = document.getElementById('entryForm');
            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                if (key !== 'csrfmiddlewaretoken' && key !== 'date') {
                    data[key] = value;
                }
            });
            
            const templates = JSON.parse(localStorage.getItem('entry_templates') || '[]');
            templates.push({
                id: Date.now(),
                name: name,
                icon: 'bi-star',
                data: data
            });
            localStorage.setItem('entry_templates', JSON.stringify(templates));
            
            this.showToast('تم حفظ القالب بنجاح', 'success');
            location.reload();
        },

        // ==================== 3. حساب الضريبة التلقائي ====================
        initTaxCalculator: function() {
            const amountInput = document.querySelector('[name="amount"]');
            const taxSection = document.querySelector('.tax-calculator');
            
            if (!amountInput) return;
            
            // إنشاء قسم الضريبة إذا لم يكن موجوداً
            if (!taxSection) {
                const calculator = document.createElement('div');
                calculator.className = 'tax-calculator';
                calculator.innerHTML = `
                    <div class="tax-row">
                        <span class="tax-label">المبلغ الأساسي:</span>
                        <span class="tax-value" id="baseAmount">0.00</span>
                    </div>
                    <div class="tax-row">
                        <span class="tax-label">ضريبة القيمة المضافة (${this.config.taxRate * 100}%):</span>
                        <span class="tax-value" id="taxAmount">0.00</span>
                    </div>
                    <div class="tax-row tax-total-row">
                        <span class="tax-label">الإجمالي شامل الضريبة:</span>
                        <span class="tax-value" id="totalWithTax">0.00</span>
                    </div>
                `;
                amountInput.parentNode.appendChild(calculator);
            }
            
            // تحديث عند تغيير المبلغ
            amountInput.addEventListener('input', () => this.calculateTax(amountInput.value));
        },

        calculateTax: function(amount) {
            const value = parseFloat(amount) || 0;
            const tax = value * this.config.taxRate;
            const total = value + tax;
            
            const baseEl = document.getElementById('baseAmount');
            const taxEl = document.getElementById('taxAmount');
            const totalEl = document.getElementById('totalWithTax');
            
            if (baseEl) baseEl.textContent = value.toFixed(2);
            if (taxEl) taxEl.textContent = tax.toFixed(2);
            if (totalEl) totalEl.textContent = total.toFixed(2);
        },

        // ==================== 4. البحث الذكي للحسابات ====================
        initSmartSearch: function() {
            const accountSelect = document.querySelector('[name="ledger_account"]');
            if (!accountSelect) return;
            
            // تحويل إلى بحث ذكي
            const container = document.createElement('div');
            container.className = 'smart-search-container';
            
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.className = 'form-control smart-search-input';
            searchInput.placeholder = 'ابحث عن الحساب بالكود أو الاسم...';
            searchInput.autocomplete = 'off';
            
            const icon = document.createElement('i');
            icon.className = 'bi bi-search smart-search-icon';
            
            const dropdown = document.createElement('div');
            dropdown.className = 'search-results-dropdown';
            
            container.appendChild(searchInput);
            container.appendChild(icon);
            container.appendChild(dropdown);
            
            // إخفاء السيليكت الأصلي
            accountSelect.style.display = 'none';
            accountSelect.parentNode.insertBefore(container, accountSelect);
            
            // استخراج الخيارات
            const options = Array.from(accountSelect.options).filter(opt => opt.value);
            
            // معالجة البحث
            searchInput.addEventListener('input', () => {
                const query = searchInput.value.toLowerCase();
                if (query.length < 1) {
                    dropdown.classList.remove('show');
                    return;
                }
                
                const matches = options.filter(opt => 
                    opt.text.toLowerCase().includes(query)
                ).slice(0, 10);
                
                dropdown.innerHTML = matches.map(opt => `
                    <div class="search-result-item" data-value="${opt.value}">
                        <span class="result-code">${opt.text.split(' - ')[0]}</span>
                        <span class="result-name">${opt.text.split(' - ').slice(1).join(' - ')}</span>
                    </div>
                `).join('');
                
                dropdown.classList.add('show');
            });
            
            // اختيار نتيجة
            dropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.search-result-item');
                if (item) {
                    const value = item.dataset.value;
                    accountSelect.value = value;
                    searchInput.value = item.textContent.trim();
                    dropdown.classList.remove('show');
                    this.state.isDirty = true;
                }
            });
            
            // إغلاق عند النقر خارجاً
            document.addEventListener('click', (e) => {
                if (!container.contains(e.target)) {
                    dropdown.classList.remove('show');
                }
            });
        },

        // ==================== 5. اختصارات لوحة المفاتيح ====================
        initKeyboardShortcuts: function() {
            // إنشاء لوحة الاختصارات
            const overlay = document.createElement('div');
            overlay.className = 'shortcuts-overlay';
            
            const panel = document.createElement('div');
            panel.className = 'keyboard-shortcuts-panel';
            panel.innerHTML = `
                <div class="shortcuts-header">
                    <h5><i class="bi bi-keyboard"></i> اختصارات لوحة المفاتيح</h5>
                    <button class="shortcuts-close">&times;</button>
                </div>
                <div class="shortcuts-list">
                    <div class="shortcut-item">
                        <span class="shortcut-desc">حفظ النموذج</span>
                        <span class="shortcut-keys">
                            <span class="shortcut-key">Ctrl</span>
                            <span class="shortcut-key">S</span>
                        </span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-desc">الانتقال للحقل التالي</span>
                        <span class="shortcut-keys">
                            <span class="shortcut-key">Tab</span>
                        </span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-desc">إظهار الآلة الحاسبة</span>
                        <span class="shortcut-keys">
                            <span class="shortcut-key">Ctrl</span>
                            <span class="shortcut-key">K</span>
                        </span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-desc">إظهار القوالب</span>
                        <span class="shortcut-keys">
                            <span class="shortcut-key">Ctrl</span>
                            <span class="shortcut-key">T</span>
                        </span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-desc">إظهار هذه اللوحة</span>
                        <span class="shortcut-keys">
                            <span class="shortcut-key">?</span>
                        </span>
                    </div>
                </div>
            `;
            
            document.body.appendChild(overlay);
            document.body.appendChild(panel);
            
            // إغلاق اللوحة
            const close = () => {
                overlay.classList.remove('show');
                panel.classList.remove('show');
            };
            
            overlay.addEventListener('click', close);
            panel.querySelector('.shortcuts-close').addEventListener('click', close);
            
            // معالجة الاختصارات
            document.addEventListener('keydown', (e) => {
                // Ctrl+S للحفظ
                if (e.ctrlKey && e.key === 's') {
                    e.preventDefault();
                    document.getElementById('entryForm')?.submit();
                }
                
                // Ctrl+K للآلة الحاسبة
                if (e.ctrlKey && e.key === 'k') {
                    e.preventDefault();
                    this.toggleCalculator();
                }
                
                // ? لإظهار الاختصارات
                if (e.key === '?' && !e.target.matches('input, textarea')) {
                    overlay.classList.toggle('show');
                    panel.classList.toggle('show');
                }
                
                // Escape للإغلاق
                if (e.key === 'Escape') {
                    close();
                    document.querySelector('.quick-calc-panel')?.classList.remove('show');
                }
            });
        },

        // ==================== 6. النسخ من فاتورة ====================
        initCopyFromInvoice: function() {
            const section = document.querySelector('.copy-from-section');
            if (!section) return;
            
            const input = section.querySelector('input');
            const button = section.querySelector('button');
            
            if (button && input) {
                button.addEventListener('click', () => {
                    const invoiceNumber = input.value.trim();
                    if (invoiceNumber) {
                        this.copyFromInvoice(invoiceNumber);
                    }
                });
            }
        },

        copyFromInvoice: function(invoiceNumber) {
            fetch(`/accounting/api/invoice/${invoiceNumber}/`, {
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // تعبئة الحقول
                    const fields = ['amount', 'description', 'ledger_account'];
                    fields.forEach(field => {
                        if (data[field]) {
                            const input = document.querySelector(`[name="${field}"]`);
                            if (input) {
                                input.value = data[field];
                                input.dispatchEvent(new Event('change'));
                            }
                        }
                    });
                    this.showToast('تم نسخ البيانات من الفاتورة', 'success');
                } else {
                    this.showToast('لم يتم العثور على الفاتورة', 'error');
                }
            })
            .catch(() => {
                this.showToast('حدث خطأ في جلب البيانات', 'error');
            });
        },

        // ==================== 7. الحسابات السريعة ====================
        initQuickCalculator: function() {
            const panel = document.createElement('div');
            panel.className = 'quick-calc-panel';
            panel.innerHTML = `
                <div class="calc-header">
                    <h6><i class="bi bi-calculator"></i> الآلة الحاسبة</h6>
                    <button class="shortcuts-close" onclick="this.parentNode.parentNode.classList.remove('show')">&times;</button>
                </div>
                <div class="calc-display" id="calcDisplay">0</div>
                <div class="calc-grid">
                    <button class="calc-btn" data-value="7">7</button>
                    <button class="calc-btn" data-value="8">8</button>
                    <button class="calc-btn" data-value="9">9</button>
                    <button class="calc-btn operator" data-value="/">÷</button>
                    <button class="calc-btn" data-value="4">4</button>
                    <button class="calc-btn" data-value="5">5</button>
                    <button class="calc-btn" data-value="6">6</button>
                    <button class="calc-btn operator" data-value="*">×</button>
                    <button class="calc-btn" data-value="1">1</button>
                    <button class="calc-btn" data-value="2">2</button>
                    <button class="calc-btn" data-value="3">3</button>
                    <button class="calc-btn operator" data-value="-">-</button>
                    <button class="calc-btn" data-value="0">0</button>
                    <button class="calc-btn" data-value=".">.</button>
                    <button class="calc-btn operator" data-value="C">C</button>
                    <button class="calc-btn operator" data-value="+">+</button>
                    <button class="calc-btn equals" data-value="=">=</button>
                    <button class="calc-btn use-result" id="useCalcResult">استخدام الناتج</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            // معالجة الأزرار
            panel.querySelectorAll('.calc-btn').forEach(btn => {
                btn.addEventListener('click', () => this.handleCalcInput(btn.dataset.value));
            });
            
            // استخدام الناتج
            document.getElementById('useCalcResult')?.addEventListener('click', () => {
                const display = document.getElementById('calcDisplay');
                const amountInput = document.querySelector('[name="amount"]');
                if (display && amountInput) {
                    amountInput.value = display.textContent;
                    amountInput.dispatchEvent(new Event('input'));
                    panel.classList.remove('show');
                }
            });
        },

        toggleCalculator: function() {
            const panel = document.querySelector('.quick-calc-panel');
            if (panel) {
                panel.classList.toggle('show');
            }
        },

        handleCalcInput: function(value) {
            const display = document.getElementById('calcDisplay');
            if (!display) return;
            
            if (value === 'C') {
                this.state.calcValue = '0';
            } else if (value === '=') {
                try {
                    this.state.calcValue = eval(this.state.calcValue).toString();
                } catch {
                    this.state.calcValue = 'خطأ';
                }
            } else {
                if (this.state.calcValue === '0' && value !== '.') {
                    this.state.calcValue = value;
                } else {
                    this.state.calcValue += value;
                }
            }
            display.textContent = this.state.calcValue;
        },

        // ==================== 8. التذكيرات الذكية ====================
        initSmartReminders: function() {
            const container = document.querySelector('.reminders-container');
            if (!container) return;
            
            // تذكيرات مبنية على السياق
            const today = new Date();
            const reminders = [];
            
            // تذكير نهاية الشهر
            if (today.getDate() >= 25) {
                reminders.push({
                    icon: 'bi-calendar-event',
                    title: 'قرب نهاية الشهر',
                    text: 'تأكد من تسجيل جميع الإيرادات والمصروفات قبل نهاية الشهر'
                });
            }
            
            // تذكير الضريبة
            if ([3, 6, 9, 12].includes(today.getMonth() + 1) && today.getDate() >= 20) {
                reminders.push({
                    icon: 'bi-receipt',
                    title: 'موعد الإقرار الضريبي',
                    text: 'يقترب موعد تقديم الإقرار الضريبي الربع سنوي'
                });
            }
            
            reminders.forEach(reminder => {
                const el = document.createElement('div');
                el.className = 'smart-reminder';
                el.innerHTML = `
                    <div class="reminder-icon"><i class="${reminder.icon}"></i></div>
                    <div class="reminder-content">
                        <h6>${reminder.title}</h6>
                        <p>${reminder.text}</p>
                    </div>
                    <button class="reminder-dismiss"><i class="bi bi-x"></i></button>
                `;
                
                el.querySelector('.reminder-dismiss').addEventListener('click', () => el.remove());
                container.appendChild(el);
            });
        },

        // ==================== 9. سحب وإفلات المرفقات ====================
        initAttachments: function() {
            const dropZone = document.getElementById('attachmentsDropZone') || document.querySelector('.attachments-drop-zone');
            const fileInput = document.getElementById('attachmentFileInput');
            const listContainer = document.getElementById('attachmentsList') || document.querySelector('.attachments-list');
            
            if (!dropZone || !fileInput) {
                console.log('⚠️ منطقة رفع المرفقات غير موجودة');
                return;
            }
            
            // سحب وإفلات
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
            
            dropZone.addEventListener('dragenter', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
            
            dropZone.addEventListener('dragleave', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    // تعيين الملفات للـ input
                    const dt = new DataTransfer();
                    // أضف الملفات الموجودة مسبقاً
                    if (fileInput.files) {
                        Array.from(fileInput.files).forEach(f => dt.items.add(f));
                    }
                    Array.from(files).forEach(file => dt.items.add(file));
                    fileInput.files = dt.files;
                    this.displayFiles(fileInput.files, listContainer);
                }
            });
            
            // عند اختيار الملفات
            fileInput.addEventListener('change', () => {
                if (fileInput.files && fileInput.files.length > 0) {
                    this.displayFiles(fileInput.files, listContainer);
                }
            });
            
            console.log('✅ تم تهيئة منطقة رفع المرفقات بنجاح');
        },
        
        displayFiles: function(files, container) {
            if (!container) return;
            container.innerHTML = '';
            
            Array.from(files).forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'attachment-item';
                
                const icon = this.getFileIcon(file.type);
                const size = this.formatFileSize(file.size);
                
                item.innerHTML = `
                    <div class="attachment-icon"><i class="${icon}"></i></div>
                    <div class="attachment-info">
                        <div class="attachment-name">${file.name}</div>
                        <div class="attachment-size">${size}</div>
                    </div>
                    <button type="button" class="attachment-remove" data-index="${index}">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                
                container.appendChild(item);
            });
            
            // معالجة الحذف
            container.querySelectorAll('.attachment-remove').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = parseInt(e.currentTarget.dataset.index);
                    this.removeFile(idx);
                });
            });
        },
        
        removeFile: function(index) {
            const fileInput = document.getElementById('attachmentFileInput');
            const container = document.getElementById('attachmentsList');
            if (!fileInput) return;
            
            const dt = new DataTransfer();
            Array.from(fileInput.files).forEach((file, i) => {
                if (i !== index) dt.items.add(file);
            });
            fileInput.files = dt.files;
            this.displayFiles(fileInput.files, container);
        },

        getFileIcon: function(mimeType) {
            if (mimeType.includes('pdf')) return 'bi-file-pdf';
            if (mimeType.includes('image')) return 'bi-file-image';
            if (mimeType.includes('word')) return 'bi-file-word';
            if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'bi-file-excel';
            return 'bi-file-earmark';
        },

        formatFileSize: function(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / 1048576).toFixed(1) + ' MB';
        },

        // ==================== 10. التصدير والطباعة ====================
        initExportOptions: function() {
            const container = document.querySelector('.export-options');
            if (!container) return;
            
            container.innerHTML = `
                <button class="export-btn pdf" onclick="EntryFeatures.exportPDF()">
                    <i class="bi bi-file-pdf"></i> تصدير PDF
                </button>
                <button class="export-btn excel" onclick="EntryFeatures.exportExcel()">
                    <i class="bi bi-file-excel"></i> تصدير Excel
                </button>
                <button class="export-btn print" onclick="EntryFeatures.printForm()">
                    <i class="bi bi-printer"></i> طباعة
                </button>
            `;
        },

        exportPDF: function() {
            window.print(); // مؤقتاً حتى إضافة مكتبة PDF
        },

        exportExcel: function() {
            this.showToast('جاري التصدير...', 'info');
        },

        printForm: function() {
            window.print();
        },

        // ==================== 11. سجل التغييرات ====================
        initChangeHistory: function() {
            const panel = document.querySelector('.history-panel');
            if (!panel) return;
            
            // جلب السجل من الخادم
            fetch('/accounting/api/entry-history/', {
                headers: { 'X-CSRFToken': this.config.csrfToken }
            })
            .then(res => res.json())
            .then(data => {
                if (data.history && data.history.length) {
                    panel.innerHTML = data.history.map(item => `
                        <div class="history-item">
                            <div class="history-avatar"><i class="bi bi-person"></i></div>
                            <div class="history-content">
                                <div class="history-action">${item.action}</div>
                                <div class="history-time">${item.timestamp}</div>
                                ${item.changes ? `<div class="history-changes">${item.changes}</div>` : ''}
                            </div>
                        </div>
                    `).join('');
                }
            })
            .catch(() => {
                // التجاهل
            });
        },

        // ==================== 12. تنبيهات الحد الائتماني ====================
        initCreditAlerts: function() {
            // يتم التفعيل عند اختيار عميل/مورد
            const supplierSelect = document.querySelector('[name="supplier"]');
            if (!supplierSelect) return;
            
            supplierSelect.addEventListener('change', () => {
                const supplierId = supplierSelect.value;
                if (supplierId) {
                    this.checkCreditLimit(supplierId);
                }
            });
        },

        checkCreditLimit: function(supplierId) {
            fetch(`/accounting/api/supplier/${supplierId}/credit/`, {
                headers: { 'X-CSRFToken': this.config.csrfToken }
            })
            .then(res => res.json())
            .then(data => {
                if (data.exceeded) {
                    const alert = document.createElement('div');
                    alert.className = 'credit-alert';
                    alert.innerHTML = `
                        <div class="credit-alert-icon"><i class="bi bi-exclamation-triangle"></i></div>
                        <div class="credit-alert-content">
                            <h6>تحذير: تجاوز الحد الائتماني</h6>
                            <p>الرصيد الحالي: ${data.balance} | الحد المسموح: ${data.limit}</p>
                        </div>
                    `;
                    
                    const existing = document.querySelector('.credit-alert');
                    if (existing) existing.remove();
                    
                    supplierSelect.parentNode.insertAdjacentElement('afterend', alert);
                }
            })
            .catch(() => {});
        },

        // ==================== زر المساعدة ====================
        initHelpButton: function() {
            const fab = document.createElement('button');
            fab.className = 'help-fab';
            fab.innerHTML = '<i class="bi bi-question-lg"></i>';
            fab.title = 'مساعدة (اضغط ?)';
            fab.addEventListener('click', () => {
                document.querySelector('.shortcuts-overlay')?.classList.add('show');
                document.querySelector('.keyboard-shortcuts-panel')?.classList.add('show');
            });
            document.body.appendChild(fab);
        },

        // ==================== مراقبة التغييرات ====================
        watchFormChanges: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            form.querySelectorAll('input, select, textarea').forEach(input => {
                input.addEventListener('change', () => {
                    this.state.isDirty = true;
                });
                input.addEventListener('input', () => {
                    this.state.isDirty = true;
                });
            });
            
            // تحذير قبل المغادرة
            window.addEventListener('beforeunload', (e) => {
                if (this.state.isDirty) {
                    e.preventDefault();
                    e.returnValue = '';
                }
            });
        },

        // ==================== الأدوات المساعدة ====================
        showToast: function(message, type = 'info') {
            const toast = document.createElement('div');
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 9999;
                animation: fadeInDown 0.3s ease;
            `;
            
            const colors = {
                success: '#10b981',
                error: '#ef4444',
                warning: '#f59e0b',
                info: '#3b82f6'
            };
            toast.style.background = colors[type] || colors.info;
            toast.textContent = message;
            
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        },

        // ==================== الميزات الجديدة المحسّنة ====================
        
        // 1. بانر استعادة المسودة التلقائي
        initDraftRestoreBanner: function() {
            const storageKey = `entry_draft_${this.config.entryType}`;
            const saved = localStorage.getItem(storageKey);
            
            if (saved) {
                const { data, timestamp } = JSON.parse(saved);
                const age = Date.now() - timestamp;
                
                // عرض البانر إذا كان أقل من ساعة
                if (age < 3600000) {
                    const banner = document.createElement('div');
                    banner.className = 'draft-restore-banner';
                    banner.innerHTML = `
                        <div class="draft-banner-content">
                            <i class="bi bi-info-circle-fill"></i>
                            <span>وجدنا مسودة محفوظة منذ ${Math.round(age / 60000)} دقيقة</span>
                            <div class="draft-banner-actions">
                                <button type="button" class="btn btn-sm btn-primary" onclick="EntryFeatures.restoreDraftFromBanner()">
                                    <i class="bi bi-arrow-clockwise"></i> استعادة
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="EntryFeatures.dismissDraftBanner()">
                                    تجاهل
                                </button>
                            </div>
                        </div>
                    `;
                    
                    const container = document.querySelector('.entry-form-enhanced');
                    if (container) {
                        container.insertBefore(banner, container.firstChild);
                    }
                }
            }
        },

        restoreDraftFromBanner: function() {
            this.restoreDraft();
            this.dismissDraftBanner();
            this.showToast('تم استعادة المسودة بنجاح', 'success');
        },

        dismissDraftBanner: function() {
            const banner = document.querySelector('.draft-restore-banner');
            if (banner) {
                banner.style.opacity = '0';
                setTimeout(() => banner.remove(), 300);
            }
            // حذف المسودة
            const storageKey = `entry_draft_${this.config.entryType}`;
            localStorage.removeItem(storageKey);
        },

        // 2. تذكر آخر الاختيارات
        initLastChoicesMemory: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            const storageKey = `last_choices_${this.config.entryType}`;
            const saved = localStorage.getItem(storageKey);
            
            if (saved) {
                const choices = JSON.parse(saved);
                const fields = ['ledger_account', 'financial_analysis_1', 'financial_analysis_2', 'cost_center', 'supplier'];
                
                fields.forEach(field => {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input && choices[field] && !input.value) {
                        input.value = choices[field];
                        // إضافة مؤشر بصري
                        const label = input.closest('.col-md-6, .col-md-12')?.querySelector('.form-label');
                        if (label && !label.querySelector('.remembered-badge')) {
                            const badge = document.createElement('span');
                            badge.className = 'remembered-badge';
                            badge.innerHTML = '<i class="bi bi-clock-history"></i> آخر اختيار';
                            label.appendChild(badge);
                        }
                    }
                });
            }
            
            // حفظ الاختيارات عند التغيير
            const fields = ['ledger_account', 'financial_analysis_1', 'financial_analysis_2', 'cost_center', 'supplier'];
            fields.forEach(field => {
                const input = form.querySelector(`[name="${field}"]`);
                if (input) {
                    input.addEventListener('change', () => {
                        const choices = JSON.parse(localStorage.getItem(storageKey) || '{}');
                        choices[field] = input.value;
                        localStorage.setItem(storageKey, JSON.stringify(choices));
                    });
                }
            });
        },

        // 3. التحقق الذكي من الحسابات
        initAccountValidation: function() {
            const accountSelect = document.querySelector('[name="ledger_account"]');
            if (!accountSelect) return;
            
            accountSelect.addEventListener('change', (e) => {
                const selectedOption = e.target.options[e.target.selectedIndex];
                const accountCode = selectedOption.text.split(' - ')[0];
                
                // تحذير بسيط للحسابات غير المناسبة
                let warning = null;
                
                if (this.config.entryType === 'revenue') {
                    // للإيرادات: تحذير إذا كان الحساب يبدأ برقم يدل على مصروف
                    if (accountCode.startsWith('4') || accountCode.startsWith('5')) {
                        warning = 'تنبيه: هذا الحساب قد يكون للمصروفات وليس الإيرادات';
                    }
                } else if (this.config.entryType === 'expense') {
                    // للمصروفات: تحذير إذا كان الحساب يبدأ برقم يدل على إيراد
                    if (accountCode.startsWith('3')) {
                        warning = 'تنبيه: هذا الحساب قد يكون للإيرادات وليس المصروفات';
                    }
                }
                
                if (warning) {
                    const warningDiv = document.createElement('div');
                    warningDiv.className = 'account-warning';
                    warningDiv.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${warning}`;
                    
                    const existingWarning = accountSelect.parentElement.querySelector('.account-warning');
                    if (existingWarning) existingWarning.remove();
                    
                    accountSelect.parentElement.appendChild(warningDiv);
                    setTimeout(() => warningDiv.remove(), 5000);
                }
            });
        },

        // 4. كشف التكرار قبل الحفظ
        initDuplicateDetection: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            form.addEventListener('submit', async (e) => {
                // التحقق من التكرار فقط عند الحفظ النهائي (ليس المسودة)
                if (e.submitter && e.submitter.classList.contains('btn-outline-primary')) {
                    return; // زر المسودة - لا داعي للتحقق
                }
                
                e.preventDefault();
                
                const formData = new FormData(form);
                formData.append('check_duplicate', 'true');
                
                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.duplicate_found) {
                        const confirmed = confirm(data.message + '\n\nهل تريد المتابعة والحفظ على أي حال؟');
                        if (!confirmed) return;
                    }
                    
                    // المتابعة بالحفظ
                    formData.delete('check_duplicate');
                    form.submit();
                    
                } catch (error) {
                    // في حالة الخطأ، متابعة الحفظ العادي
                    form.submit();
                }
            });
        },

        // 5. إدارة القوالب المحسّنة
        initTemplateManagement: function() {
            const list = document.querySelector('.templates-list');
            if (!list) return;
            
            // إضافة أزرار تعديل وحذف للقوالب المخصصة
            const templates = JSON.parse(localStorage.getItem('entry_templates') || '[]');
            
            document.querySelectorAll('.template-btn').forEach((btn, index) => {
                // تخطي القوالب الافتراضية (أول 3)
                if (index < 3) return;
                
                const template = templates[index - 3];
                if (!template) return;
                
                // إضافة أيقونة الحذف
                const deleteBtn = document.createElement('span');
                deleteBtn.className = 'template-delete-btn';
                deleteBtn.innerHTML = '<i class="bi bi-x-circle"></i>';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    if (confirm(`هل تريد حذف القالب "${template.name}"؟`)) {
                        templates.splice(index - 3, 1);
                        localStorage.setItem('entry_templates', JSON.stringify(templates));
                        location.reload();
                    }
                };
                btn.appendChild(deleteBtn);
            });
        },

        // 6. نسخ من آخر قيد مشابه
        initRecentEntriesCopy: function() {
            const section = document.querySelector('.copy-from-section');
            if (!section) return;
            
            // إضافة قسم آخر القيود
            const recentSection = document.createElement('div');
            recentSection.className = 'recent-entries-section';
            recentSection.innerHTML = `
                <div class="recent-header">
                    <i class="bi bi-clock-history"></i>
                    <span>آخر القيود المشابهة</span>
                </div>
                <div class="recent-entries-list">
                    <div class="loading-spinner">جاري التحميل...</div>
                </div>
            `;
            
            section.parentElement.insertBefore(recentSection, section.nextSibling);
            
            // جلب آخر القيود
            this.loadRecentEntries();
        },

        loadRecentEntries: async function() {
            const list = document.querySelector('.recent-entries-list');
            if (!list) return;
            
            try {
                const response = await fetch(`/accounting/entries/recent/?type=${this.config.entryType}&limit=5`);
                const data = await response.json();
                
                if (data.entries && data.entries.length > 0) {
                    list.innerHTML = data.entries.map(entry => `
                        <div class="recent-entry-item" onclick="EntryFeatures.copyFromRecentEntry(${JSON.stringify(entry).replace(/"/g, '&quot;')})">
                            <div class="recent-entry-header">
                                <span class="recent-entry-date">${entry.date}</span>
                                <span class="recent-entry-amount">${parseFloat(entry.amount).toFixed(2)} ج.م</span>
                            </div>
                            <div class="recent-entry-desc">${entry.description}</div>
                            <div class="recent-entry-account">${entry.ledger_account_name}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="no-recent-entries">لا توجد قيود سابقة</div>';
                }
            } catch (error) {
                list.innerHTML = '<div class="error-message">خطأ في تحميل القيود</div>';
            }
        },

        copyFromRecentEntry: function(entry) {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            // ملء الحقول
            const fields = {
                'amount': entry.amount,
                'description': entry.description,
                'ledger_account': entry.ledger_account,
                'financial_analysis_1': entry.financial_analysis_1,
                'financial_analysis_2': entry.financial_analysis_2,
                'cost_center': entry.cost_center,
                'supplier': entry.supplier
            };
            
            Object.keys(fields).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input && fields[key]) {
                    input.value = fields[key];
                    input.dispatchEvent(new Event('change'));
                }
            });
            
            this.showToast('تم نسخ البيانات من القيد السابق', 'success');
        },

        // 7. معاينة المرفقات المحسّنة
        initAttachmentsPreview: function() {
            const dropZone = document.querySelector('.attachments-drop-zone');
            const listContainer = document.querySelector('.attachments-list');
            if (!dropZone || !listContainer) return;
            
            // تحسين عرض المرفقات
            dropZone.addEventListener('change', (e) => {
                if (e.target.type === 'file') {
                    this.displayAttachmentPreviews(e.target.files, listContainer);
                }
            });
        },

        displayAttachmentPreviews: function(files, container) {
            container.innerHTML = '';
            const maxSize = 10 * 1024 * 1024; // 10MB
            
            Array.from(files).forEach((file, index) => {
                const sizeExceeded = file.size > maxSize;
                const preview = document.createElement('div');
                preview.className = `attachment-preview ${sizeExceeded ? 'size-exceeded' : ''}`;
                
                const icon = this.getFileIcon(file.type);
                const size = this.formatFileSize(file.size);
                
                preview.innerHTML = `
                    <div class="attachment-icon">${icon}</div>
                    <div class="attachment-info">
                        <div class="attachment-name">${file.name}</div>
                        <div class="attachment-meta">
                            <span class="attachment-size">${size}</span>
                            <span class="attachment-type">${file.type || 'غير معروف'}</span>
                        </div>
                        ${sizeExceeded ? '<div class="attachment-error">الحجم يتجاوز الحد الأقصى (10MB)</div>' : ''}
                    </div>
                    <button type="button" class="attachment-remove" onclick="EntryFeatures.removeAttachment(${index})">
                        <i class="bi bi-x-circle"></i>
                    </button>
                `;
                
                container.appendChild(preview);
            });
        },

        getFileIcon: function(mimeType) {
            if (mimeType.startsWith('image/')) return '<i class="bi bi-file-image"></i>';
            if (mimeType.includes('pdf')) return '<i class="bi bi-file-pdf"></i>';
            if (mimeType.includes('word')) return '<i class="bi bi-file-word"></i>';
            if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return '<i class="bi bi-file-excel"></i>';
            return '<i class="bi bi-file-earmark"></i>';
        },

        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 بايت';
            const k = 1024;
            const sizes = ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
        },

        removeAttachment: function(index) {
            const input = document.querySelector('.attachments-drop-zone input[type="file"]');
            if (input && input.files) {
                const dt = new DataTransfer();
                Array.from(input.files).forEach((file, i) => {
                    if (i !== index) dt.items.add(file);
                });
                input.files = dt.files;
                input.dispatchEvent(new Event('change'));
            }
        },

        // 8. اختصارات لوحة المفاتيح المحسّنة
        initEnhancedKeyboardShortcuts: function() {
            const form = document.getElementById('entryForm');
            if (!form) return;
            
            document.addEventListener('keydown', (e) => {
                // Ctrl+S: حفظ كمسودة
                if (e.ctrlKey && e.key === 's') {
                    e.preventDefault();
                    this.performAutosave();
                    this.showToast('تم حفظ المسودة', 'success');
                }
                
                // Ctrl+Enter: حفظ القيد
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    form.submit();
                }
                
                // Escape: إلغاء
                if (e.key === 'Escape') {
                    if (confirm('هل تريد إلغاء التعديلات والعودة؟')) {
                        window.location.href = '/accounting/entries/';
                    }
                }
            });
            
            // Enter للتنقل بين الحقول
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach((input, index) => {
                if (input.tagName === 'TEXTAREA') return; // تخطي textarea
                
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
                        e.preventDefault();
                        const nextInput = inputs[index + 1];
                        if (nextInput) {
                            nextInput.focus();
                        }
                    }
                });
            });
        }
    };

    // تصدير الوحدة
    window.EntryFeatures = EntryFeatures;
    
    // التهيئة التلقائية عند تحميل الصفحة
    document.addEventListener('DOMContentLoaded', function() {
        // تحقق من وجود النموذج
        if (document.getElementById('entryForm')) {
            EntryFeatures.init();
        }
    });

})();
