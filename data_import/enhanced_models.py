"""
Advanced Data Import & Migration System
نظام استيراد وترحيل البيانات المتقدم

ترحيل سهل وبسيط لبيانات العملاء والموردين والمخزون من أي نظام قديم
"""

from django.db import models
from django.db.models import JSONField


class ImportTemplate(models.Model):
    """قوالب الاستيراد"""
    
    SOURCE_TYPE_CHOICES = [
        ('excel', 'Excel (XLSX/XLS)'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('sql', 'قاعدة بيانات SQL'),
        ('other_erp', 'نظام ERP آخر'),
    ]
    
    TARGET_MODEL_CHOICES = [
        ('customers', 'العملاء'),
        ('suppliers', 'الموردين'),
        ('products', 'المنتجات'),
        ('invoices', 'الفواتير'),
        ('accounts', 'الحسابات'),
        ('employees', 'الموظفين'),
    ]
    
    name = models.CharField('اسم القالب', max_length=200)
    source_type = models.CharField('نوع المصدر', max_length=20, choices=SOURCE_TYPE_CHOICES)
    target_model = models.CharField('النموذج المستهدف', max_length=50, choices=TARGET_MODEL_CHOICES)
    
    # تعيين الأعمدة
    column_mapping = models.JSONField('تعيين الأعمدة', default=dict)
    
    # قواعد التحويل
    transformation_rules = models.JSONField('قواعد التحويل', default=dict)
    
    # التحقق
    validation_rules = models.JSONField('قواعد التحقق', default=dict)
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'قالب استيراد'
        verbose_name_plural = 'قوالب الاستيراد'
    
    def __str__(self):
        return self.name


class ImportJob(models.Model):
    """مهام الاستيراد"""
    
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('processing', 'جاري المعالجة'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('partial', 'مكتمل جزئياً'),
    ]
    
    template = models.ForeignKey(ImportTemplate, on_delete=models.PROTECT, verbose_name='القالب')
    
    job_number = models.CharField('رقم المهمة', max_length=50, unique=True)
    source_file = models.FileField('ملف المصدر', upload_to='imports/')
    
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # إحصائيات
    total_records = models.IntegerField('إجمالي السجلات', default=0)
    successful_records = models.IntegerField('سجلات ناجحة', default=0)
    failed_records = models.IntegerField('سجلات فاشلة', default=0)
    
    # الأخطاء
    error_log = models.TextField('سجل الأخطاء', blank=True)
    
    started_at = models.DateTimeField('بدء المعالجة', null=True, blank=True)
    completed_at = models.DateTimeField('انتهاء المعالجة', null=True, blank=True)
    
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'مهمة استيراد'
        verbose_name_plural = 'مهام الاستيراد'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_number} - {self.status}"
