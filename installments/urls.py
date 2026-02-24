"""
URLs لنظام التقسيط الذكي
"""
from django.urls import path
from . import views

app_name = 'installments'

urlpatterns = [
    # لوحة التحكم
    path('', views.dashboard, name='dashboard'),
    
    # خطط التقسيط
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/edit/', views.plan_edit, name='plan_edit'),
    
    # العقود
    path('contracts/', views.contract_list, name='contracts_list'),
    path('contracts/create/', views.contract_create, name='contract_create'),
    path('contracts/<int:pk>/', views.contract_detail, name='contract_detail'),
    path('contracts/<int:pk>/edit/', views.contract_edit, name='contract_edit'),
    path('contracts/<int:pk>/approve/', views.contract_approve, name='contract_approve'),
    path('contracts/<int:pk>/print/', views.print_contract, name='contract_print'),
    path('contracts/<int:contract_pk>/guarantor/add/', views.add_guarantor, name='add_guarantor'),
    
    # الأقساط
    path('installments/', views.installment_list, name='installment_list'),
    path('installments/overdue/', views.overdue_installments, name='overdue'),
    path('installments/<int:pk>/pay/', views.pay_installment, name='pay_installment'),
    path('installments/<int:pk>/pay-ajax/', views.pay_installment_ajax, name='pay_installment_ajax'),
    path('installments/<int:pk>/reminder/', views.send_reminder, name='send_reminder'),
    
    # التحصيل
    path('collection/', views.collection, name='collection'),
    
    # العملاء
    path('customers/', views.customer_list, name='customers'),
    
    # الحاسبة
    path('calculator/', views.calculator, name='calculator'),
    
    # التسوية المبكرة
    path('early-settlements/', views.early_settlement_list, name='early_settlement_list'),
    path('contracts/<int:contract_pk>/early-settlement/', views.early_settlement_create, name='early_settlement_create'),
    path('early-settlements/<int:pk>/', views.early_settlement_detail, name='early_settlement_detail'),
    path('early-settlements/<int:pk>/approve/', views.early_settlement_approve, name='early_settlement_approve'),
    path('early-settlements/<int:pk>/complete/', views.early_settlement_complete, name='early_settlement_complete'),
    
    # إعادة الجدولة
    path('reschedules/', views.reschedule_list, name='reschedule_list'),
    path('contracts/<int:contract_pk>/reschedule/', views.reschedule_create, name='reschedule_create'),
    path('reschedules/<int:pk>/', views.reschedule_detail, name='reschedule_detail'),
    path('reschedules/<int:pk>/approve/', views.reschedule_approve, name='reschedule_approve'),
    
    # نقل الملكية
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('contracts/<int:contract_pk>/transfer/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/approve/', views.transfer_approve, name='transfer_approve'),
    
    # التقييم الائتماني
    path('credit-scores/', views.credit_score_list, name='credit_score_list'),
    path('credit-scores/<int:customer_pk>/', views.credit_score_detail, name='credit_score_detail'),
    path('credit-scores/<int:customer_pk>/refresh/', views.credit_score_refresh, name='credit_score_refresh'),
    
    # إجراءات التحصيل
    path('collection-actions/', views.collection_actions_list, name='collection_actions_list'),
    path('installments/<int:installment_pk>/action/', views.collection_action_create, name='collection_action_create'),
    
    # الإعفاءات
    path('waivers/', views.waiver_list, name='waiver_list'),
    path('installments/<int:installment_pk>/waiver/', views.waiver_create, name='waiver_create'),
    path('waivers/<int:pk>/', views.waiver_detail, name='waiver_detail'),
    path('waivers/<int:pk>/approve/', views.waiver_approve, name='waiver_approve'),
    
    # الإعدادات
    path('settings/', views.settings_view, name='settings'),
    
    # API
    path('api/calculate/', views.api_calculate, name='api_calculate'),
    path('api/contracts/<int:pk>/stats/', views.api_contract_stats, name='api_contract_stats'),
    path('api/contracts/<int:pk>/summary/', views.api_contract_summary, name='api_contract_summary'),
    path('api/customers/<int:customer_pk>/credit/', views.api_check_credit, name='api_check_credit'),
    
    # التقارير
    path('reports/', views.reports, name='reports'),
    path('reports/export/', views.reports_export, name='reports_export'),
    path('reports/collection/', views.report_collection, name='report_collection'),
    path('reports/overdue/', views.report_overdue, name='report_overdue'),
    path('reports/customers/', views.report_customers, name='report_customers'),
    path('reports/forecast/', views.report_forecast, name='report_forecast'),
    path('reports/aging/', views.report_aging, name='report_aging'),
    
    # الطباعة
    path('print/contract/<int:pk>/', views.print_contract, name='print_contract'),
    path('print/schedule/<int:pk>/', views.print_schedule, name='print_schedule'),
    path('print/receipt/<int:pk>/', views.print_receipt, name='print_receipt'),
]
