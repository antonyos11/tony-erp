"""
ملفات apps.py لجميع التطبيقات الجديدة
"""

# risk_management/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class RiskManagementConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'risk_management'
    verbose_name = _('إدارة المخاطر والتأمين')

# tax_system/apps.py
class TaxSystemConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'tax_system'
    verbose_name = _('نظام الضرائب')

# contract_management/apps.py
class ContractManagementConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'contract_management'
    verbose_name = _('إدارة العقود')

# advanced_notifications/apps.py
class AdvancedNotificationsConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'advanced_notifications'
    verbose_name = _('الإشعارات المتقدمة')

# treasury_management/apps.py
class TreasuryManagementConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'treasury_management'
    verbose_name = _('إدارة الشؤون المالية')

# advanced_crm/apps.py
class AdvancedCrmConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'advanced_crm'
    verbose_name = _('نظام CRM المتقدم')

# business_intelligence/apps.py
class BusinessIntelligenceConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'business_intelligence'
    verbose_name = _('الذكاء الاصطناعي والبيانات الضخمة')

# correspondence_management/apps.py
class CorrespondenceManagementConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'correspondence_management'
    verbose_name = _('إدارة المراسلات')

# intellectual_property/apps.py
class IntellectualPropertyConfig(AppConfig):
    default_auto_field = 'django.db.BigAutoField'
    name = 'intellectual_property'
    verbose_name = _('الملكية الفكرية والبراءات')
