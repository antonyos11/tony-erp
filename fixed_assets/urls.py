from django.urls import path
from . import views

app_name = 'fixed_assets'

urlpatterns = [
    # Assets
    path('', views.asset_list, name='asset_list'),
    path('new/', views.asset_create, name='asset_create'),
    path('<int:pk>/', views.asset_detail, name='asset_detail'),
    path('<int:pk>/edit/', views.asset_edit, name='asset_edit'),
    path('<int:pk>/depreciate/', views.asset_depreciate, name='asset_depreciate'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    
    # Depreciation
    path('depreciation/schedule/', views.depreciation_schedule, name='depreciation_schedule'),
    path('depreciation/post/', views.post_monthly_depreciation, name='post_depreciation'),
    
    # Maintenance
    path('<int:asset_id>/maintenance/new/', views.maintenance_create, name='maintenance_create'),
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    
    # Transfer
    path('<int:asset_id>/transfer/', views.asset_transfer, name='asset_transfer'),
    
    # Reports
    path('reports/register/', views.asset_register, name='asset_register'),
    path('reports/depreciation/', views.depreciation_report, name='depreciation_report'),
]
