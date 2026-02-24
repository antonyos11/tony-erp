from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.views.generic import RedirectView
from .views import (
    ShowroomViewSet,
    ShowroomEmployeeViewSet,
    ShowroomKPIsView,
    ShowroomPnLView,
    manage_extra_perms,
    ActiveShowroomView,
    ShowroomExpenseViewSet,
    ShowroomPurchaseViewSet,
    ShowroomStockMovementViewSet,
    ShowroomPayrollEntryViewSet,
    ShowroomTransferAPIView,
    ShowroomShiftViewSet,
    ShowroomShiftAssignmentViewSet,
    ShowroomSummaryView,
    ShowroomComparisonView,
    TemporaryWorkerViewSet,
    ShowroomRentPaymentViewSet,
    property_management_view,
)

app_name = 'showrooms'

router = DefaultRouter()
router.register(r'showrooms', ShowroomViewSet, basename='showroom')
router.register(r'showroom-employees', ShowroomEmployeeViewSet, basename='showroom-employee')
router.register(r'showroom-expenses', ShowroomExpenseViewSet, basename='showroom-expense')
router.register(r'showroom-purchases', ShowroomPurchaseViewSet, basename='showroom-purchase')
router.register(r'showroom-movements', ShowroomStockMovementViewSet, basename='showroom-movement')
router.register(r'showroom-payroll', ShowroomPayrollEntryViewSet, basename='showroom-payroll')
router.register(r'showroom-shifts', ShowroomShiftViewSet, basename='showroom-shift')
router.register(r'showroom-shift-assignments', ShowroomShiftAssignmentViewSet, basename='showroom-shift-assignment')
router.register(r'temporary-workers', TemporaryWorkerViewSet, basename='temporary-worker')
router.register(r'rent-payments', ShowroomRentPaymentViewSet, basename='rent-payment')

urlpatterns = router.urls + [
    path('showrooms/pnl/', ShowroomPnLView.as_view(), name='showroom-pnl'),
    path('showrooms/kpis/', ShowroomKPIsView.as_view(), name='showroom-kpis'),
    path('showrooms/active/', ActiveShowroomView.as_view(), name='active-showroom'),
    path('showrooms/transfer/', ShowroomTransferAPIView.as_view(), name='showroom-transfer'),
    path('showrooms/summary/', ShowroomSummaryView.as_view(), name='showroom-summary'),
    path('showrooms/compare/', ShowroomComparisonView.as_view(), name='showroom-compare'),
    path('<int:showroom_id>/employee/<int:employee_id>/extra-perms/', manage_extra_perms, name='showroom-employee-extra-perms'),
    
    # Property Management
    path('property-management/', property_management_view, name='property-management'),
    
    # Alias URLs for menu compatibility (underscore versions pointing to hyphen versions)
    path('list/', ShowroomViewSet.as_view({'get': 'list'}), name='showroom_list'),
    path('create/', ShowroomViewSet.as_view({'get': 'list', 'post': 'create'}), name='showroom_create'),
    path('active/', ActiveShowroomView.as_view(), name='active_showroom'),
    path('employees/', ShowroomEmployeeViewSet.as_view({'get': 'list'}), name='employee_list'),
    path('employees/create/', ShowroomEmployeeViewSet.as_view({'get': 'list', 'post': 'create'}), name='employee_create'),
    path('employees/permissions/', ShowroomEmployeeViewSet.as_view({'get': 'list'}), name='employee_permissions'),
    path('kpis/', ShowroomKPIsView.as_view(), name='kpis'),
    path('pnl/', ShowroomPnLView.as_view(), name='pnl'),
]
