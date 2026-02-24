"""
URLs لمنشئ التقارير
"""

from django.urls import path
from . import views

app_name = 'report_builder'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.report_list, name='list'),
    path('create/', views.create_report, name='create'),
    path('builder/<uuid:uuid>/', views.report_builder, name='builder'),
    path('save/<uuid:uuid>/', views.save_report, name='save'),
    path('preview/<uuid:uuid>/', views.preview_report, name='preview'),
    path('execute/<uuid:uuid>/', views.execute_report, name='execute'),
    path('export/<uuid:uuid>/', views.export_report, name='export'),
    path('delete/<uuid:uuid>/', views.delete_report, name='delete'),
    path('api/fields/<int:content_type_id>/', views.get_model_fields, name='get_fields'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('edit/<int:pk>/', stub_view, name='edit'),
    path('run/', stub_view, name='run'),
]
