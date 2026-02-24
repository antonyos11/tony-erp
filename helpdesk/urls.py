from django.urls import path
from . import views

app_name = 'helpdesk'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('knowledge-base/<slug:slug>/', views.article_detail, name='article_detail'),
]
