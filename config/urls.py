"""
URLs الرئيسية — RITA ERP
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

