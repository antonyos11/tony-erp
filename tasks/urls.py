"""
URLs لنظام المهام
"""

from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.task_list, name='list'),
    path('create/', views.task_create, name='task_create'),
    path('<int:task_id>/', views.task_detail, name='detail'),
    path('<int:task_id>/status/', views.task_update_status, name='update_status'),
    path('<int:task_id>/comment/', views.add_comment, name='add_comment'),
    
    path('subtask/<int:subtask_id>/toggle/', views.toggle_subtask, name='toggle_subtask'),
    
    path('reminders/', views.reminders_list, name='reminders'),
    path('reminders/create/', views.create_reminder, name='create_reminder'),
    path('reminders/<int:reminder_id>/snooze/', views.snooze_reminder, name='snooze_reminder'),
    path('reminders/<int:reminder_id>/dismiss/', views.dismiss_reminder, name='dismiss_reminder'),
    
    path('kanban/', views.kanban_board, name='kanban'),
    path('calendar/', views.calendar_view, name='calendar'),
]
