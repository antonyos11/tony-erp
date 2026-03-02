"""
URLs تطبيق الشركاء (الموردين) — RITA ERP
"""
from django.urls import path
from apps.partners import views

app_name = 'partners'

urlpatterns = [
    path('',                        views.SupplierListView.as_view(),        name='supplier_list'),
    path('create/',                 views.SupplierCreateView.as_view(),      name='supplier_create'),
    path('<int:pk>/',               views.SupplierDetailView.as_view(),      name='supplier_detail'),
    path('<int:pk>/edit/',          views.SupplierUpdateView.as_view(),      name='supplier_update'),
    path('<int:pk>/toggle/',        views.SupplierToggleActiveView.as_view(),name='supplier_toggle'),
    path('<int:pk>/statement/',     views.SupplierStatementView.as_view(),   name='supplier_statement'),
    path('export/',                 views.SupplierExportView.as_view(),      name='supplier_export'),
]
