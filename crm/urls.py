from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'crm'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('options/', views.crm_options, name='options'),
    
    # Customers URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customers/export/', views.customer_export, name='customer_export'),
    
    # Contact Persons URLs
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/create/', views.contact_create, name='contact_create'),
    path('customers/<int:customer_pk>/contacts/create/', views.contact_person_create, name='contact_person_create'),
    path('contacts/<int:pk>/edit/', views.contact_person_edit, name='contact_person_edit'),
    path('contacts/<int:pk>/delete/', views.contact_person_delete, name='contact_person_delete'),
    
    # Follow-ups URLs - المتابعات
    path('followups/', views.followup_list, name='followup_list'),
    path('followups/my/', views.my_followups, name='my_followups'),
    path('followups/create/', views.followup_create, name='followup_create'),
    path('followups/<int:pk>/', views.followup_detail, name='followup_detail'),
    path('followups/<int:pk>/edit/', views.followup_edit, name='followup_edit'),
    path('followups/<int:pk>/delete/', views.followup_delete, name='followup_delete'),
    path('followups/<int:pk>/complete/', views.followup_complete, name='followup_complete'),
    
    # Tasks URLs - المهام
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/complete/', views.task_complete, name='task_complete'),
    
    # Appointments URLs - المواعيد
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/calendar/', views.appointment_calendar, name='appointment_calendar'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),
    
    # Kanban Board - لوحة كانبان
    path('kanban/', views.kanban_board, name='kanban_board'),
    path('calendar/', views.crm_calendar, name='crm_calendar'),
    
    # Support Tickets URLs - طلبات الدعم الفني
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/<int:pk>/close/', views.ticket_close, name='ticket_close'),
    path('tickets/<int:pk>/comment/', views.ticket_add_comment, name='ticket_add_comment'),
    path('tickets/<int:pk>/assign/', views.ticket_assign, name='ticket_assign'),
    
    # Email URLs - البريد الإلكتروني
    path('email/', views.email_dashboard, name='email_dashboard'),
    path('email/send/', views.email_send, name='email_send'),
    path('email/templates/', views.email_templates, name='email_templates'),
    path('email/templates/create/', views.email_template_create, name='email_template_create'),
    path('email/templates/<int:pk>/edit/', views.email_template_edit, name='email_template_edit'),
    path('email/templates/<int:pk>/delete/', views.email_template_delete, name='email_template_delete'),
    path('email/log/', views.email_log, name='email_log'),
    path('email/settings/', views.email_settings, name='email_settings'),
    
    # WhatsApp URLs - الواتساب
    path('whatsapp/', views.whatsapp_dashboard, name='whatsapp_dashboard'),
    path('whatsapp/conversations/', views.whatsapp_conversations, name='whatsapp_conversations'),
    path('whatsapp/conversations/<int:pk>/', views.whatsapp_conversation_detail, name='whatsapp_conversation_detail'),
    path('whatsapp/bulk/', views.whatsapp_bulk, name='whatsapp_bulk'),
    path('whatsapp/bulk/create/', views.whatsapp_bulk_create, name='whatsapp_bulk_create'),
    path('whatsapp/templates/', views.whatsapp_templates, name='whatsapp_templates'),
    path('whatsapp/templates/create/', views.whatsapp_template_create, name='whatsapp_template_create'),
    path('whatsapp/templates/<int:pk>/edit/', views.whatsapp_template_edit, name='whatsapp_template_edit'),
    path('whatsapp/log/', views.whatsapp_log, name='whatsapp_log'),
    path('whatsapp/settings/', views.whatsapp_settings, name='whatsapp_settings'),
    
    # Campaigns URLs - الحملات التسويقية
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    path('campaigns/<int:pk>/launch/', views.campaign_launch, name='campaign_launch'),
    path('campaigns/<int:pk>/pause/', views.campaign_pause, name='campaign_pause'),
    path('campaigns/<int:pk>/report/', views.campaign_report, name='campaign_report'),
    path('analytics/', views.communication_analytics, name='communication_analytics'),
    
    # Contracts URLs - العقود
    path('contracts/', views.contract_list, name='contract_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<int:pk>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:pk>/edit/', views.contract_edit, name='contract_edit'),
    path('contracts/<int:pk>/delete/', views.contract_delete, name='contract_delete'),
    path('contracts/<int:pk>/renew/', views.contract_renew, name='contract_renew'),
    path('contracts/renewals/', views.contract_renewals, name='contract_renewals'),
    path('contracts/settings/', views.contract_settings, name='contract_settings'),
    
    # Quotations URLs - عروض الأسعار
    path('quotations/', views.quotation_list, name='quotation_list'),
    path('quotations/create/', views.quotation_create, name='quotation_create'),
    path('quotations/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    path('quotations/<int:pk>/print/', views.quotation_print, name='quotation_print'),
    path('quotations/<int:pk>/edit/', views.quotation_edit, name='quotation_edit'),
    path('quotations/<int:pk>/delete/', views.quotation_delete, name='quotation_delete'),
    path('quotations/<int:pk>/duplicate/', views.quotation_duplicate, name='quotation_duplicate'),
    path('quotations/<int:pk>/send/', views.quotation_send, name='quotation_send'),
    path('quotations/<int:pk>/accept/', views.quotation_accept, name='quotation_accept'),
    path('quotations/<int:pk>/reject/', views.quotation_reject, name='quotation_reject'),
    path('quotations/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
    path('quotations/<int:pk>/send-email/', views.quotation_send_email, name='quotation_send_email'),
    path('quotations/<int:pk>/convert/', views.quotation_convert_to_invoice, name='quotation_convert_to_invoice'),
    path('quotations/settings/', views.quotation_settings, name='quotation_settings'),
    
    # Service Plans URLs - الخطط والباقات
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/edit/', views.plan_edit, name='plan_edit'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),
    path('subscriptions/', views.subscription_list, name='subscription_list'),
    
    # Maintenance Contracts - تتبع عقود الصيانة
    path('maintenance-contracts/', views.maintenance_contracts, name='maintenance_contracts'),
    
    # Opportunities URLs
    path('opportunities/', views.opportunity_list, name='opportunity_list'),
    path('opportunities/kanban/', views.opportunity_kanban, name='opportunity_kanban'),
    path('opportunities/create/', views.opportunity_create, name='opportunity_create'),
    path('opportunities/<int:pk>/', views.opportunity_detail, name='opportunity_detail'),
    path('opportunities/<int:pk>/edit/', views.opportunity_edit, name='opportunity_edit'),
    path('opportunities/<int:pk>/delete/', views.opportunity_delete, name='opportunity_delete'),
    path('opportunities/<int:pk>/move/', views.opportunity_move_stage, name='opportunity_move_stage'),
    path('opportunities/<int:pk>/convert/', views.opportunity_convert, name='opportunity_convert'),
    
    # Activities URLs
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/calendar/', views.activity_calendar, name='activity_calendar'),
    path('activities/create/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activities/<int:pk>/delete/', views.activity_delete, name='activity_delete'),
    path('activities/<int:pk>/complete/', views.activity_complete, name='activity_complete'),
    
    # Reports URLs - التقارير
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/customers/', views.customer_report, name='customer_report'),
    path('reports/opportunities/', views.opportunity_report, name='opportunity_report'),
    path('reports/activities/', views.activity_report, name='activity_report'),
    path('reports/pipeline/', views.pipeline_report, name='pipeline_report'),
    path('reports/commissions/', views.commissions_report, name='commissions_report'),
    path('reports/support/', views.support_report, name='support_report'),
    path('reports/performance/', views.performance_report, name='performance_report'),
    path('reports/source-conversions/', views.source_conversions_report, name='source_conversions_report'),
    path('reports/trends/commissions/', views.commissions_trend, name='commissions_trend'),
    path('reports/trends/acceptance/', views.acceptance_trend, name='acceptance_trend'),
    
    # Settings URLs - الإعدادات
    path('settings/', views.crm_settings, name='settings'),
    path('settings/types/', views.customer_types, name='customer_types'),
    path('settings/sources/', views.customer_sources, name='customer_sources'),
    path('settings/stages/', views.opportunity_stages, name='opportunity_stages'),
    path('settings/activity-types/', views.activity_types, name='activity_types'),
    path('settings/ticket-categories/', views.ticket_categories, name='ticket_categories'),
    path('settings/business-activities/', views.business_activities, name='business_activities'),
    path('settings/regions/', views.regions, name='regions'),
    path('settings/rejection-reasons/', views.rejection_reasons, name='rejection_reasons'),
    path('settings/contract-types/', views.contract_types, name='contract_types'),
    path('settings/general/', views.general_settings, name='general_settings'),
    
    # Advanced System URLs - النظام المتقدم
    path('admin/roles/', views.admin_roles, name='admin_roles'),
    path('admin/teams/', views.admin_teams, name='admin_teams'),
    path('admin/user-assignments/', views.admin_user_assignments, name='admin_user_assignments'),
    path('admin/modules/', views.admin_modules, name='admin_modules'),
    path('admin/approvals/', views.admin_approvals, name='admin_approvals'),
    path('admin/system/', views.admin_system, name='admin_system'),
    
    # Currency Management - إدارة العملات
    path('currencies/', views.currency_list, name='currency_list'),
    
    # Redirects for expected paths
    path('customer-types/', RedirectView.as_view(pattern_name='crm:customer_types', permanent=False)),
    path('customer-sources/', RedirectView.as_view(pattern_name='crm:customer_sources', permanent=False)),
    path('opportunity-stages/', RedirectView.as_view(pattern_name='crm:opportunity_stages', permanent=False)),
    path('activity-types/', RedirectView.as_view(pattern_name='crm:activity_types', permanent=False)),
    path('ticket-categories/', RedirectView.as_view(pattern_name='crm:ticket_categories', permanent=False)),
    
    # AJAX and API endpoints
    path('ajax/customers/', views.ajax_customer_search, name='ajax_customer_search'),
    path('ajax/customers/create/', views.ajax_create_customer, name='ajax_create_customer'),
    path('ajax/contacts/<int:customer_id>/', views.ajax_get_contacts, name='ajax_get_contacts'),
    path('ajax/contacts/create/', views.ajax_create_contact, name='ajax_create_contact'),
    path('ajax/opportunities/stage/<int:stage_id>/', views.ajax_opportunities_by_stage, name='ajax_opportunities_by_stage'),
    path('ajax/dashboard-stats/', views.ajax_dashboard_stats, name='ajax_dashboard_stats'),
    path('ajax/product/<int:product_id>/price/', views.ajax_product_price, name='ajax_product_price'),
    
    # Quick actions
    path('quick/customer/', views.quick_add_customer, name='quick_add_customer'),
    path('quick/opportunity/', views.quick_add_opportunity, name='quick_add_opportunity'),
    path('quick/activity/', views.quick_add_activity, name='quick_add_activity'),
    
    # Bulk operations
    path('bulk/customers/delete/', views.bulk_delete_customers, name='bulk_delete_customers'),
    path('bulk/opportunities/stage/', views.bulk_move_opportunities, name='bulk_move_opportunities'),
    path('bulk/activities/complete/', views.bulk_complete_activities, name='bulk_complete_activities'),
]

# --- Advanced CRM URLs ---
from crm import views_advanced as crm_adv  # noqa: E402

urlpatterns += [
    # قواعد المتابعة
    path('followup-rules/', crm_adv.followup_rule_list, name='followup_rule_list'),
    path('followup-rules/create/', crm_adv.followup_rule_create, name='followup_rule_create'),
    path('followup-rules/<int:pk>/edit/', crm_adv.followup_rule_edit, name='followup_rule_edit'),
    path('followup-rules/<int:pk>/delete/', crm_adv.followup_rule_delete, name='followup_rule_delete'),

    # سجل المتابعات
    path('followup-logs/', crm_adv.followup_log_list, name='followup_log_list'),

    # تقييم العملاء
    path('lead-scores/', crm_adv.lead_score_list, name='lead_score_list'),
    path('lead-scores/<int:pk>/', crm_adv.lead_score_detail, name='lead_score_detail'),

    # اتفاقيات SLA
    path('sla/', crm_adv.sla_list, name='sla_list'),
    path('sla/create/', crm_adv.sla_create, name='sla_create'),
    path('sla/<int:pk>/edit/', crm_adv.sla_edit, name='sla_edit'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('contact-detail/<int:pk>/', stub_view, name='contact_detail'),
    path('contact-edit/<int:pk>/', stub_view, name='contact_edit'),
]
