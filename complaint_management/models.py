from django.db import models
from django.contrib.auth.models import User


class Complaint(models.Model):
    """الشكوى"""
    complaint_number = models.CharField('رقم الشكوى', max_length=100, unique=True)
    customer = models.ForeignKey('partners.Customer', on_delete=models.CASCADE, related_name='complaints')
    
    channel = models.CharField('قناة الشكوى', max_length=20, choices=[
        ('phone', 'هاتف'), ('email', 'بريد'), ('website', 'موقع'), ('social_media', 'وسائل تواصل'),
        ('in_person', 'شخصياً'), ('mobile_app', 'تطبيق')
    ])
    category = models.CharField('التصنيف', max_length=50, choices=[
        ('product_quality', 'جودة منتج'), ('service_quality', 'جودة خدمة'), 
        ('delivery', 'توصيل'), ('pricing', 'تسعير'), ('staff_behavior', 'سلوك موظفين'), ('other', 'أخرى')
    ])
    
    priority = models.CharField('الأولوية', max_length=20, choices=[
        ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'عالية'), ('critical', 'حرجة')
    ], default='medium')
    
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('open', 'مفتوحة'), ('in_progress', 'قيد المعالجة'), ('resolved', 'محلولة'),
        ('closed', 'مغلقة'), ('escalated', 'مصعَّدة')
    ], default='open')
    
    # SLA
    received_at = models.DateTimeField('وقت الاستلام', auto_now_add=True)
    response_deadline = models.DateTimeField('الموعد النهائي للرد')
    resolution_deadline = models.DateTimeField('الموعد النهائي للحل')
    
    first_response_at = models.DateTimeField('أول رد', null=True, blank=True)
    resolved_at = models.DateTimeField('تاريخ الحل', null=True, blank=True)
    closed_at = models.DateTimeField('تاريخ الإغلاق', null=True, blank=True)
    
    # المعالجة
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_complaints')
    resolution = models.TextField('الحل', blank=True)
    
    # رضا العميل
    customer_satisfaction_rating = models.IntegerField('تقييم رضا العميل', null=True, blank=True,
                                                       help_text='من 1 إلى 5')
    customer_feedback = models.TextField('تعليق العميل', blank=True)
    
    # تحليل السبب الجذري
    root_cause = models.TextField('السبب الجذري', blank=True)
    corrective_action = models.TextField('الإجراء التصحيحي', blank=True)
    preventive_action = models.TextField('الإجراء الوقائي', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'شكوى'
        verbose_name_plural = 'الشكاوى'
        ordering = ['-received_at']
    
    def __str__(self):
        return f"{self.complaint_number} - {self.customer.name}"


class ImprovementInitiative(models.Model):
    """مبادرة تحسين"""
    title = models.CharField('العنوان', max_length=200)
    description = models.TextField('الوصف')
    
    initiative_type = models.CharField('نوع المبادرة', max_length=30, choices=[
        ('process_improvement', 'تحسين عملية'), ('quality_improvement', 'تحسين جودة'),
        ('cost_reduction', 'خفض تكلفة'), ('customer_satisfaction', 'رضا العميل'),
        ('efficiency', 'كفاءة')
    ])
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('proposed', 'مقترحة'), ('approved', 'معتمدة'), ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة'), ('cancelled', 'ملغاة')
    ], default='proposed')
    
    # الأهداف
    current_state = models.TextField('الحالة الحالية')
    target_state = models.TextField('الحالة المستهدفة')
    expected_benefits = models.TextField('الفوائد المتوقعة')
    
    # التنفيذ
    start_date = models.DateField('تاريخ البدء', null=True, blank=True)
    target_completion_date = models.DateField('تاريخ الانتهاء المستهدف')
    actual_completion_date = models.DateField('تاريخ الانتهاء الفعلي', null=True, blank=True)
    
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='improvement_initiatives')
    team_members = models.ManyToManyField(User, related_name='participating_initiatives', blank=True)
    
    # النتائج
    results_achieved = models.TextField('النتائج المحققة', blank=True)
    lessons_learned = models.TextField('الدروس المستفادة', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'مبادرة تحسين'
        verbose_name_plural = 'مبادرات التحسين'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
