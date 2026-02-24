# branches/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class BranchType(models.TextChoices):
    """أنواع الفروع والمعارض"""
    BRANCH = 'branch', _('فرع')
    SHOWROOM = 'showroom', _('معرض')
    WAREHOUSE = 'warehouse', _('مخزن')
    OUTLET = 'outlet', _('منفذ بيع')


class Branch(models.Model):
    """
    نموذج موحد للفروع والمعارض
    يجمع بين الفروع والمعارض في جدول واحد مع التمييز بينهم بحقل النوع
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("اسم الفرع/المعرض")
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("الكود"),
        help_text=_("كود فريد للفرع أو المعرض")
    )
    
    branch_type = models.CharField(
        max_length=20,
        choices=BranchType.choices,
        default=BranchType.BRANCH,
        verbose_name=_("النوع")
    )
    
    # الفرع الأب (للمعارض التابعة لفرع)
    parent_branch = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_locations',
        verbose_name=_("الفرع الرئيسي"),
        help_text=_("المعرض أو المنفذ التابع لفرع رئيسي")
    )
    
    # بيانات الموقع
    address = models.TextField(
        verbose_name=_("العنوان"),
        blank=True
    )
    
    city = models.CharField(
        max_length=100,
        verbose_name=_("المدينة"),
        blank=True
    )
    
    region = models.CharField(
        max_length=100,
        verbose_name=_("المنطقة"),
        blank=True
    )
    
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name=_("خط العرض")
    )
    
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name=_("خط الطول")
    )
    
    # بيانات التواصل
    phone = models.CharField(
        max_length=20,
        verbose_name=_("الهاتف"),
        blank=True
    )
    
    mobile = models.CharField(
        max_length=20,
        verbose_name=_("الجوال"),
        blank=True
    )
    
    email = models.EmailField(
        verbose_name=_("البريد الإلكتروني"),
        blank=True
    )
    
    # المسؤول
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches',
        verbose_name=_("المدير المسؤول")
    )
    
    # الإعدادات
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("نشط")
    )
    
    is_main = models.BooleanField(
        default=False,
        verbose_name=_("الفرع/المعرض الرئيسي")
    )
    
    can_sell = models.BooleanField(
        default=True,
        verbose_name=_("يمكنه البيع")
    )
    
    can_purchase = models.BooleanField(
        default=False,
        verbose_name=_("يمكنه الشراء")
    )
    
    has_inventory = models.BooleanField(
        default=True,
        verbose_name=_("له مخزون خاص")
    )
    
    # أوقات العمل
    working_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("بداية الدوام")
    )
    
    working_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("نهاية الدوام")
    )
    
    working_days = models.CharField(
        max_length=50,
        default="0,1,2,3,4,5",
        verbose_name=_("أيام العمل"),
        help_text=_("أرقام الأيام مفصولة بفواصل (0=الأحد)")
    )
    
    # التواريخ
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("تاريخ الإنشاء")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("تاريخ التحديث")
    )
    
    # ملاحظات
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات")
    )

    class Meta:
        verbose_name = _("فرع/معرض")
        verbose_name_plural = _("الفروع والمعارض")
        ordering = ['branch_type', 'name']
        
    def __str__(self):
        type_label = dict(BranchType.choices).get(self.branch_type, '')
        return f"{self.name} ({type_label})"
    
    @property
    def type_icon(self):
        """أيقونة حسب النوع"""
        icons = {
            'branch': 'fas fa-building',
            'showroom': 'fas fa-car',
            'warehouse': 'fas fa-warehouse',
            'outlet': 'fas fa-shop',
        }
        return icons.get(self.branch_type, 'fas fa-map-marker-alt')
    
    @property
    def type_color(self):
        """لون حسب النوع"""
        colors = {
            'branch': 'primary',
            'showroom': 'success',
            'warehouse': 'warning',
            'outlet': 'info',
        }
        return colors.get(self.branch_type, 'secondary')
    
    def get_all_children(self):
        """الحصول على جميع الفروع/المعارض التابعة"""
        return Branch.objects.filter(parent_branch=self, is_active=True)
    
    @classmethod
    def get_branches(cls):
        """الحصول على الفروع فقط"""
        return cls.objects.filter(branch_type=BranchType.BRANCH, is_active=True)
    
    @classmethod
    def get_showrooms(cls):
        """الحصول على المعارض فقط"""
        return cls.objects.filter(branch_type=BranchType.SHOWROOM, is_active=True)
    
    @classmethod
    def get_all_active(cls):
        """الحصول على جميع الفروع والمعارض النشطة"""
        return cls.objects.filter(is_active=True)


class BranchTransfer(models.Model):
    """تحويلات بين الفروع والمعارض"""
    
    class TransferStatus(models.TextChoices):
        DRAFT = 'draft', _('مسودة')
        PENDING = 'pending', _('في الانتظار')
        APPROVED = 'approved', _('معتمد')
        IN_TRANSIT = 'in_transit', _('في الطريق')
        RECEIVED = 'received', _('مستلم')
        CANCELLED = 'cancelled', _('ملغي')
    
    transfer_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("رقم التحويل")
    )
    
    from_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name=_("من فرع/معرض")
    )
    
    to_branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name=_("إلى فرع/معرض")
    )
    
    status = models.CharField(
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.DRAFT,
        verbose_name=_("الحالة")
    )
    
    transfer_date = models.DateField(
        verbose_name=_("تاريخ التحويل")
    )
    
    received_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("تاريخ الاستلام")
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("ملاحظات")
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_transfers',
        verbose_name=_("أنشئ بواسطة")
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transfers',
        verbose_name=_("اعتمد بواسطة")
    )
    
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers',
        verbose_name=_("استلم بواسطة")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("تحويل")
        verbose_name_plural = _("التحويلات")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transfer_number}: {self.from_branch} → {self.to_branch}"
