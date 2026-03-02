"""
URLs عروض الأسعار — RITA ERP
"""
from django.urls import path
from apps.quotations import views

app_name = 'quotations'

urlpatterns = [
    # اللوحة
    path('dashboard/', views.QuotationDashboardView.as_view(), name='quotation_dashboard'),

    # القائمة
    path('', views.QuotationListView.as_view(), name='quotation_list'),

    # إنشاء
    path('create/', views.QuotationCreateView.as_view(), name='quotation_create'),

    # تفاصيل
    path('<int:pk>/', views.QuotationDetailView.as_view(), name='quotation_detail'),

    # تعديل
    path('<int:pk>/edit/', views.QuotationUpdateView.as_view(), name='quotation_update'),

    # طباعة
    path('<int:pk>/print/', views.QuotationPrintView.as_view(), name='quotation_print'),

    # إجراءات
    path('<int:pk>/convert/', views.ConvertToInvoiceView.as_view(), name='convert_to_invoice'),
    path('<int:pk>/accept/', views.AcceptQuotationView.as_view(), name='quotation_accept'),
    path('<int:pk>/reject/', views.RejectQuotationView.as_view(), name='quotation_reject'),

    # متابعة
    path('<int:pk>/follow-up/', views.AddFollowUpView.as_view(), name='add_follow_up'),
    # واتساب ونسخ
    path('<int:pk>/send-whatsapp/', views.QuotationWhatsAppView.as_view(), name='quotation_whatsapp'),
    path('<int:pk>/duplicate/', views.QuotationDuplicateView.as_view(), name='quotation_duplicate'),
]
