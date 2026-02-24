from django.urls import path
from . import views

app_name = 'tender_bidding'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('tenders/', views.tender_list, name='tender_list'),
    path('tenders/create/', views.tender_create, name='tender_create'),
    path('tenders/<int:pk>/', views.tender_detail, name='tender_detail'),
    path('tenders/<int:pk>/edit/', views.tender_edit, name='tender_edit'),
    path('tenders/<int:pk>/delete/', views.tender_delete, name='tender_delete'),
    path('bids/', views.bid_list, name='bid_list'),
    path('bids/create/', views.bid_create, name='bid_create'),
    path('bids/<int:pk>/', views.bid_detail, name='bid_detail'),
]
