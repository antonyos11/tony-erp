"""
URLs للمستندات التعاونية
"""

from django.urls import path
from . import views

app_name = 'collaborative_docs'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_document, name='create'),
    path('edit/<uuid:doc_uuid>/', views.edit_document, name='edit'),
    path('save/<uuid:doc_uuid>/', views.save_document, name='save'),
    path('share/<uuid:doc_uuid>/', views.share_document, name='share'),
    path('comment/<uuid:doc_uuid>/', views.add_comment, name='add_comment'),
    path('versions/<uuid:doc_uuid>/', views.get_versions, name='versions'),
    path('restore/<uuid:doc_uuid>/<int:version_id>/', views.restore_version, name='restore'),
    path('folder/', views.folder_contents, name='folder_root'),
    path('folder/<int:folder_id>/', views.folder_contents, name='folder'),
    path('folder/create/', views.create_folder, name='create_folder'),
]
