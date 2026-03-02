"""
URLs الرئيسية — RITA ERP
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('production/', include('apps.production.urls')),
    path('sales/', include('apps.sales.urls')),
    path('purchases/', include('apps.purchases.urls')),
    path('authorization/', include('apps.authorization.urls')),
    path('reports/', include('apps.reports.urls')),
    path('treasury/', include('apps.treasury.urls')),
    path('installments/', include('apps.installments.urls')),
    path('printing/',     include('apps.printing.urls')),
    path('delivery/',     include('apps.delivery.urls')),
    path('warranty/',     include('apps.warranty.urls')),
    path('hr/',           include('apps.hr.urls')),
    path('quotations/',   include('apps.quotations.urls')),
    path('expenses/',     include('apps.expenses.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('crm/', include('apps.crm.urls')),
    path('partners/', include('apps.partners.urls')),
    path('api/v1/', include('apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ===== Error Handlers (Sprint 20) =====
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'

