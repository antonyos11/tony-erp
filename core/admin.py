from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext as _t
from .models import Company, Currency, AuditLog, AppSettings
from typing import Callable, TypeVar, Any, cast

F = TypeVar('F', bound=Callable[..., Any])

def short_desc(text: Any) -> Callable[[F], F]:
	"""Decorator to attach Django admin short_description with typing-friendly pattern."""
	def decorator(func: F) -> F:
		setattr(func, 'short_description', text)
		return func
	return decorator


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
	list_display = ("name", "phone", "tax_id", "default_currency", "created_display")
	list_filter = ("default_currency",)
	search_fields = ("name", "phone", "tax_id")
	readonly_fields = ("created_display",)
	
	@short_desc(_("الهاتف"))
	def created_display(self, obj):
		return obj.phone or _("غير محدد")

	fieldsets = (
		(_('بيانات الشركة الأساسية'), {
			'fields': ('name', 'address', 'phone', 'tax_id')
		}),
		(_('الإعدادات'), {
			'fields': ('logo', 'invoice_prefix', 'default_currency')
		}),
	)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "symbol", "exchange_rate", "is_active", "is_active_display", "is_default_display", "updated_at")
	list_filter = ("is_active", "is_default")
	# list_editable مُعطّلة لتفادي تحذير التعديلات غير المحفوظة
	search_fields = ("name", "code", "symbol")
	ordering = ("code",)
	
	fieldsets = (
		(_('معلومات العملة الأساسية'), {
			'fields': ('code', 'name', 'symbol')
		}),
		(_('إعدادات العملة'), {
			'fields': ('is_active', 'is_default', 'exchange_rate', 'decimal_places')
		}),
		(_('معلومات إضافية'), {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	
	@short_desc(_("حالة العملة"))
	def is_active_display(self, obj):
		if obj.is_active:
			return format_html('<span style="color: green; font-weight: bold;">{}</span>', _("نشط"))
		return format_html('<span style="color: red; font-weight: bold;">{}</span>', _("غير نشط"))
	
	@short_desc(_("النوع"))
	def is_default_display(self, obj):
		if obj.is_default:
			return format_html('<span style="color: blue; font-weight: bold;">{}</span>', _("افتراضية"))
		return format_html('<span style="color: gray;">{}</span>', _("عادية"))

	def save_model(self, request, obj, form, change):
		# التأكد من وجود عملة افتراضية واحدة فقط
		if obj.is_default:
			old_default = Currency.objects.filter(is_default=True).exclude(pk=obj.pk).first()
			if old_default:
				old_default.is_default = False
				old_default.save()
				messages.info(request, _t('تم إلغاء تعيين %(name)s كعملة افتراضية') % {'name': old_default.name})
		
		super().save_model(request, obj, form, change)
		
		if obj.is_default:
			messages.success(request, _t('تم تعيين %(name)s كعملة افتراضية للنظام') % {'name': obj.name})
	
	def get_readonly_fields(self, request, obj=None):
		if obj:  # editing an existing object
			readonly = ['code', 'created_at', 'updated_at']
			# إذا كانت العملة الافتراضية، لا يمكن تغيير سعر الصرف
			if obj.is_default:
				readonly.append('exchange_rate')
			return tuple(readonly)
		return ('created_at', 'updated_at')
	
	actions = ['make_active', 'make_inactive', 'set_as_default']
	
	@short_desc(_("تفعيل العملات المختارة"))
	def make_active(self, request, queryset):
		updated = queryset.update(is_active=True)
		messages.success(request, _t('تم تفعيل %(count)s عملة') % {'count': updated})
	
	@short_desc(_("إلغاء تفعيل العملات المختارة"))
	def make_inactive(self, request, queryset):
		# التأكد من عدم إلغاء تفعيل العملة الافتراضية
		default_count = queryset.filter(is_default=True).count()
		if default_count > 0:
			messages.error(request, _t('لا يمكن إلغاء تفعيل العملة الافتراضية'))
			return
		updated = queryset.update(is_active=False)
		messages.success(request, _t('تم إلغاء تفعيل %(count)s عملة') % {'count': updated})
	
	@short_desc(_("تعيين كعملة افتراضية"))
	def set_as_default(self, request, queryset):
		if queryset.count() != 1:
			messages.error(request, _t('يجب اختيار عملة واحدة فقط لتعيينها كافتراضية'))
			return
		currency = queryset.first()
		if not currency.is_active:
			messages.error(request, _t('لا يمكن تعيين عملة غير نشطة كافتراضية'))
			return
		Currency.objects.filter(is_default=True).update(is_default=False)
		currency.is_default = True
		currency.save()
		messages.success(request, _t('تم تعيين %(name)s كعملة افتراضية') % {'name': currency.name})


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
	list_display = ('id', 'updated_at', 'audit_retention_days')
	readonly_fields = ('updated_at',)
	
	fieldsets = (
		(_('إعدادات المظهر'), {
			'fields': ('brand_colors', 'kpi_visible_keys')
		}),
		(_('إعدادات المراجعة'), {
			'fields': ('audit_retention_days', 'audit_sensitive_fields', 
				  'audit_ignore_apps', 'audit_ignore_models', 'audit_alert_rules')
		}),
		(_('إعدادات السلامة'), {
			'fields': ('safety_incident_alert_threshold', 'safety_alert_emails')
		}),
	)
	
	def has_add_permission(self, request):
		# السماح بإضافة واحدة فقط
		return not AppSettings.objects.exists()
	
	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = (
		'created_at', 'action', 'app_label', 'model_name', 'object_id', 'user', 'ip_address'
	)
	list_filter = ('action', 'app_label', 'model_name', 'created_at')
	search_fields = ('object_repr', 'object_id', 'user__username', 'ip_address', 'user_agent')
	readonly_fields = (
		'user', 'action', 'app_label', 'model_name', 'object_id', 'object_repr',
		'changes', 'ip_address', 'user_agent', 'created_at'
	)
	ordering = ('-created_at',)
