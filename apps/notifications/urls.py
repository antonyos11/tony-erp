from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('',                        views.NotificationListView.as_view(),   name='notification_list'),
    path('<int:pk>/read/',          views.MarkReadView.as_view(),           name='mark_read'),
    path('<int:pk>/delete/',        views.DeleteNotificationView.as_view(), name='delete'),
    path('mark-all-read/',          views.MarkAllReadView.as_view(),        name='mark_all_read'),
    path('clear-all/',              views.ClearAllNotificationsView.as_view(), name='clear_all'),
    path('unread-count/',           views.UnreadCountView.as_view(),        name='unread_count'),
    path('settings/',               views.NotificationSettingsView.as_view(), name='settings'),
]
