"""
URLs للنسخ الاحتياطي السحابي
"""

from django.urls import path
from . import views

app_name = 'cloud_backup'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('providers/', views.providers_list, name='providers'),
    path('providers/add/', views.add_provider, name='add_provider'),
    path('backup-now/', views.backup_now, name='backup_now'),
    path('backup/<uuid:uuid>/', views.backup_detail, name='backup_detail'),
    path('restore/<uuid:uuid>/', views.restore_backup, name='restore'),
    path('delete/<uuid:uuid>/', views.delete_backup, name='delete'),
    path('schedules/', views.schedules_list, name='schedules'),
    path('schedules/create/', views.create_schedule, name='create_schedule'),
    path('schedules/<int:schedule_id>/toggle/', views.toggle_schedule, name='toggle_schedule'),
]
