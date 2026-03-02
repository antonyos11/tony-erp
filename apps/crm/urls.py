"""
URLs تطبيق CRM — RITA ERP
"""
from django.urls import path
from apps.crm import views

app_name = 'crm'

urlpatterns = [
    # لوحة CRM
    path('', views.CRMDashboardView.as_view(), name='dashboard'),

    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/kanban/', views.LeadKanbanView.as_view(), name='lead_kanban'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_update'),
    path('leads/<int:pk>/convert/', views.LeadConvertView.as_view(), name='lead_convert'),

    # ملف العميل
    path('customers/<int:pk>/profile/', views.CustomerProfileView.as_view(), name='customer_profile'),
    path('customers/search/', views.CustomerSearchView.as_view(), name='customer_search'),

    # التفاعلات
    path('interactions/', views.InteractionListView.as_view(), name='interaction_list'),
    path('interactions/create/', views.InteractionCreateView.as_view(), name='interaction_create'),
    path('interactions/<int:pk>/done/', views.mark_follow_up_done, name='follow_up_done'),
    path('follow-ups/', views.FollowUpListView.as_view(), name='follow_up_list'),

    # الشكاوى
    path('complaints/', views.ComplaintListView.as_view(), name='complaint_list'),
    path('complaints/create/', views.ComplaintCreateView.as_view(), name='complaint_create'),
    path('complaints/<int:pk>/', views.ComplaintDetailView.as_view(), name='complaint_detail'),
    path('complaints/<int:pk>/resolve/', views.ComplaintResolveView.as_view(), name='complaint_resolve'),

    # المهام
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/complete/', views.TaskCompleteView.as_view(), name='task_complete'),

    # المجموعات
    path('groups/', views.CustomerGroupListView.as_view(), name='group_list'),
    path('groups/create/', views.CustomerGroupCreateView.as_view(), name='group_create'),

    # التقارير
    path('reports/ratings/', views.CustomerRatingReportView.as_view(), name='rating_report'),
    path('reports/lead-sources/', views.LeadSourceReportView.as_view(), name='lead_source_report'),
    path('reports/salesman/', views.SalesmanPerformanceView.as_view(), name='salesman_report'),
]
