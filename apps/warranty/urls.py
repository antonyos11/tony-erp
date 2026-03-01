"""
URLs تطبيق الضمان — RITA ERP
"""
from django.urls import path
from apps.warranty import views

app_name = 'warranty'

urlpatterns = [
    path('activate/',                         views.WarrantyActivateView.as_view(),    name='warranty_activate'),
    path('search/',                            views.WarrantySearchView.as_view(),      name='warranty_search'),
    path('<int:pk>/',                          views.WarrantyDetailView.as_view(),      name='warranty_detail'),
    path('<int:warranty_pk>/claim/',           views.WarrantyClaimCreateView.as_view(), name='claim_create'),
    path('claim/new/',                         views.WarrantyClaimCreateView.as_view(), name='claim_create_generic'),
]
