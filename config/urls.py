"""
URL configuration for Tony ERP project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('branches:unified_dashboard')),
    path('branches/', include('branches.urls')),
    path('accounting/', include('accounting.urls')),
    path('dashboard/', include('accounting.urls')),
    path('inventory/', include('inventory.urls')),
]
