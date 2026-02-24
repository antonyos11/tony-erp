// ملف JavaScript للمساعدة السياقية
// Contextual Help JavaScript

class ContextualHelp {
    constructor() {
        this.helpData = {};
        this.currentContext = null;
        this.init();
    }
    
    init() {
        console.log('Initializing Contextual Help System...');
        
        // تحميل بيانات المساعدة
        this.loadHelpData();
        
        // إضافة أيقونات المساعدة
        setTimeout(() => this.addHelpIcons(), 500);
        
        // إضافة زر المساعدة العائم
        this.addFloatingButton();
        
        // معالجة الأحداث
        this.bindEvents();
        
        console.log('Contextual Help System initialized');
    }
    
    loadHelpData() {
        // تحميل من API
        fetch('/api/help/tooltips/')
            .then(response => response.json())
            .then(data => {
                this.helpData = data;
                console.log('Help data loaded:', Object.keys(data).length, 'items');
            })
            .catch(error => {
                console.warn('Could not load help data from API, using defaults');
                // استخدام بيانات افتراضية
                this.useDefaultHelpData();
            });
    }
    
    useDefaultHelpData() {
        // بيانات مساعدة افتراضية
        this.helpData = {
            'customer': {
                title: 'اختيار العميل',
                content: 'اختر العميل من القائمة أو ابحث عنه. يمكنك إضافة عميل جديد بالضغط على زر "+".',
                tips: ['استخدم Ctrl+F للبحث السريع', 'العملاء الأكثر تعاملاً يظهرون في الأعلى']
            },
            'discount': {
                title: 'الخصم',
                content: 'أدخل قيمة الخصم بالريال أو النسبة المئوية.',
                tips: ['اضغط F8 لآلة حاسبة الخصم']
            }
        };
    }
    
    addHelpIcons() {
        // البحث عن جميع الحقول
        const fields = document.querySelectorAll('input:not([type="hidden"]), select, textarea');
        
        fields.forEach(field => {
            // تجاهل الحقول التي تحتوي بالفعل على أيقونة مساعدة
            if (field.parentElement?.querySelector('.help-icon')) {
                return;
            }
            
            const fieldId = field.id || field.name;
            const fieldLabel = this.getFieldLabel(field);
            
            // إضافة أيقونة مساعدة
            const icon = document.createElement('i');
            icon.className = 'fas fa-question-circle help-icon';
            icon.dataset.fieldId = fieldId;
            icon.dataset.fieldLabel = fieldLabel;
            icon.title = 'اضغط للمساعدة (أو F1)';
            
            // إدراج الأيقونة
            if (field.parentElement) {
                const wrapper = field.parentElement;
                
                // إذا كان الحقل داخل div.form-group
                if (wrapper.classList.contains('form-group') || wrapper.classList.contains('mb-3')) {
                    const label = wrapper.querySelector('label');
                    if (label && !label.querySelector('.help-icon')) {
                        label.appendChild(icon);
                    }
                } else {
                    field.insertAdjacentElement('afterend', icon);
                }
            }
        });
        
        console.log('Help icons added to', fields.length, 'fields');
    }
    
    getFieldLabel(field) {
        // البحث عن label المرتبط
        let label = null;
        
        if (field.id) {
            label = document.querySelector(`label[for="${field.id}"]`);
        }
        
        if (!label && field.parentElement) {
            label = field.parentElement.querySelector('label');
        }
        
        return label ? label.textContent.trim() : field.name;
    }
    
    addFloatingButton() {
        // إنشاء زر المساعدة العائم
        const button = document.createElement('button');
        button.className = 'floating-help-button';
        button.innerHTML = '<i class="fas fa-question"></i>';
        button.title = 'المساعدة (F1)';
        // تأكيد الموقع بعيداً عن زر الشات حتى لو وُجد CSS آخر
        button.style.top = '80px';
        button.style.left = '20px';
        button.style.bottom = 'auto';
        button.style.right = 'auto';
        button.onclick = () => this.showGeneralHelp();
        
        document.body.appendChild(button);
    }
    
    bindEvents() {
        // النقر على أيقونة المساعدة
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('help-icon') || 
                e.target.parentElement?.classList.contains('help-icon')) {
                const icon = e.target.classList.contains('help-icon') ? e.target : e.target.parentElement;
                const fieldId = icon.dataset.fieldId;
                const fieldLabel = icon.dataset.fieldLabel;
                this.showHelp(fieldId, fieldLabel);
            }
        });
        
        // F1 للمساعدة السياقية
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F1') {
                e.preventDefault();
                const activeElement = document.activeElement;
                
                if (activeElement && (activeElement.tagName === 'INPUT' || 
                    activeElement.tagName === 'SELECT' || 
                    activeElement.tagName === 'TEXTAREA')) {
                    const fieldId = activeElement.id || activeElement.name;
                    const fieldLabel = this.getFieldLabel(activeElement);
                    this.showHelp(fieldId, fieldLabel);
                } else {
                    this.showGeneralHelp();
                }
            }
        });
        
        // Tooltip عند hover
        document.addEventListener('mouseover', (e) => {
            if (e.target.classList.contains('help-icon')) {
                const fieldId = e.target.dataset.fieldId;
                if (this.helpData[fieldId]) {
                    e.target.title = this.helpData[fieldId].title;
                }
            }
        });
    }
    
    showHelp(fieldId, fieldLabel) {
        console.log('Showing help for:', fieldId);
        
        let help = this.helpData[fieldId];
        
        // إذا لم تكن هناك مساعدة محددة، استخدم مساعدة عامة
        if (!help) {
            help = {
                title: fieldLabel || 'مساعدة',
                content: 'هذا الحقل يحتاج إلى معلومات صحيحة. يرجى التأكد من البيانات المدخلة.',
                tips: ['استخدم Tab للانتقال للحقل التالي', 'البيانات المطلوبة مميزة بـ *']
            };
        }
        
        let content = `
            <div class="contextual-help">
                <h5><i class="fas fa-info-circle"></i> ${help.title}</h5>
                <p>${help.content}</p>
        `;
        
        if (help.tips && help.tips.length > 0) {
            content += '<div class="help-tips"><strong><i class="fas fa-lightbulb"></i> نصائح مفيدة:</strong><ul>';
            help.tips.forEach(tip => {
                content += `<li>${tip}</li>`;
            });
            content += '</ul></div>';
        }
        
        if (help.html) {
            content += `<div class="help-additional">${help.html}</div>`;
        }
        
        if (help.video_url) {
            content += `
                <div class="help-video">
                    <iframe src="${help.video_url}" allowfullscreen></iframe>
                </div>
            `;
        }
        
        content += '</div>';
        
        this.showModal('المساعدة - ' + help.title, content);
    }
    
    showGeneralHelp() {
        const content = `
            <div class="general-help">
                <h5><i class="fas fa-book"></i> المساعدة العامة</h5>
                
                <h6>اختصارات لوحة المفاتيح:</h6>
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th style="width: 30%">الاختصار</th>
                            <th>الوظيفة</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><kbd>F1</kbd></td><td>عرض المساعدة السياقية</td></tr>
                        <tr><td><kbd>F3</kbd></td><td>البحث في الحسابات</td></tr>
                        <tr><td><kbd>F4</kbd></td><td>الآلة الحاسبة</td></tr>
                        <tr><td><kbd>F5</kbd></td><td>فاتورة جديدة</td></tr>
                        <tr><td><kbd>Ctrl + S</kbd></td><td>حفظ</td></tr>
                        <tr><td><kbd>Ctrl + F</kbd></td><td>بحث عام</td></tr>
                        <tr><td><kbd>Ctrl + P</kbd></td><td>طباعة</td></tr>
                        <tr><td><kbd>Tab</kbd></td><td>الانتقال للحقل التالي</td></tr>
                        <tr><td><kbd>Shift + Tab</kbd></td><td>العودة للحقل السابق</td></tr>
                        <tr><td><kbd>Esc</kbd></td><td>إلغاء / إغلاق</td></tr>
                    </tbody>
                </table>
                
                <div class="inline-help">
                    <i class="fas fa-info-circle"></i>
                    <strong>نصيحة:</strong> للحصول على مساعدة حول حقل معين، ضع المؤشر عليه واضغط <kbd>F1</kbd> أو انقر على أيقونة المساعدة 
                    <i class="fas fa-question-circle text-primary"></i>
                </div>
                
                <h6>الأسئلة الشائعة:</h6>
                <div class="faq-section">
                    <div class="faq-item">
                        <div class="faq-question" onclick="this.classList.toggle('active'); this.nextElementSibling.classList.toggle('show')">
                            <span>كيف أقوم بإنشاء فاتورة جديدة؟</span>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                        <div class="faq-answer">
                            اضغط على "فواتير" من القائمة الجانبية، ثم "فاتورة جديدة"، أو اضغط <kbd>F5</kbd> من أي مكان.
                        </div>
                    </div>
                    
                    <div class="faq-item">
                        <div class="faq-question" onclick="this.classList.toggle('active'); this.nextElementSibling.classList.toggle('show')">
                            <span>كيف أبحث عن عميل؟</span>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                        <div class="faq-answer">
                            في حقل العميل، ابدأ بكتابة الاسم أو رقم الهاتف، أو اضغط <kbd>F7</kbd> لفتح نافذة البحث المتقدم.
                        </div>
                    </div>
                    
                    <div class="faq-item">
                        <div class="faq-question" onclick="this.classList.toggle('active'); this.nextElementSibling.classList.toggle('show')">
                            <span>كيف أضيف خصماً على الفاتورة؟</span>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                        <div class="faq-answer">
                            يمكنك إضافة خصم على مستوى البند أو على الإجمالي. اضغط <kbd>F8</kbd> لفتح آلة حاسبة الخصم.
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.showModal('المساعدة العامة', content);
    }
    
    showModal(title, content) {
        // إنشاء modal إذا لم يكن موجوداً
        let modal = document.getElementById('helpModal');
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'helpModal';
            modal.className = 'modal fade';
            modal.setAttribute('tabindex', '-1');
            modal.innerHTML = `
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="helpModalTitle"></h5>
                            <button type="button" class="btn-close btn-close-white" id="helpModalCloseX" aria-label="إغلاق"></button>
                        </div>
                        <div class="modal-body" id="helpModalBody"></div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" id="helpModalCloseBtn">
                                <i class="fas fa-times"></i> إغلاق
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // ربط أحداث الإغلاق مباشرة
            document.getElementById('helpModalCloseX').onclick = () => this.closeModal();
            document.getElementById('helpModalCloseBtn').onclick = () => this.closeModal();
            
            // إغلاق بالنقر خارج النافذة
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }
        
        document.getElementById('helpModalTitle').innerHTML = title;
        document.getElementById('helpModalBody').innerHTML = content;
        
        // عرض modal - Simple direct approach
        modal.style.display = 'block';
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        
        // إضافة backdrop
        let backdrop = document.getElementById('helpModalBackdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'helpModalBackdrop';
            backdrop.className = 'modal-backdrop fade show';
            backdrop.style.zIndex = '1040';
            backdrop.onclick = () => this.closeModal();
            document.body.appendChild(backdrop);
        } else {
            backdrop.style.display = 'block';
        }
    }
    
    closeModal() {
        const modal = document.getElementById('helpModal');
        const backdrop = document.getElementById('helpModalBackdrop');
        
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
        if (backdrop) {
            backdrop.style.display = 'none';
        }
        document.body.classList.remove('modal-open');
    }
}

// تفعيل عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.contextualHelp = new ContextualHelp();
    console.log('Contextual Help ready!');
});
