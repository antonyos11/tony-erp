from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from apps.api import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)
router.register(r'customers', views.CustomerViewSet)
router.register(r'invoices', views.SalesInvoiceViewSet)
router.register(r'stock-levels', views.StockLevelViewSet)
router.register(r'production-orders', views.ProductionOrderViewSet)
router.register(r'quotations', views.QuotationViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'attendance', views.AttendanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard_api, name='api_dashboard'),
    path('token/', obtain_auth_token, name='api_token'),
]
