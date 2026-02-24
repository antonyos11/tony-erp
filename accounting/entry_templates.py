"""
قوالب القيود المحاسبية الجاهزة
Accounting Entry Templates
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class EntryTemplate(models.Model):
    """قالب قيد محاسبي"""
    
    name = models.CharField('اسم القالب', max_length=200)
    description = models.TextField('الوصف', blank=True)
    template_type = models.CharField('نوع القالب', max_length=50, choices=[
        ('revenue', 'إيراد'),
        ('expense', 'مصروف'),
        ('journal', 'قيد يومي'),
        ('adjustment', 'قيد تسوية'),
        ('opening', 'قيد افتتاحي'),
        ('closing', 'قيد ختامي'),
    ])
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    is_public = models.BooleanField('عام (متاح للجميع)', default=False)
    usage_count = models.IntegerField('عدد مرات الاستخدام', default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قالب قيد محاسبي'
        verbose_name_plural = 'قوالب القيود المحاسبية'
        ordering = ['-usage_count', '-created_at']
    
    def __str__(self):
        return self.name
    
    def use_template(self):
        """زيادة عداد الاستخدام"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class EntryTemplateItem(models.Model):
    """بند في قالب القيد"""
    
    template = models.ForeignKey(EntryTemplate, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey('accounting.Account', on_delete=models.CASCADE, verbose_name='الحساب')
    
    debit_percentage = models.DecimalField('نسبة مدين', max_digits=5, decimal_places=2, default=0)
    credit_percentage = models.DecimalField('نسبة دائن', max_digits=5, decimal_places=2, default=0)
    
    description = models.CharField('البيان', max_length=500, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    
    order = models.IntegerField('الترتيب', default=0)
    
    class Meta:
        verbose_name = 'بند القالب'
        verbose_name_plural = 'بنود القالب'
        ordering = ['order']
    
    def __str__(self):
        return f'{self.template.name} - {self.account.name}'


# قوالب جاهزة (يتم إنشاؤها عند التنفيذ الأولي)
PREDEFINED_TEMPLATES = [
    {
        'name': 'قيد بيع نقدي',
        'description': 'قيد قياسي لمبيعات نقدية',
        'template_type': 'revenue',
        'items': [
            {'account_code': '1101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'النقدية'},
            {'account_code': '4101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'المبيعات'},
        ]
    },
    {
        'name': 'قيد بيع آجل',
        'description': 'قيد قياسي لمبيعات آجلة',
        'template_type': 'revenue',
        'items': [
            {'account_code': '1201', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'العملاء'},
            {'account_code': '4101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'المبيعات'},
        ]
    },
    {
        'name': 'قيد شراء نقدي',
        'description': 'قيد قياسي لمشتريات نقدية',
        'template_type': 'expense',
        'items': [
            {'account_code': '5101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'المشتريات'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد شراء آجل',
        'description': 'قيد قياسي لمشتريات آجلة',
        'template_type': 'expense',
        'items': [
            {'account_code': '5101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'المشتريات'},
            {'account_code': '2101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'الموردون'},
        ]
    },
    {
        'name': 'قيد دفع رواتب',
        'description': 'قيد قياسي لدفع رواتب الموظفين',
        'template_type': 'expense',
        'items': [
            {'account_code': '5201', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'مصروف الرواتب'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد إيجار',
        'description': 'قيد قياسي لدفع إيجار',
        'template_type': 'expense',
        'items': [
            {'account_code': '5202', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'مصروف الإيجار'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد كهرباء وماء',
        'description': 'قيد قياسي للمرافق',
        'template_type': 'expense',
        'items': [
            {'account_code': '5203', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'مصروف الكهرباء والماء'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد تحصيل من عميل',
        'description': 'قيد قياسي لتحصيل مبالغ من العملاء',
        'template_type': 'journal',
        'items': [
            {'account_code': '1101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'النقدية'},
            {'account_code': '1201', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'العملاء'},
        ]
    },
    {
        'name': 'قيد دفع لمورد',
        'description': 'قيد قياسي لدفع مستحقات الموردين',
        'template_type': 'journal',
        'items': [
            {'account_code': '2101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'الموردون'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد إهلاك أصول',
        'description': 'قيد شهري لإهلاك الأصول الثابتة',
        'template_type': 'adjustment',
        'items': [
            {'account_code': '5301', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'مصروف الإهلاك'},
            {'account_code': '1301', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'مجمع الإهلاك'},
        ]
    },
    {
        'name': 'قيد مصروفات مستحقة',
        'description': 'قيد تسوية للمصروفات المستحقة',
        'template_type': 'adjustment',
        'items': [
            {'account_code': '5999', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'مصروفات متنوعة'},
            {'account_code': '2201', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'مصروفات مستحقة'},
        ]
    },
    {
        'name': 'قيد إيرادات مقدمة',
        'description': 'قيد تسوية للإيرادات المقدمة',
        'template_type': 'adjustment',
        'items': [
            {'account_code': '1101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'النقدية'},
            {'account_code': '2202', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'إيرادات مقدمة'},
        ]
    },
    {
        'name': 'قيد بنك - إيداع',
        'description': 'قيد إيداع نقدية في البنك',
        'template_type': 'journal',
        'items': [
            {'account_code': '1102', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'البنك'},
            {'account_code': '1101', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'النقدية'},
        ]
    },
    {
        'name': 'قيد بنك - سحب',
        'description': 'قيد سحب نقدية من البنك',
        'template_type': 'journal',
        'items': [
            {'account_code': '1101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'النقدية'},
            {'account_code': '1102', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'البنك'},
        ]
    },
    {
        'name': 'قيد خصم مكتسب',
        'description': 'قيد لخصم تم الحصول عليه من المورد',
        'template_type': 'revenue',
        'items': [
            {'account_code': '2101', 'debit_percentage': 100, 'credit_percentage': 0, 'description': 'الموردون'},
            {'account_code': '4201', 'debit_percentage': 0, 'credit_percentage': 100, 'description': 'خصم مكتسب'},
        ]
    },
]


def create_predefined_templates():
    """إنشاء القوالب الجاهزة"""
    from accounting.models import Account
    
    for template_data in PREDEFINED_TEMPLATES:
        # إنشاء القالب
        template, created = EntryTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults={
                'description': template_data['description'],
                'template_type': template_data['template_type'],
                'is_public': True
            }
        )
        
        if created:
            # إضافة البنود
            for idx, item_data in enumerate(template_data['items']):
                try:
                    account = Account.objects.get(code=item_data['account_code'])
                    EntryTemplateItem.objects.create(
                        template=template,
                        account=account,
                        debit_percentage=item_data['debit_percentage'],
                        credit_percentage=item_data['credit_percentage'],
                        description=item_data['description'],
                        order=idx
                    )
                except Account.DoesNotExist:
                    print(f"الحساب {item_data['account_code']} غير موجود")
