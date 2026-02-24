"""
Mobile API Package
حزمة API للتطبيقات المحمولة

توفر endpoints محسّنة للموبايل مع استجابات مضغوطة
"""

from .auth import MobileAuthViewSet
from .dashboard import MobileDashboardViewSet
from .pos import MobilePOSViewSet
from .inventory import MobileInventoryViewSet
from .production import MobileProductionViewSet

__all__ = [
    'MobileAuthViewSet',
    'MobileDashboardViewSet',
    'MobilePOSViewSet',
    'MobileInventoryViewSet',
    'MobileProductionViewSet',
]
