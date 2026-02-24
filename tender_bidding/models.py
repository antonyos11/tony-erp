from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Tender(models.Model):
    """المناقصة"""
    TENDER_TYPES = [
        ('open', 'مفتوحة'),
        ('limited', 'محدودة'),
        ('prequalified', 'بقائمة مؤهلة مسبقاً'),
        ('request_for_proposal', 'طلب عروض (RFP)'),
        ('request_for_quotation', 'طلب أسعار (RFQ)'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('published', 'منشورة'),
        ('open', 'مفتوحة للتقديم'),
        ('closed', 'مغلقة'),
        ('under_evaluation', 'قيد التقييم'),
        ('awarded', 'تم الترسية'),
        ('cancelled', 'ملغاة'),
    ]
    
    DIRECTION_CHOICES = [
        ('incoming', 'واردة - نحن نقدم عطاء'),
        ('outgoing', 'صادرة - نحن نطلب عطاءات'),
    ]
    
    # معلومات أساسية
    reference_number = models.CharField('الرقم المرجعي', max_length=100, unique=True)
    title = models.CharField('العنوان', max_length=300)
    description = models.TextField('الوصف')
    direction = models.CharField('الاتجاه', max_length=20, choices=DIRECTION_CHOICES)
    tender_type = models.CharField('نوع المناقصة', max_length=50, choices=TENDER_TYPES)
    status = models.CharField('الحالة', max_length=30, choices=STATUS_CHOICES, default='draft')
    
    # الجهة
    issuing_organization = models.CharField('الجهة المصدرة', max_length=200, blank=True)
    contact_person = models.CharField('جهة الاتصال', max_length=200, blank=True)
    contact_email = models.EmailField('البريد الإلكتروني', blank=True)
    contact_phone = models.CharField('الهاتف', max_length=20, blank=True)
    
    # التواريخ
    published_date = models.DateField('تاريخ النشر', null=True, blank=True)
    submission_deadline = models.DateTimeField('الموعد النهائي للتقديم')
    opening_date = models.DateTimeField('تاريخ فتح المظاريف', null=True, blank=True)
    award_date = models.DateField('تاريخ الترسية', null=True, blank=True)
    
    # المتطلبات
    requirements = models.JSONField('المتطلبات', default=list)
    technical_specifications = models.TextField('المواصفات الفنية', blank=True)
    evaluation_criteria = models.JSONField('معايير التقييم', default=dict)
    
    # المالية
    estimated_value = models.DecimalField('القيمة التقديرية', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    budget_allocated = models.DecimalField('الميزانية المخصصة', max_digits=15, decimal_places=2, null=True, blank=True)
    performance_bond_percentage = models.DecimalField('نسبة ضمان الأداء %', max_digits=5, decimal_places=2, default=10)
    
    # المستندات
    documents_required = models.JSONField('المستندات المطلوبة', default=list)
    tender_document_url = models.URLField('رابط وثائق المناقصة', blank=True)
    
    # الفائز
    winning_bid = models.ForeignKey('Bid', on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='won_tenders', verbose_name='العطاء الفائز')
    award_amount = models.DecimalField('مبلغ الترسية', max_digits=15, decimal_places=2, null=True, blank=True)
    award_justification = models.TextField('مبرر الترسية', blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tenders_created')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مناقصة'
        verbose_name_plural = 'المناقصات'
        ordering = ['-submission_deadline']
        indexes = [
            models.Index(fields=['status', 'direction']),
            models.Index(fields=['submission_deadline']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class Bid(models.Model):
    """العطاء/العرض"""
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('submitted', 'مُقدَّم'),
        ('under_review', 'قيد المراجعة'),
        ('shortlisted', 'مُرشَّح'),
        ('accepted', 'مقبول'),
        ('rejected', 'مرفوض'),
        ('withdrawn', 'منسحب'),
    ]
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids', verbose_name='المناقصة')
    bidder_name = models.CharField('اسم مقدم العطاء', max_length=200)
    bidder_company = models.CharField('الشركة', max_length=200, blank=True)
    bidder_email = models.EmailField('البريد الإلكتروني', blank=True)
    bidder_phone = models.CharField('الهاتف', max_length=20, blank=True)
    
    # العطاء
    bid_amount = models.DecimalField('قيمة العطاء', max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField('العملة', max_length=10, default='EGP')
    validity_period_days = models.IntegerField('فترة صلاحية العطاء (أيام)', default=90)
    delivery_time_days = models.IntegerField('مدة التسليم (أيام)', null=True, blank=True)
    
    # التقييم
    status = models.CharField('الحالة', max_length=30, choices=STATUS_CHOICES, default='draft')
    technical_score = models.DecimalField('الدرجة الفنية', max_digits=5, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    financial_score = models.DecimalField('الدرجة المالية', max_digits=5, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    total_score = models.DecimalField('الدرجة الإجمالية', max_digits=5, decimal_places=2, null=True, blank=True,
                                     validators=[MinValueValidator(0), MaxValueValidator(100)])
    rank = models.IntegerField('الترتيب', null=True, blank=True)
    
    # المستندات المرفقة
    documents = models.JSONField('المستندات المرفقة', default=list)
    technical_proposal = models.TextField('العرض الفني', blank=True)
    commercial_proposal = models.TextField('العرض المالي', blank=True)
    
    # الضمانات
    bid_bond_amount = models.DecimalField('مبلغ ضمان العطاء', max_digits=15, decimal_places=2, null=True, blank=True)
    bid_bond_reference = models.CharField('رقم ضمان العطاء', max_length=100, blank=True)
    
    # التقييم والملاحظات
    evaluation_notes = models.TextField('ملاحظات التقييم', blank=True)
    rejection_reason = models.TextField('سبب الرفض', blank=True)
    
    submitted_at = models.DateTimeField('تاريخ التقديم', null=True, blank=True)
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='evaluated_bids', verbose_name='تم التقييم بواسطة')
    evaluated_at = models.DateTimeField('تاريخ التقييم', null=True, blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'عطاء'
        verbose_name_plural = 'العطاءات'
        ordering = ['-total_score', 'bid_amount']
        indexes = [
            models.Index(fields=['tender', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['rank']),
        ]
    
    def __str__(self):
        return f"{self.bidder_name} - {self.tender.reference_number}"
    
    def calculate_total_score(self, technical_weight=0.6, financial_weight=0.4):
        """حساب الدرجة الإجمالية"""
        if self.technical_score is not None and self.financial_score is not None:
            self.total_score = (
                (self.technical_score * Decimal(str(technical_weight))) + 
                (self.financial_score * Decimal(str(financial_weight)))
            )
            self.save()


class BidComparison(models.Model):
    """مقارنة العطاءات"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='comparisons', verbose_name='المناقصة')
    name = models.CharField('اسم المقارنة', max_length=200)
    comparison_date = models.DateField('تاريخ المقارنة', auto_now_add=True)
    
    # معايير المقارنة
    criteria = models.JSONField('معايير المقارنة', default=dict)
    
    # النتائج
    comparison_matrix = models.JSONField('مصفوفة المقارنة', default=dict)
    recommended_bid = models.ForeignKey(Bid, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='recommendations', verbose_name='العطاء الموصى به')
    recommendation_reason = models.TextField('سبب التوصية', blank=True)
    
    # الاعتماد
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_comparisons', verbose_name='اعتمد بواسطة')
    approved_at = models.DateTimeField('تاريخ الاعتماد', null=True, blank=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='comparisons_created')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مقارنة عطاءات'
        verbose_name_plural = 'مقارنات العطاءات'
        ordering = ['-comparison_date']
    
    def __str__(self):
        return f"مقارنة {self.tender.reference_number} - {self.name}"


class TenderEvaluation(models.Model):
    """تقييم المناقصة"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='evaluations', verbose_name='المناقصة')
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='detailed_evaluations', verbose_name='العطاء')
    
    evaluator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='المقيِّم')
    evaluation_date = models.DateField('تاريخ التقييم', auto_now_add=True)
    
    # معايير التقييم (حسب الوزن)
    technical_quality_score = models.DecimalField('جودة فنية', max_digits=5, decimal_places=2, 
                                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    experience_score = models.DecimalField('خبرة', max_digits=5, decimal_places=2,
                                          validators=[MinValueValidator(0), MaxValueValidator(100)])
    price_score = models.DecimalField('سعر', max_digits=5, decimal_places=2,
                                     validators=[MinValueValidator(0), MaxValueValidator(100)])
    delivery_time_score = models.DecimalField('وقت التسليم', max_digits=5, decimal_places=2,
                                             validators=[MinValueValidator(0), MaxValueValidator(100)])
    financial_stability_score = models.DecimalField('استقرار مالي', max_digits=5, decimal_places=2,
                                                    validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # الدرجة النهائية
    final_score = models.DecimalField('الدرجة النهائية', max_digits=5, decimal_places=2, default=0)
    
    # التعليقات
    strengths = models.TextField('نقاط القوة', blank=True)
    weaknesses = models.TextField('نقاط الضعف', blank=True)
    recommendations = models.TextField('التوصيات', blank=True)
    
    is_recommended = models.BooleanField('موصى به', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تقييم مناقصة'
        verbose_name_plural = 'تقييمات المناقصات'
        unique_together = ['bid', 'evaluator']
        ordering = ['-final_score']
    
    def __str__(self):
        return f"تقييم {self.bid.bidder_name} - {self.evaluator.username}"
    
    def calculate_final_score(self):
        """حساب الدرجة النهائية"""
        weights = {
            'technical_quality': 0.30,
            'experience': 0.15,
            'price': 0.35,
            'delivery_time': 0.10,
            'financial_stability': 0.10,
        }
        
        self.final_score = (
            (self.technical_quality_score * Decimal(str(weights['technical_quality']))) +
            (self.experience_score * Decimal(str(weights['experience']))) +
            (self.price_score * Decimal(str(weights['price']))) +
            (self.delivery_time_score * Decimal(str(weights['delivery_time']))) +
            (self.financial_stability_score * Decimal(str(weights['financial_stability'])))
        )
        
        self.save()


class TenderPerformance(models.Model):
    """أداء المناقصة بعد الترسية"""
    tender = models.OneToOneField(Tender, on_delete=models.CASCADE, related_name='performance', verbose_name='المناقصة')
    winning_bid = models.ForeignKey(Bid, on_delete=models.CASCADE, verbose_name='العطاء الفائز')
    
    # الأداء
    contract_value = models.DecimalField('قيمة العقد', max_digits=15, decimal_places=2)
    actual_cost = models.DecimalField('التكلفة الفعلية', max_digits=15, decimal_places=2, default=0)
    
    planned_start_date = models.DateField('تاريخ البدء المخطط')
    actual_start_date = models.DateField('تاريخ البدء الفعلي', null=True, blank=True)
    planned_end_date = models.DateField('تاريخ الانتهاء المخطط')
    actual_end_date = models.DateField('تاريخ الانتهاء الفعلي', null=True, blank=True)
    
    completion_percentage = models.DecimalField('نسبة الإنجاز %', max_digits=5, decimal_places=2, default=0,
                                               validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # التقييم
    quality_rating = models.IntegerField('تقييم الجودة', validators=[MinValueValidator(1), MaxValueValidator(5)], 
                                        default=3, help_text='من 1 إلى 5')
    timeliness_rating = models.IntegerField('تقييم الالتزام بالمواعيد', validators=[MinValueValidator(1), MaxValueValidator(5)],
                                          default=3, help_text='من 1 إلى 5')
    communication_rating = models.IntegerField('تقييم التواصل', validators=[MinValueValidator(1), MaxValueValidator(5)],
                                             default=3, help_text='من 1 إلى 5')
    overall_rating = models.DecimalField('التقييم الإجمالي', max_digits=3, decimal_places=2, default=0)
    
    # المشاكل والحلول
    issues_encountered = models.TextField('المشاكل التي واجهت', blank=True)
    solutions_implemented = models.TextField('الحلول المطبقة', blank=True)
    lessons_learned = models.TextField('الدروس المستفادة', blank=True)
    
    would_work_again = models.BooleanField('نوصي بالتعامل مجدداً', default=True)
    
    notes = models.TextField('ملاحظات', blank=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'أداء مناقصة'
        verbose_name_plural = 'أداء المناقصات'
    
    def __str__(self):
        return f"أداء {self.tender.reference_number}"
    
    def calculate_overall_rating(self):
        """حساب التقييم الإجمالي"""
        self.overall_rating = Decimal(
            (self.quality_rating + self.timeliness_rating + self.communication_rating) / 3
        )
        self.save()
