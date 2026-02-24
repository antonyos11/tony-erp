from django.urls import path
from . import views

app_name = 'exports'

urlpatterns = [
    # قائمة التصدير الرئيسية
    path('', views.export_list, name='export_list'),
    path('history/', views.export_history, name='export_history'),

    # عمليات التصدير
    path('create/', views.export_create, name='export_create'),
    path('status/<int:export_id>/', views.export_status, name='export_status'),
    path('download/<int:export_id>/', views.export_download, name='export_download'),

    # النسخ الاحتياطية
    path('backups/', views.backup_list, name='backup_list'),
]
