from django.db import models
from django.conf import settings

class TicketCategory(models.Model):
    """Ticket categories"""
    name = models.CharField('الاسم', max_length=100)
    code = models.CharField('الكود', max_length=50, unique=True)
    description = models.TextField('الوصف', blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    sla_hours = models.IntegerField('وقت SLA بالساعات', default=24)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'فئة التذاكر'
        verbose_name_plural = 'فئات التذاكر'

    def __str__(self):
        return self.name

class Ticket(models.Model):
    """Support tickets"""
    PRIORITY_CHOICES = [
        ('low', 'منخفضة'),
        ('medium', 'متوسطة'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة'),
    ]
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('open', 'مفتوح'),
        ('pending', 'قيد الانتظار'),
        ('resolved', 'تم الحل'),
        ('closed', 'مغلق'),
    ]
    
    ticket_number = models.CharField('رقم التذكرة', max_length=50, unique=True)
    subject = models.CharField('الموضوع', max_length=200)
    description = models.TextField('الوصف')
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, verbose_name='الفئة')
    priority = models.CharField('الأولوية', max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Customer info
    customer = models.ForeignKey('partners.Customer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='العميل')
    contact_name = models.CharField('اسم جهة الاتصال', max_length=100, blank=True)
    contact_email = models.EmailField('البريد الإلكتروني', blank=True)
    contact_phone = models.CharField('رقم الهاتف', max_length=20, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='helpdesk_assigned_tickets', verbose_name='معين إلى')
    assigned_team = models.CharField('الفريق المعين', max_length=100, blank=True)
    
    # Dates
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    due_date = models.DateTimeField('تاريخ الاستحقاق', null=True, blank=True)
    resolved_at = models.DateTimeField('تاريخ الحل', null=True, blank=True)
    closed_at = models.DateTimeField('تاريخ الإغلاق', null=True, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='helpdesk_created_tickets')

    class Meta:
        verbose_name = 'تذكرة دعم'
        verbose_name_plural = 'تذاكر الدعم'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

class TicketComment(models.Model):
    """Comments on tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField('التعليق')
    is_internal = models.BooleanField('داخلي', default=False, help_text='التعليقات الداخلية لا تظهر للعميل')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='helpdesk_comments')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)

    class Meta:
        verbose_name = 'تعليق'
        verbose_name_plural = 'التعليقات'
        ordering = ['created_at']

    def __str__(self):
        return f"تعليق على {self.ticket.ticket_number}"

class TicketAttachment(models.Model):
    """Attachments on tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField('الملف', upload_to='helpdesk/attachments/')
    filename = models.CharField('اسم الملف', max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)

    class Meta:
        verbose_name = 'مرفق'
        verbose_name_plural = 'المرفقات'

class KnowledgeBase(models.Model):
    """Knowledge base articles"""
    title = models.CharField('العنوان', max_length=200)
    slug = models.SlugField('الرابط', unique=True)
    content = models.TextField('المحتوى')
    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    is_published = models.BooleanField('منشور', default=False)
    view_count = models.IntegerField('عدد المشاهدات', default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='helpdesk_kb_articles')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)

    class Meta:
        verbose_name = 'مقال قاعدة المعرفة'
        verbose_name_plural = 'مقالات قاعدة المعرفة'

    def __str__(self):
        return self.title
