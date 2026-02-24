"""
نماذج نظام إدارة المحتوى
CMS Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class PageCategory(models.Model):
    """تصنيف الصفحات"""
    
    name = models.CharField('الاسم', max_length=100)
    slug = models.SlugField('المعرف', unique=True, allow_unicode=True)
    description = models.TextField('الوصف', blank=True)
    icon = models.CharField('الأيقونة', max_length=50, blank=True)
    color = models.CharField('اللون', max_length=20, default='primary')
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='التصنيف الأب'
    )
    
    order = models.IntegerField('الترتيب', default=0)
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تصنيف'
        verbose_name_plural = 'التصنيفات'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Page(models.Model):
    """صفحة المحتوى"""
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('published', 'منشور'),
        ('scheduled', 'مجدول'),
        ('archived', 'مؤرشف'),
    ]
    
    title = models.CharField('العنوان', max_length=300)
    slug = models.SlugField('المعرف', unique=True, allow_unicode=True)
    
    category = models.ForeignKey(
        PageCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages',
        verbose_name='التصنيف'
    )
    
    # المحتوى
    excerpt = models.TextField('المقتطف', blank=True)
    content = models.TextField('المحتوى')
    content_blocks = models.JSONField('كتل المحتوى', default=list, blank=True)
    
    # الصورة
    featured_image = models.ImageField('الصورة البارزة', upload_to='cms/pages/', blank=True)
    
    # SEO
    meta_title = models.CharField('عنوان SEO', max_length=200, blank=True)
    meta_description = models.TextField('وصف SEO', blank=True)
    meta_keywords = models.CharField('كلمات مفتاحية', max_length=300, blank=True)
    
    # الحالة
    status = models.CharField('الحالة', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # النشر
    published_at = models.DateTimeField('تاريخ النشر', null=True, blank=True)
    scheduled_at = models.DateTimeField('موعد النشر المجدول', null=True, blank=True)
    
    # المؤلف
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cms_pages',
        verbose_name='المؤلف'
    )
    
    # القالب
    template = models.CharField('القالب', max_length=100, default='default')
    
    # الخيارات
    is_homepage = models.BooleanField('الصفحة الرئيسية', default=False)
    show_in_menu = models.BooleanField('عرض في القائمة', default=True)
    allow_comments = models.BooleanField('السماح بالتعليقات', default=True)
    
    # الإحصائيات
    view_count = models.IntegerField('عدد المشاهدات', default=0)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'صفحة'
        verbose_name_plural = 'الصفحات'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)


class ContentBlock(models.Model):
    """كتلة محتوى قابلة لإعادة الاستخدام"""
    
    BLOCK_TYPES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('gallery', 'معرض صور'),
        ('video', 'فيديو'),
        ('html', 'HTML'),
        ('quote', 'اقتباس'),
        ('table', 'جدول'),
        ('accordion', 'أكورديون'),
        ('tabs', 'تبويبات'),
        ('cta', 'دعوة للإجراء'),
        ('form', 'نموذج'),
    ]
    
    name = models.CharField('الاسم', max_length=100)
    block_type = models.CharField('نوع الكتلة', max_length=20, choices=BLOCK_TYPES)
    
    content = models.TextField('المحتوى', blank=True)
    content_json = models.JSONField('بيانات المحتوى', default=dict, blank=True)
    
    # التصميم
    css_class = models.CharField('فئة CSS', max_length=100, blank=True)
    background_color = models.CharField('لون الخلفية', max_length=20, blank=True)
    
    is_global = models.BooleanField('كتلة عامة', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'كتلة محتوى'
        verbose_name_plural = 'كتل المحتوى'
    
    def __str__(self):
        return self.name


class Menu(models.Model):
    """القوائم"""
    
    name = models.CharField('الاسم', max_length=100)
    slug = models.SlugField('المعرف', unique=True, allow_unicode=True)
    location = models.CharField('الموقع', max_length=50, blank=True)
    
    is_active = models.BooleanField('نشط', default=True)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'قائمة'
        verbose_name_plural = 'القوائم'
    
    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """عناصر القائمة"""
    
    LINK_TYPES = [
        ('page', 'صفحة'),
        ('url', 'رابط خارجي'),
        ('category', 'تصنيف'),
    ]
    
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='القائمة'
    )
    
    title = models.CharField('العنوان', max_length=100)
    link_type = models.CharField('نوع الرابط', max_length=20, choices=LINK_TYPES, default='url')
    
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True, verbose_name='الصفحة')
    url = models.URLField('الرابط', blank=True)
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='العنصر الأب'
    )
    
    icon = models.CharField('الأيقونة', max_length=50, blank=True)
    css_class = models.CharField('فئة CSS', max_length=100, blank=True)
    
    order = models.IntegerField('الترتيب', default=0)
    is_active = models.BooleanField('نشط', default=True)
    open_in_new_tab = models.BooleanField('فتح في تبويب جديد', default=False)
    
    class Meta:
        verbose_name = 'عنصر قائمة'
        verbose_name_plural = 'عناصر القائمة'
        ordering = ['order']
    
    def __str__(self):
        return self.title
    
    @property
    def get_url(self):
        if self.link_type == 'page' and self.page:
            return f'/page/{self.page.slug}/'
        return self.url


class MediaFile(models.Model):
    """ملفات الوسائط"""
    
    FILE_TYPES = [
        ('image', 'صورة'),
        ('video', 'فيديو'),
        ('audio', 'صوت'),
        ('document', 'مستند'),
        ('other', 'أخرى'),
    ]
    
    title = models.CharField('العنوان', max_length=200)
    file = models.FileField('الملف', upload_to='cms/media/')
    file_type = models.CharField('نوع الملف', max_length=20, choices=FILE_TYPES)
    
    alt_text = models.CharField('النص البديل', max_length=200, blank=True)
    caption = models.TextField('التعليق', blank=True)
    
    file_size = models.BigIntegerField('حجم الملف', default=0)
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='رفع بواسطة'
    )
    
    created_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'ملف وسائط'
        verbose_name_plural = 'ملفات الوسائط'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class PageComment(models.Model):
    """تعليقات الصفحات"""
    
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='page_comments',
        verbose_name='الصفحة'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المستخدم'
    )
    
    name = models.CharField('الاسم', max_length=100, blank=True)
    email = models.EmailField('البريد الإلكتروني', blank=True)
    
    content = models.TextField('المحتوى')
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='الرد على'
    )
    
    is_approved = models.BooleanField('موافق عليه', default=False)
    
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تعليق'
        verbose_name_plural = 'التعليقات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تعليق على {self.page.title}"
