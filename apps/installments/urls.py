"""
URLs تطبيق الأقساط — RITA ERP
"""
from django.urls import path
from apps.installments import views

app_name = 'installments'

urlpatterns = [
    path('',                  views.InstallmentPlanListView.as_view(),   name='plan_list'),
    path('create/',           views.InstallmentPlanCreateView.as_view(), name='plan_create'),
    path('<int:pk>/',         views.InstallmentPlanDetailView.as_view(), name='plan_detail'),
    path('pay/<int:pk>/',     views.PayInstallmentView.as_view(),        name='pay_installment'),
    path('overdue/',          views.OverdueInstallmentsView.as_view(),   name='overdue_list'),
]
