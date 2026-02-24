from rest_framework.routers import DefaultRouter
from .api_views import (
    VehicleViewSet, DriverViewSet, TripViewSet,
    VehicleExpenseViewSet, VehicleDocumentViewSet,
    DriverViolationViewSet, DriverAdvanceViewSet,
    DriverLocationPingViewSet,
)

router = DefaultRouter()
router.register('vehicles', VehicleViewSet)
router.register('drivers', DriverViewSet)
router.register('trips', TripViewSet)
router.register('expenses', VehicleExpenseViewSet)
router.register('documents', VehicleDocumentViewSet)
router.register('violations', DriverViolationViewSet)
router.register('advances', DriverAdvanceViewSet)
router.register('locations', DriverLocationPingViewSet)

urlpatterns = router.urls
