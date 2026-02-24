"""
نظام المساعدة السياقية
Contextual Help System
"""

from django.db import models


class HelpContent(models.Model):
    """محتوى المساعدة"""
    
    CONTEXT_TYPES = [
        ('form', 'نموذج'),
        ('field', 'حقل'),
        ('page', 'صفحة'),
        ('action', 'إجراء'),
        ('error', 'خطأ'),
    ]
    
    context_type = models.CharField(max_length=20, choices=CONTEXT_TYPES, verbose_name='نوع السياق')
    context_id = models.CharField(max_length=100, verbose_name='معرّف السياق')
    title = models.CharField(max_length=200, verbose_name='العنوان')
    content = models.TextField(verbose_name='المحتوى')
    content_html = models.TextField(blank=True, verbose_name='محتوى HTML')
    video_url = models.URLField(blank=True, verbose_name='رابط الفيديو')
    order = models.IntegerField(default=0, verbose_name='الترتيب')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'محتوى مساعدة'
        verbose_name_plural = 'محتويات المساعدة'
        ordering = ['order', 'title']
        unique_together = ['context_type', 'context_id']
    
    def __str__(self):
        return f"{self.get_context_type_display()} - {self.title}"


class ContextualHelpSystem:
    """نظام المساعدة السياقية"""
    
    # مساعدات مدمجة للحقول الشائعة
    BUILT_IN_HELPS = {
        # حقول المبيعات
        'invoice_customer': {
            'title': 'اختيار العميل',
            'content': 'اختر العميل من القائمة أو ابحث عنه. يمكنك إضافة عميل جديد بالضغط على زر "+".',
            'tips': [
                'استخدم Ctrl+F للبحث السريع',
                'العملاء الأكثر تعاملاً يظهرون في الأعلى',
            ]
        },
        'invoice_items': {
            'title': 'إضافة منتجات',
            'content': 'أضف المنتجات للفاتورة. يمكنك استخدام الباركود أو البحث بالاسم.',
            'tips': [
                'اضغط F6 لإضافة منتج سريع',
                'استخدم Tab للانتقال بين الحقول',
                'الأسعار تُحدّث تلقائياً',
            ]
        },
        'invoice_discount': {
            'title': 'الخصم',
            'content': 'أدخل قيمة الخصم بالج.م. يمكنك تطبيق خصم على كل بند أو على الإجمالي.',
            'tips': [
                'اضغط F8 لفتح آلة حاسبة الخصم',
                'الخصم الإجمالي يوزع نسبياً على البنود',
            ]
        },
        
        # حقول المحاسبة
        'entry_account': {
            'title': 'اختيار الحساب',
            'content': 'اختر الحساب المناسب من دليل الحسابات. استخدم البحث للوصول السريع.',
            'tips': [
                'اضغط F3 للبحث في الحسابات',
                'الحسابات مرتبة حسب النوع',
                'يمكنك عرض رصيد الحساب قبل الاختيار',
            ]
        },
        'entry_debit_credit': {
            'title': 'المدين والدائن',
            'content': 'أدخل المبلغ في عمود المدين أو الدائن. يجب أن يتساوى مجموع المدين مع الدائن.',
            'tips': [
                'استخدم Tab للانتقال بين الأعمدة',
                'الأرصدة تُحسب تلقائياً',
                'تحذير إذا لم يتوازن القيد',
            ]
        },
        
        # حقول المخزون
        'product_min_stock': {
            'title': 'الحد الأدنى للمخزون',
            'content': 'حدد الحد الأدنى الذي يجب تنبيهك عند الوصول إليه.',
            'tips': [
                'يُفضل أن يكون كافٍ لأسبوع واحد',
                'سيصلك تنبيه عند النفاذ',
            ]
        },
        'product_reorder_quantity': {
            'title': 'كمية إعادة الطلب',
            'content': 'الكمية التي يُنصح بطلبها عند الوصول للحد الأدنى.',
            'tips': [
                'احسبها بناءً على معدل الاستهلاك',
                'خذ في الاعتبار وقت التوريد',
            ]
        },
        
        # حقول المشتريات
        'purchase_expected_delivery': {
            'title': 'تاريخ التسليم المتوقع',
            'content': 'حدد التاريخ المتوقع لاستلام البضاعة.',
            'tips': [
                'سيصلك تنبيه قبل الموعد بيوم',
                'تنبيه آخر إذا تأخر التسليم',
            ]
        },
        'purchase_payment_terms': {
            'title': 'شروط الدفع',
            'content': 'حدد شروط الدفع المتفق عليها مع المورد.',
            'tips': [
                'مثال: نقدي، آجل 30 يوم، تقسيط',
                'تؤثر على تقارير الذمم',
            ]
        },
    }
    
    @classmethod
    def get_help(cls, context_type, context_id):
        """الحصول على المساعدة لسياق معين"""
        # البحث في قاعدة البيانات
        try:
            db_help = HelpContent.objects.get(
                context_type=context_type,
                context_id=context_id,
                is_active=True
            )
            return {
                'title': db_help.title,
                'content': db_help.content,
                'content_html': db_help.content_html,
                'video_url': db_help.video_url,
                'source': 'database'
            }
        except HelpContent.DoesNotExist:
            pass
        
        # البحث في المساعدات المدمجة
        if context_id in cls.BUILT_IN_HELPS:
            return {
                **cls.BUILT_IN_HELPS[context_id],
                'source': 'built-in'
            }
        
        return None
    
    @classmethod
    def get_field_help(cls, field_name):
        """مساعدة خاصة بحقل"""
        return cls.get_help('field', field_name)
    
    @classmethod
    def get_form_help(cls, form_name):
        """مساعدة خاصة بنموذج"""
        return cls.get_help('form', form_name)
    
    @classmethod
    def get_page_help(cls, page_name):
        """مساعدة خاصة بصفحة"""
        return cls.get_help('page', page_name)
    
    @classmethod
    def create_help_tooltips(cls):
        """إنشاء tooltips لجميع الحقول"""
        tooltips = {}
        
        for field_id, help_data in cls.BUILT_IN_HELPS.items():
            tooltips[field_id] = {
                'title': help_data['title'],
                'content': help_data['content'],
                'tips': help_data.get('tips', [])
            }
        
        # إضافة من قاعدة البيانات
        db_helps = HelpContent.objects.filter(
            context_type='field',
            is_active=True
        )
        
        for help_item in db_helps:
            tooltips[help_item.context_id] = {
                'title': help_item.title,
                'content': help_item.content,
                'html': help_item.content_html
            }
        
        return tooltips


# JavaScript للمساعدة السياقية
CONTEXTUAL_HELP_JS = """
class ContextualHelp {
    constructor() {
        this.helpData = {};
        this.init();
    }
    
    init() {
        // تحميل بيانات المساعدة
        this.loadHelpData();
        
        // إضافة أيقونات المساعدة
        this.addHelpIcons();
        
        // معالجة الأحداث
        this.bindEvents();
    }
    
    loadHelpData() {
        // تحميل من الخادم
        fetch('/api/help/tooltips/')
            .then(response => response.json())
            .then(data => {
                this.helpData = data;
            });
    }
    
    addHelpIcons() {
        // إضافة أيقونة مساعدة لكل حقل له مساعدة
        document.querySelectorAll('input, select, textarea').forEach(field => {
            const fieldId = field.id || field.name;
            
            if (this.helpData[fieldId]) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-question-circle help-icon';
                icon.dataset.fieldId = fieldId;
                icon.style.cursor = 'pointer';
                icon.style.marginLeft = '5px';
                icon.style.color = '#007bff';
                
                // إضافة بعد الحقل
                if (field.parentElement) {
                    field.parentElement.insertBefore(icon, field.nextSibling);
                }
            }
        });
    }
    
    bindEvents() {
        // عند النقر على أيقونة المساعدة
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('help-icon')) {
                const fieldId = e.target.dataset.fieldId;
                this.showHelp(fieldId);
            }
        });
        
        // عند التركيز على حقل (F1 للمساعدة)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F1') {
                e.preventDefault();
                const activeElement = document.activeElement;
                const fieldId = activeElement.id || activeElement.name;
                
                if (this.helpData[fieldId]) {
                    this.showHelp(fieldId);
                } else {
                    this.showGeneralHelp();
                }
            }
        });
    }
    
    showHelp(fieldId) {
        const help = this.helpData[fieldId];
        
        if (!help) return;
        
        let content = `
            <div class="contextual-help">
                <h5>${help.title}</h5>
                <p>${help.content}</p>
        `;
        
        if (help.tips && help.tips.length > 0) {
            content += '<div class="help-tips"><strong>نصائح:</strong><ul>';
            help.tips.forEach(tip => {
                content += `<li>${tip}</li>`;
            });
            content += '</ul></div>';
        }
        
        if (help.html) {
            content += help.html;
        }
        
        content += '</div>';
        
        // عرض في modal
        this.showModal('المساعدة', content);
    }
    
    showGeneralHelp() {
        const content = `
            <div class="general-help">
                <h5>مساعدة عامة</h5>
                <h6>اختصارات لوحة المفاتيح:</h6>
                <table class="table table-sm">
                    <tr><td><kbd>F1</kbd></td><td>المساعدة</td></tr>
                    <tr><td><kbd>Ctrl+S</kbd></td><td>حفظ</td></tr>
                    <tr><td><kbd>Ctrl+F</kbd></td><td>بحث</td></tr>
                    <tr><td><kbd>Tab</kbd></td><td>الحقل التالي</td></tr>
                    <tr><td><kbd>Esc</kbd></td><td>إلغاء</td></tr>
                </table>
                
                <p>للحصول على مساعدة حول حقل معين، ضع المؤشر عليه واضغط F1</p>
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
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="helpModalTitle"></h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body" id="helpModalBody"></div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">إغلاق</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        document.getElementById('helpModalTitle').textContent = title;
        document.getElementById('helpModalBody').innerHTML = content;
        
        $(modal).modal('show');
    }
}

// تفعيل عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.contextualHelp = new ContextualHelp();
});
"""
