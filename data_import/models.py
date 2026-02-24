# -*- coding: utf-8 -*-
"""
نماذج نظام استيراد البيانات
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class ImportSession(models.Model):
    """جلسة استيراد بيانات"""
    
    STATUS_CHOICES = [
        ('pending', _('قيد الانتظار')),
        ('processing', _('جاري المعالجة')),
        ('completed', _('مكتمل')),
        ('failed', _('فشل')),
        ('partial', _('مكتمل جزئياً')),
    ]
    
    MODULE_CHOICES = [
        ('all', _('جميع الموديولات')),
        ('products', _('المنتجات')),
        ('categories', _('الفئات')),
        ('customers', _('العملاء')),
        ('suppliers', _('الموردين')),
        ('employees', _('الموظفين')),
        ('departments', _('الأقسام')),
        ('accounts', _('الحسابات المحاسبية')),
        ('locations', _('المخازن/المواقع')),
        ('opening_balances', _('الأرصدة الافتتاحية')),
    ]
    
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name=_('المستخدم'))
    module = models.CharField(_('الموديول'), max_length=50, choices=MODULE_CHOICES)
    file = models.FileField(_('ملف Excel'), upload_to='imports/%Y/%m/')
    original_filename = models.CharField(_('اسم الملف الأصلي'), max_length=255)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    total_rows = models.IntegerField(_('إجمالي الصفوف'), default=0)
    processed_rows = models.IntegerField(_('الصفوف المعالجة'), default=0)
    success_count = models.IntegerField(_('الناجحة'), default=0)
    error_count = models.IntegerField(_('الفاشلة'), default=0)
    
    error_log = models.TextField(_('سجل الأخطاء'), blank=True)
    result_summary = models.JSONField(_('ملخص النتائج'), default=dict, blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    completed_at = models.DateTimeField(_('تاريخ الانتهاء'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('جلسة استيراد')
        verbose_name_plural = _('جلسات الاستيراد')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_module_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ImportError(models.Model):
    """أخطاء الاستيراد التفصيلية"""
    
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='errors')
    row_number = models.IntegerField(_('رقم الصف'))
    column_name = models.CharField(_('اسم العمود'), max_length=100, blank=True)
    error_type = models.CharField(_('نوع الخطأ'), max_length=50)
    error_message = models.TextField(_('رسالة الخطأ'))
    row_data = models.JSONField(_('بيانات الصف'), default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('خطأ استيراد')
        verbose_name_plural = _('أخطاء الاستيراد')
        ordering = ['row_number']


class SystemInitialization(models.Model):
    """حالة تهيئة النظام"""
    
    id = models.AutoField(primary_key=True)
    is_initialized = models.BooleanField(_('تم التهيئة'), default=False)
    initialized_at = models.DateTimeField(_('تاريخ التهيئة'), null=True, blank=True)
    initialized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # حالة استيراد كل موديول
    products_imported = models.BooleanField(_('تم استيراد المنتجات'), default=False)
    categories_imported = models.BooleanField(_('تم استيراد الفئات'), default=False)
    customers_imported = models.BooleanField(_('تم استيراد العملاء'), default=False)
    suppliers_imported = models.BooleanField(_('تم استيراد الموردين'), default=False)
    employees_imported = models.BooleanField(_('تم استيراد الموظفين'), default=False)
    departments_imported = models.BooleanField(_('تم استيراد الأقسام'), default=False)
    accounts_imported = models.BooleanField(_('تم استيراد الحسابات'), default=False)
    locations_imported = models.BooleanField(_('تم استيراد المخازن'), default=False)
    opening_balances_imported = models.BooleanField(_('تم استيراد الأرصدة'), default=False)
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('حالة تهيئة النظام')
        verbose_name_plural = _('حالة تهيئة النظام')
    
    @classmethod
    def get_instance(cls):
        """الحصول على سجل التهيئة الوحيد"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
