from django.db import models
from django.contrib.auth.models import User


class ComplianceStandard(models.Model):
    """معيار الامتثال"""
    code = models.CharField('الرمز', max_length=50, unique=True)
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف')
    
    standard_type = models.CharField('نوع المعيار', max_length=30, choices=[
        ('iso', 'ISO'), ('regulatory', 'تنظيمي'), ('industry', 'صناعي'), 
        ('internal', 'داخلي'), ('quality', 'جودة'), ('safety', 'سلامة')
    ])
    
    issuing_body = models.CharField('الجهة المصدرة', max_length=200)
    version = models.CharField('الإصدار', max_length=50)
    effective_date = models.DateField('تاريخ السريان')
    
    requirements = models.TextField('المتطلبات')
    reference_url = models.URLField('رابط المرجع', blank=True)
    
    is_mandatory = models.BooleanField('إلزامي', default=True)
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'معيار امتثال'
        verbose_name_plural = 'معايير الامتثال'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class ComplianceChecklist(models.Model):
    """قائمة المراجعة"""
    title = models.CharField('العنوان', max_length=200)
    standard = models.ForeignKey(ComplianceStandard, on_delete=models.CASCADE, related_name='checklists')
    
    description = models.TextField('الوصف', blank=True)
    checklist_items = models.JSONField('بنود القائمة', default=list, help_text='قائمة بنود المراجعة')
    
    frequency = models.CharField('التكرار', max_length=20, choices=[
        ('daily', 'يومي'), ('weekly', 'أسبوعي'), ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'), ('annually', 'سنوي'), ('ad_hoc', 'عند الطلب')
    ])
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='compliance_checklists')
    
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'قائمة مراجعة'
        verbose_name_plural = 'قوائم المراجعة'
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} - {self.standard.code}"


class Audit(models.Model):
    """المراجعة"""
    audit_number = models.CharField('رقم المراجعة', max_length=100, unique=True)
    title = models.CharField('العنوان', max_length=200)
    
    audit_type = models.CharField('نوع المراجعة', max_length=30, choices=[
        ('internal', 'داخلية'), ('external', 'خارجية'), ('compliance', 'امتثال'),
        ('financial', 'مالية'), ('operational', 'تشغيلية'), ('quality', 'جودة')
    ])
    
    standard = models.ForeignKey(ComplianceStandard, on_delete=models.SET_NULL, null=True, blank=True)
    checklist = models.ForeignKey(ComplianceChecklist, on_delete=models.SET_NULL, null=True, blank=True)
    
    scope = models.TextField('النطاق')
    objectives = models.TextField('الأهداف')
    
    # الجدولة
    scheduled_date = models.DateField('التاريخ المجدول')
    actual_start_date = models.DateField('تاريخ البدء الفعلي', null=True, blank=True)
    actual_end_date = models.DateField('تاريخ الانتهاء الفعلي', null=True, blank=True)
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('planned', 'مخططة'), ('in_progress', 'قيد التنفيذ'), ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة')
    ], default='planned')
    
    # الفريق
    lead_auditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audits_led')
    audit_team = models.ManyToManyField(User, related_name='audits_participated', blank=True)
    
    # النتائج
    findings_summary = models.TextField('ملخص النتائج', blank=True)
    overall_compliance_score = models.IntegerField('نقاط الامتثال الإجمالية', null=True, blank=True,
                                                   help_text='من 0 إلى 100')
    
    report_document_url = models.URLField('رابط تقرير المراجعة', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'مراجعة'
        verbose_name_plural = 'المراجعات'
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.audit_number} - {self.title}"


class AuditFinding(models.Model):
    """نتيجة المراجعة"""
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='findings')
    finding_number = models.CharField('رقم النتيجة', max_length=50)
    
    severity = models.CharField('الخطورة', max_length=20, choices=[
        ('minor', 'بسيطة'), ('major', 'كبيرة'), ('critical', 'حرجة'), ('observation', 'ملاحظة')
    ])
    
    category = models.CharField('التصنيف', max_length=50, choices=[
        ('non_compliance', 'عدم امتثال'), ('deficiency', 'نقص'), 
        ('opportunity', 'فرصة تحسين'), ('best_practice', 'ممارسة جيدة')
    ])
    
    description = models.TextField('الوصف')
    evidence = models.TextField('الدليل', blank=True)
    impact = models.TextField('التأثير', blank=True)
    
    # الإجراءات التصحيحية
    corrective_action_required = models.BooleanField('يتطلب إجراء تصحيحي', default=True)
    corrective_action_plan = models.TextField('خطة الإجراء التصحيحي', blank=True)
    corrective_action_deadline = models.DateField('الموعد النهائي للإجراء', null=True, blank=True)
    
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                          related_name='audit_findings_responsible')
    
    status = models.CharField('الحالة', max_length=20, choices=[
        ('open', 'مفتوحة'), ('in_progress', 'قيد المعالجة'), 
        ('resolved', 'محلولة'), ('closed', 'مغلقة')
    ], default='open')
    
    resolution_date = models.DateField('تاريخ الحل', null=True, blank=True)
    resolution_notes = models.TextField('ملاحظات الحل', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'نتيجة مراجعة'
        verbose_name_plural = 'نتائج المراجعات'
        ordering = ['-severity', 'finding_number']
    
    def __str__(self):
        return f"{self.audit.audit_number} - {self.finding_number}"


class ComplianceReport(models.Model):
    """تقرير الامتثال"""
    title = models.CharField('العنوان', max_length=200)
    report_period_start = models.DateField('بداية فترة التقرير')
    report_period_end = models.DateField('نهاية فترة التقرير')
    
    standards_covered = models.ManyToManyField(ComplianceStandard, verbose_name='المعايير المغطاة')
    
    # الملخص التنفيذي
    executive_summary = models.TextField('الملخص التنفيذي')
    overall_compliance_status = models.CharField('حالة الامتثال الإجمالية', max_length=20, choices=[
        ('compliant', 'ملتزم'), ('partially_compliant', 'ملتزم جزئياً'), 
        ('non_compliant', 'غير ملتزم'), ('under_review', 'قيد المراجعة')
    ])
    
    compliance_percentage = models.DecimalField('نسبة الامتثال %', max_digits=5, decimal_places=2, default=0)
    
    # التفاصيل
    detailed_findings = models.TextField('النتائج التفصيلية')
    areas_of_concern = models.TextField('مجالات القلق', blank=True)
    recommendations = models.TextField('التوصيات')
    
    # الأرقام
    total_audits_conducted = models.IntegerField('إجمالي المراجعات', default=0)
    total_findings = models.IntegerField('إجمالي النتائج', default=0)
    critical_findings = models.IntegerField('النتائج الحرجة', default=0)
    major_findings = models.IntegerField('النتائج الكبيرة', default=0)
    minor_findings = models.IntegerField('النتائج البسيطة', default=0)
    
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='compliance_reports')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_compliance_reports')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تقرير امتثال'
        verbose_name_plural = 'تقارير الامتثال'
        ordering = ['-report_period_end']
    
    def __str__(self):
        return f"{self.title} - {self.report_period_end}"
