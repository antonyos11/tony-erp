from django.db import models
from django.conf import settings
from decimal import Decimal

class LoyaltyProgram(models.Model):
    """Loyalty program configuration"""
    name = models.CharField('اسم البرنامج', max_length=200)
    code = models.CharField('الكود', max_length=50, unique=True)
    description = models.TextField('الوصف', blank=True)
    points_per_unit = models.DecimalField('النقاط لكل وحدة عملة', max_digits=10, decimal_places=2, default=1)
    redemption_rate = models.DecimalField('معدل الاستبدال', max_digits=10, decimal_places=2, default=0.01, help_text='قيمة كل نقطة بالعملة')
    min_points_redeem = models.IntegerField('الحد الأدنى للاستبدال', default=100)
    is_active = models.BooleanField('نشط', default=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)

    class Meta:
        verbose_name = 'برنامج ولاء'
        verbose_name_plural = 'برامج الولاء'

    def __str__(self):
        return self.name

class LoyaltyTier(models.Model):
    """Loyalty program tiers"""
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='tiers')
    name = models.CharField('اسم المستوى', max_length=100)
    min_points = models.IntegerField('الحد الأدنى من النقاط')
    points_multiplier = models.DecimalField('مضاعف النقاط', max_digits=5, decimal_places=2, default=1)
    discount_percentage = models.DecimalField('نسبة الخصم', max_digits=5, decimal_places=2, default=0)
    benefits = models.TextField('المزايا', blank=True)
    color = models.CharField('اللون', max_length=20, default='#6c757d')

    class Meta:
        verbose_name = 'مستوى ولاء'
        verbose_name_plural = 'مستويات الولاء'
        ordering = ['min_points']

    def __str__(self):
        return f"{self.program.name} - {self.name}"

class CustomerLoyalty(models.Model):
    """Customer loyalty account"""
    customer = models.OneToOneField('partners.Customer', on_delete=models.CASCADE, related_name='loyalty')
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.PROTECT)
    current_points = models.IntegerField('النقاط الحالية', default=0)
    total_earned = models.IntegerField('إجمالي المكتسب', default=0)
    total_redeemed = models.IntegerField('إجمالي المستبدل', default=0)
    current_tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, blank=True)
    joined_at = models.DateTimeField('تاريخ الانضمام', auto_now_add=True)
    last_activity = models.DateTimeField('آخر نشاط', null=True, blank=True)

    class Meta:
        verbose_name = 'حساب ولاء العميل'
        verbose_name_plural = 'حسابات ولاء العملاء'

    def __str__(self):
        return f"{self.customer} - {self.current_points} نقطة"

    def update_tier(self):
        """Update customer tier based on total points"""
        tiers = self.program.tiers.filter(min_points__lte=self.total_earned).order_by('-min_points')
        if tiers.exists():
            self.current_tier = tiers.first()
            self.save()

class PointsTransaction(models.Model):
    """Points earning and redemption transactions"""
    TYPE_CHOICES = [
        ('earn', 'اكتساب'),
        ('redeem', 'استبدال'),
        ('expire', 'انتهاء صلاحية'),
        ('adjust', 'تعديل'),
        ('bonus', 'مكافأة'),
    ]
    
    loyalty_account = models.ForeignKey(CustomerLoyalty, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField('نوع العملية', max_length=20, choices=TYPE_CHOICES)
    points = models.IntegerField('النقاط')
    description = models.CharField('الوصف', max_length=200)
    reference_type = models.CharField('نوع المرجع', max_length=50, blank=True)
    reference_id = models.IntegerField('معرف المرجع', null=True, blank=True)
    balance_after = models.IntegerField('الرصيد بعد العملية')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'حركة نقاط'
        verbose_name_plural = 'حركات النقاط'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loyalty_account.customer} - {self.get_transaction_type_display()} {self.points}"

class LoyaltyReward(models.Model):
    """Redeemable rewards"""
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='rewards')
    name = models.CharField('اسم المكافأة', max_length=200)
    description = models.TextField('الوصف', blank=True)
    points_cost = models.IntegerField('تكلفة النقاط')
    reward_type = models.CharField('نوع المكافأة', max_length=50, choices=[
        ('discount', 'خصم'),
        ('product', 'منتج'),
        ('voucher', 'قسيمة'),
    ])
    reward_value = models.DecimalField('قيمة المكافأة', max_digits=10, decimal_places=2)
    quantity_available = models.IntegerField('الكمية المتاحة', null=True, blank=True)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'مكافأة'
        verbose_name_plural = 'المكافآت'

    def __str__(self):
        return f"{self.name} ({self.points_cost} نقطة)"
