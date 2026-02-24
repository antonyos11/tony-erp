"""
URLs للتوقيعات الرقمية
"""

from django.urls import path
from . import views

app_name = 'digital_signatures'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('my-signature/', views.my_signature, name='my_signature'),
    path('create/', views.create_request, name='create_request'),
    path('request/<uuid:uuid>/', views.request_detail, name='request_detail'),
    path('sign/<uuid:uuid>/', views.sign_document, name='sign_document'),
    path('sign/<int:id>/', views.sign_document_by_id, name='sign'),
    path('reject/<uuid:uuid>/', views.reject_document, name='reject_document'),
    path('reject/<int:id>/', views.reject_document_by_id, name='reject'),
    path('reminder/<uuid:uuid>/', views.send_reminder, name='send_reminder'),
    path('download/<uuid:uuid>/', views.download_signed, name='download_signed'),
    path('download/<int:id>/', views.download_signed_by_id, name='download'),
    path('view/<int:id>/', views.view_document, name='view'),
    path('verify/<int:id>/', views.verify_document, name='verify'),
    path('templates/', views.templates_list, name='templates'),
]
