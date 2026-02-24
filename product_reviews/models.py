"""
نماذج نظام المراجعات والتقييمات
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from inventory.models import Product


class ProductReview(models.Model):
    """مراجعات المنتجات"""
    
    RATING_CHOICES = [(i, f'{i} نجوم') for i in range(1, 6)]
    
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
    ]
    
    # المعلومات الأساسية
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='المنتج'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name='المستخدم'
    )
    
    # التقييم
    rating = models.IntegerField(
        'التقييم',
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField('العنوان', max_length=200)
    review_text = models.TextField('المراجعة')
    
    # تقييمات تفصيلية (اختياري)
    quality_rating = models.IntegerField(
        'تقييم الجودة',
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    value_rating = models.IntegerField(
        'تقييم القيمة مقابل السعر',
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    delivery_rating = models.IntegerField(
        'تقييم التوصيل',
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # الحالة
    status = models.CharField(
        'الحالة',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # معلومات الشراء
    verified_purchase = models.BooleanField('شراء موثق', default=False)
    purchase_date = models.DateField('تاريخ الشراء', null=True, blank=True)
    
    # التفاعل
    helpful_count = models.IntegerField('عدد الإعجابات (مفيد)', default=0)
    not_helpful_count = models.IntegerField('عدد عدم الإعجاب (غير مفيد)', default=0)
    
    # ملاحظات الإدارة
    admin_notes = models.TextField('ملاحظات الإدارة', blank=True)
    rejection_reason = models.TextField('سبب الرفض', blank=True)
    
    # التواريخ
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    approved_at = models.DateTimeField('تاريخ الموافقة', null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reviews',
        verbose_name='وافق عليها'
    )
    
    class Meta:
        verbose_name = 'مراجعة منتج'
        verbose_name_plural = 'مراجعات المنتجات'
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # مراجعة واحدة لكل مستخدم لكل منتج
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['rating']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        stars = '⭐' * self.rating
        return f"{stars} - {self.product.name} - {self.user.username}"
    
    def get_stars_display(self):
        """عرض النجوم"""
        return '⭐' * self.rating
    
    def is_helpful(self):
        """هل المراجعة مفيدة؟"""
        if self.helpful_count + self.not_helpful_count == 0:
            return None
        return (self.helpful_count / (self.helpful_count + self.not_helpful_count)) * 100
    
    def approve(self, user):
        """الموافقة على المراجعة"""
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()
    
    def reject(self, reason, user):
        """رفض المراجعة"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.approved_by = user
        self.save()


class ReviewImage(models.Model):
    """صور المراجعات"""
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='المراجعة'
    )
    image = models.ImageField('الصورة', upload_to='review_images/%Y/%m/')
    caption = models.CharField('التعليق', max_length=200, blank=True)
    uploaded_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'صورة مراجعة'
        verbose_name_plural = 'صور المراجعات'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"صورة - {self.review}"


class ReviewVideo(models.Model):
    """فيديوهات المراجعات"""
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='المراجعة'
    )
    video = models.FileField('الفيديو', upload_to='review_videos/%Y/%m/')
    thumbnail = models.ImageField('الصورة المصغرة', upload_to='review_thumbnails/%Y/%m/', blank=True, null=True)
    duration = models.IntegerField('المدة (ثواني)', null=True, blank=True)
    uploaded_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    
    class Meta:
        verbose_name = 'فيديو مراجعة'
        verbose_name_plural = 'فيديوهات المراجعات'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"فيديو - {self.review}"


class ReviewHelpfulness(models.Model):
    """تصويت على فائدة المراجعة"""
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='helpfulness_votes',
        verbose_name='المراجعة'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    is_helpful = models.BooleanField('مفيد؟')
    created_at = models.DateTimeField('تاريخ التصويت', auto_now_add=True)
    
    class Meta:
        verbose_name = 'تصويت على المراجعة'
        verbose_name_plural = 'تصويتات المراجعات'
        unique_together = ['review', 'user']
    
    def __str__(self):
        vote = 'مفيد' if self.is_helpful else 'غير مفيد'
        return f"{vote} - {self.review}"


class MerchantReply(models.Model):
    """رد التاجر على المراجعة"""
    review = models.OneToOneField(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='merchant_reply',
        verbose_name='المراجعة'
    )
    reply_text = models.TextField('الرد')
    replied_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='رد بواسطة'
    )
    created_at = models.DateTimeField('تاريخ الرد', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)
    
    class Meta:
        verbose_name = 'رد التاجر'
        verbose_name_plural = 'ردود التاجر'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"رد على: {self.review}"


class ReviewReport(models.Model):
    """بلاغات المراجعات"""
    
    REASON_CHOICES = [
        ('spam', 'رسالة غير مرغوبة'),
        ('offensive', 'محتوى مسيء'),
        ('fake', 'مراجعة مزيفة'),
        ('irrelevant', 'غير متعلق بالمنتج'),
        ('other', 'أخرى'),
    ]
    
    review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='المراجعة'
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='أبلغ بواسطة'
    )
    reason = models.CharField('السبب', max_length=20, choices=REASON_CHOICES)
    description = models.TextField('الوصف', blank=True)
    created_at = models.DateTimeField('تاريخ البلاغ', auto_now_add=True)
    is_resolved = models.BooleanField('تم المعالجة', default=False)
    resolved_at = models.DateTimeField('تاريخ المعالجة', null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        verbose_name='عولج بواسطة'
    )
    
    class Meta:
        verbose_name = 'بلاغ مراجعة'
        verbose_name_plural = 'بلاغات المراجعات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"بلاغ - {self.review} - {self.get_reason_display()}"
