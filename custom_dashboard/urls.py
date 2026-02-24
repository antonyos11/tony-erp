"""
URLs للوحة التحكم المخصصة
"""

from django.urls import path
from . import views

app_name = 'custom_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # التخطيطات
    path('layouts/', views.layouts_list, name='layouts'),
    path('layouts/create/', views.create_layout, name='create_layout'),
    path('layouts/<int:layout_id>/update/', views.update_layout, name='update_layout'),
    path('layouts/<int:layout_id>/default/', views.set_default_layout, name='set_default'),
    path('layouts/<int:layout_id>/delete/', views.delete_layout, name='delete_layout'),
    path('layouts/<int:layout_id>/positions/', views.save_layout_positions, name='save_positions'),
    
    # الويدجتس
    path('layouts/<int:layout_id>/add-widget/', views.add_widget, name='add_widget'),
    path('widgets/<int:widget_id>/position/', views.update_widget_position, name='update_position'),
    path('widgets/<int:widget_id>/toggle/', views.toggle_widget, name='toggle_widget'),
    path('widgets/<int:widget_id>/remove/', views.remove_widget, name='remove_widget'),
    path('widgets/<int:widget_id>/data/', views.get_widget_data, name='widget_data'),
    path('widgets/available/', views.available_widgets, name='available_widgets'),
    
    # الإجراءات السريعة
    path('quick-actions/', views.quick_actions_list, name='quick_actions'),
    path('quick-actions/create/', views.create_quick_action, name='create_quick_action'),
    path('quick-actions/<int:action_id>/delete/', views.delete_quick_action, name='delete_quick_action'),
]
