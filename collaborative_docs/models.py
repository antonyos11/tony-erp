"""
نماذج المستندات التعاونية
Collaborative Documents Models
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class DocumentFolder(models.Model):
    """مجلد المستندات"""
    
    name = models.CharField('الاسم', max_length=200)
    description = models.TextField('الوصف', blank=True)
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders',
        verbose_name='المجلد الأب'
    )
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_folders',
        verbose_name='المالك'
    )
    
    is_shared = models.BooleanField('مشترك', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'مجلد'
        verbose_name_plural = 'المجلدات'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Document(models.Model):
    """المستند التعاوني"""
    
    DOC_TYPES = [
        ('document', 'مستند'),
        ('spreadsheet', 'جدول بيانات'),
        ('presentation', 'عرض تقديمي'),
        ('form', 'نموذج'),
    ]
    
    uuid = models.UUIDField('المعرف الفريد', default=uuid.uuid4, unique=True)
    title = models.CharField('العنوان', max_length=300)
    
    doc_type = models.CharField('نوع المستند', max_length=20, choices=DOC_TYPES, default='document')
    
    content = models.TextField('المحتوى', blank=True)
    content_json = models.JSONField('المحتوى JSON', default=dict, blank=True)
    
    folder = models.ForeignKey(
        DocumentFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name='المجلد'
    )
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_documents',
        verbose_name='المالك'
    )
    
    # المشاركة
    collaborators = models.ManyToManyField(
        User,
        through='DocumentCollaborator',
        through_fields=('document', 'user'),
        related_name='shared_documents',
        verbose_name='المتعاونون'
    )
    
    # الإعدادات
    is_public = models.BooleanField('عام', default=False)
    is_template = models.BooleanField('قالب', default=False)
    is_starred = models.BooleanField('مفضل', default=False)
    is_archived = models.BooleanField('مؤرشف', default=False)
    
    # الإحصائيات
    view_count = models.IntegerField('عدد المشاهدات', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='last_edited_documents',
        verbose_name='آخر تعديل بواسطة'
    )
    
    class Meta:
        verbose_name = 'مستند'
        verbose_name_plural = 'المستندات'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title
    
    @property
    def edit_url(self):
        return f"/docs/edit/{self.uuid}/"


class DocumentCollaborator(models.Model):
    """متعاون في المستند"""
    
    PERMISSIONS = [
        ('view', 'عرض فقط'),
        ('comment', 'تعليق'),
        ('edit', 'تعديل'),
        ('admin', 'مسؤول'),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    permission = models.CharField('الصلاحية', max_length=20, choices=PERMISSIONS, default='view')
    
    added_at = models.DateTimeField('تاريخ الإضافة', auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_collaborators',
        verbose_name='أضيف بواسطة'
    )
    
    class Meta:
        verbose_name = 'متعاون'
        verbose_name_plural = 'المتعاونون'
        unique_together = ['document', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.document.title}"


class DocumentVersion(models.Model):
    """نسخة المستند"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='المستند'
    )
    
    version_number = models.IntegerField('رقم النسخة')
    content = models.TextField('المحتوى')
    content_json = models.JSONField('المحتوى JSON', default=dict)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='أنشأ بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    description = models.CharField('الوصف', max_length=300, blank=True)
    
    class Meta:
        verbose_name = 'نسخة'
        verbose_name_plural = 'النسخ'
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"


class DocumentComment(models.Model):
    """تعليق على المستند"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='المستند'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    
    content = models.TextField('المحتوى')
    
    # موقع التعليق في المستند
    position_start = models.IntegerField('بداية الموقع', null=True, blank=True)
    position_end = models.IntegerField('نهاية الموقع', null=True, blank=True)
    selected_text = models.TextField('النص المحدد', blank=True)
    
    # الرد على تعليق
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='الرد على'
    )
    
    is_resolved = models.BooleanField('تم الحل', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'تعليق'
        verbose_name_plural = 'التعليقات'
        ordering = ['created_at']
    
    def __str__(self):
        return f"تعليق على {self.document.title}"


class DocumentActivity(models.Model):
    """نشاط المستند"""
    
    ACTIVITY_TYPES = [
        ('created', 'تم الإنشاء'),
        ('edited', 'تم التعديل'),
        ('shared', 'تمت المشاركة'),
        ('commented', 'تم التعليق'),
        ('viewed', 'تم العرض'),
        ('restored', 'تمت الاستعادة'),
    ]
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='المستند'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='المستخدم'
    )
    
    activity_type = models.CharField('نوع النشاط', max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField('الوصف', blank=True)
    
    created_at = models.DateTimeField('التاريخ', auto_now_add=True)
    
    class Meta:
        verbose_name = 'نشاط'
        verbose_name_plural = 'الأنشطة'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.document.title}"
