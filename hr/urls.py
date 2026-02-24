from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_wage_production
from . import views_employee_portal
from . import views_loans
from . import api_views

# DRF REST API Router
hr_api_router = DefaultRouter()
hr_api_router.register(r'employees', api_views.EmployeeViewSet, basename='api-employees')
hr_api_router.register(r'departments', api_views.DepartmentViewSet, basename='api-departments')
hr_api_router.register(r'positions', api_views.JobPositionViewSet, basename='api-positions')

app_name = 'hr'

urlpatterns = [ 
    # لوحة التحكم الرئيسية
    path('', views.hr_dashboard, name='dashboard'),
    
    # بوابة الموظف (Self-Service Portal)
    path('portal/', views_employee_portal.employee_portal, name='employee_portal'),
    path('portal/leave/', views_employee_portal.submit_leave_request, name='employee_portal_leave'),
    path('portal/production/', views_employee_portal.submit_production_entry, name='employee_portal_production'),
    path('portal/stats/', views_employee_portal.get_production_stats, name='employee_portal_stats'),
    path('portal/photo/', views_employee_portal.upload_employee_photo, name='employee_portal_photo'),

    # صفحة الترحيب قبل الدخول للنظام
    path('welcome/', views_employee_portal.employee_welcome, name='employee_welcome'),
    path('welcome/attendance/', views_employee_portal.register_attendance, name='employee_welcome_attendance'),
    path('welcome/attendance/status/', views_employee_portal.check_attendance_status, name='employee_welcome_attendance_status'),
    
    # إدارة الموظفين
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    
    # استيراد وتصدير الموظفين
    path('employees/import/', views.employee_import, name='employee_import'),
    path('employees/export/', views.employee_export, name='employee_export'),
    path('employees/export/<str:format>/', views.employee_export, name='employee_export_format'),
    
    # API endpoints for AJAX calls
    path('api/positions/', views.get_positions_by_department, name='get_positions_by_department'),
    
    # إدارة الأقسام والمناصب
    path('departments/', views.department_list, name='department_list'),
    path('departments/', views.department_list, name='departments'),
    path('departments/create/', views.department_create, name='department_create'),
    path('positions/', views.position_list, name='position_list'),
    path('positions/', views.position_list, name='positions'),
    path('positions/create/', views.position_create, name='position_create'),
    
    # نظام الحضور والانصراف
    path('attendance/', views.attendance_dashboard, name='attendance_dashboard'),
    path('attendance/records/', views.attendance_records, name='attendance_records'),
    path('attendance/employee/<int:employee_id>/', views.attendance_employee, name='attendance_employee'),
    path('attendance/manual-entry/', views.manual_attendance_entry, name='manual_attendance_entry'),
    path('attendance/check-in/', views.check_in, name='check_in'),
    path('attendance/check-out/', views.check_out, name='check_out'),
    
    # إدارة الإجازات
    path('leaves/', views.leave_dashboard, name='leave_dashboard'),
    path('leaves/employee/<int:employee_id>/', views.leave_employee, name='leave_employee'),
    path('leaves/request/create/', views.leave_request_create, name='leave_request_create'),
    path('leaves/request/', views.leave_request_list, name='leave_request_list'),
    path('leaves/request/<int:pk>/', views.leave_request_detail, name='leave_request_detail'),
    path('leaves/request/<int:pk>/approve/', views.leave_request_approve, name='leave_request_approve'),
    path('leaves/request/<int:pk>/reject/', views.leave_request_reject, name='leave_request_reject'),
    
    # إدارة الرواتب
    path('payroll/', views.payroll_dashboard, name='payroll_dashboard'),
    path('payroll/employee/<int:employee_id>/', views.payroll_employee, name='payroll_employee'),
    path('payroll/generate/', views.payroll_generate, name='payroll_generate'),
    path('payroll/list/', views.payroll_list, name='payroll_list'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/approve/', views.payroll_approve, name='payroll_approve'),
    path('payroll/report/', views.payroll_report, name='payroll_report'),
    path('payroll/<int:pk>/payslip.pdf', views.payroll_payslip_pdf, name='payroll_payslip_pdf'),
    
    # === مفردات المرتب - البدلات والخصومات ===
    path('payroll/items/', views.payroll_items_dashboard, name='payroll_items_dashboard'),
    path('payroll/allowance-types/', views.allowance_type_list, name='allowance_type_list'),
    path('payroll/allowance-types/create/', views.allowance_type_create, name='allowance_type_create'),
    path('payroll/allowance-types/<int:pk>/edit/', views.allowance_type_edit, name='allowance_type_edit'),
    path('payroll/allowance-types/<int:pk>/delete/', views.allowance_type_delete, name='allowance_type_delete'),
    path('payroll/deduction-types/', views.deduction_type_list, name='deduction_type_list'),
    path('payroll/deduction-types/create/', views.deduction_type_create, name='deduction_type_create'),
    path('payroll/deduction-types/<int:pk>/edit/', views.deduction_type_edit, name='deduction_type_edit'),
    path('payroll/deduction-types/<int:pk>/delete/', views.deduction_type_delete, name='deduction_type_delete'),
    path('payroll/employee-allowances/', views.employee_allowance_list, name='employee_allowance_list'),
    path('payroll/employee-allowances/create/', views.employee_allowance_create, name='employee_allowance_create'),
    path('payroll/employee-deductions/', views.employee_deduction_list, name='employee_deduction_list'),
    path('payroll/employee-deductions/create/', views.employee_deduction_create, name='employee_deduction_create'),
    
    # إدارة الأداء
    path('performance/', views.performance_dashboard, name='performance_dashboard'),
    path('performance/reviews/', views.performance_review_list, name='performance_review_list'),
    path('performance/reviews/create/', views.performance_review_create, name='performance_review_create'),
    path('performance/reviews/<int:pk>/', views.performance_review_detail, name='performance_review_detail'),
    
    # === نظام الأهداف والتارجت المتطور ===
    path('targets/', views.targets_dashboard, name='targets_dashboard'),
    path('targets/list/', views.targets_list, name='targets_list'),
    path('targets/create/', views.target_create, name='target_create'),
    path('targets/<int:pk>/', views.target_detail, name='target_detail'),
    path('targets/<int:pk>/update-progress/', views.target_update_progress, name='target_update_progress'),
    path('targets/employee/<int:employee_id>/', views.employee_targets, name='employee_targets'),
    path('targets/teams/', views.team_targets_list, name='team_targets_list'),
    path('performance/analytics/', views.performance_analytics, name='performance_analytics'),
    
    # إدارة التدريب والتطوير
    path('training/', views.training_dashboard, name='training_dashboard'),
    path('training/programs/', views.training_program_list, name='training_program_list'),
    path('training/programs/create/', views.training_program_create, name='training_program_create'),
    path('training/programs/<int:pk>/', views.training_program_detail, name='training_program_detail'),
    path('training/enroll/', views.training_enroll, name='training_enroll'),

    # إدارة التوظيف
    path('recruitment/', views.recruitment_dashboard, name='recruitment_dashboard'),
    path('recruitment/vacancies/', views.job_vacancy_list, name='job_vacancy_list'),
    path('recruitment/vacancies/create/', views.job_vacancy_create, name='job_vacancy_create'),
    path('recruitment/applications/', views.job_application_list, name='job_application_list'),
    path('recruitment/applications/<int:pk>/', views.job_application_detail, name='job_application_detail'),

    # العلاقات العمالية
    path('relations/', views.relations_dashboard, name='relations_dashboard'),
    path('relations/complaints/', views.complaint_list, name='complaint_list'),
    path('relations/disciplinary/', views.disciplinary_list, name='disciplinary_list'),

    # السلامة والصحة المهنية
    path('hse/', views.hse_dashboard, name='hse_dashboard'),
    path('hse/incidents/', views.hse_incident_list, name='hse_incident_list'),
    path('hse/inspections/', views.hse_inspection_list, name='hse_inspection_list'),
    path('hse/trainings/', views.hse_training_list, name='hse_training_list'),

    # السياسات واللوائح
    path('policies/', views.policies, name='policies'),
    
    # التقارير
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # =====================
    # بوابة الموظفين - الخدمة الذاتية
    # =====================
    path('employee-portal/', views.employee_portal, name='employee_portal'),
    path('employee-portal/leave/submit/', views.employee_submit_leave_request, name='employee_submit_leave_request'),
    
    # إدارة الموافقات على الإجازات
    path('leave-approval/', views.leave_approval_dashboard, name='leave_approval_dashboard'),
    path('leave-approval/<int:request_id>/approve/', views.approve_leave_request, name='approve_leave_request'),
    path('leave-approval/<int:request_id>/reject/', views.reject_leave_request, name='reject_leave_request'),
    
    # بطاقات الهوية
    path('id-cards/', views.employee_id_cards_list, name='employee_id_cards_list'),
    path('id-cards/generate/<int:employee_id>/', views.generate_employee_id_card, name='generate_employee_id_card'),
    path('id-cards/print/<int:card_id>/', views.print_employee_id_card, name='print_employee_id_card'),
    path('id-cards/preview/<int:card_id>/', views.id_card_preview, name='id_card_preview'),
    
    # تسجيل الدخول بـ QR Code
    path('qr-login/', views.qr_login_scanner, name='qr_login_scanner'),
    path('qr-login/action/', views.qr_attendance_action, name='qr_attendance_action'),
    
    # =====================
    # نظام تكامل الأجور مع الإنتاج
    # =====================
    path('wage-production/', views_wage_production.wage_production_dashboard, name='wage_production_dashboard'),
    path('wage-production/employee/<int:employee_id>/', views_wage_production.employee_productivity_report, name='employee_productivity_report'),
    path('wage-production/ranking/', views_wage_production.productivity_ranking, name='productivity_ranking'),
    path('wage-production/calculate-wage/', views_wage_production.calculate_piece_rate_wage, name='calculate_piece_rate_wage'),
    path('wage-production/order/<int:order_id>/labor-cost/', views_wage_production.production_order_labor_cost, name='production_order_labor_cost'),
    path('wage-production/generate-payroll/', views_wage_production.generate_payroll_from_production, name='generate_payroll_from_production'),
    path('wage-production/analytics/', views_wage_production.wage_analytics_report, name='wage_analytics_report'),
    path('wage-production/export-csv/', views_wage_production.export_productivity_csv, name='export_productivity_csv'),
    path('wage-production/ajax/productivity/', views_wage_production.productivity_ajax, name='productivity_ajax'),
    path('wage-production/ajax/update-labor-cost/', views_wage_production.update_production_labor_cost, name='update_production_labor_cost'),
    
    # =============================
    # URLs إضافية لبطاقات الهوية
    # =============================
    path('id-cards/<int:card_id>/deactivate/', views.id_card_deactivate, name='id_card_deactivate'),
    path('id-cards/<int:card_id>/pdf/', views.id_card_print_pdf, name='id_card_print_pdf'),
    
    # =============================
    # نظام بطاقات التعريف المتقدم
    # =============================
    # إنشاء البطاقات
    path('id-cards/select-employee/', views.id_card_select_employee, name='id_card_select_employee'),
    path('id-cards/create/', views.id_card_create_single, name='id_card_create_single'),
    path('id-cards/bulk-create/', views.id_card_bulk_create, name='id_card_bulk_create'),
    
    # التحميل والطباعة
    path('id-cards/<int:card_id>/download-pdf/', views.id_card_download_pdf, name='id_card_download_pdf'),
    path('id-cards/<int:card_id>/download-pvc/', views.id_card_download_pvc, name='id_card_download_pvc'),
    path('id-cards/<int:card_id>/revoke/', views.id_card_revoke, name='id_card_revoke'),
    path('id-cards/<int:card_id>/lost-replacement/', views.id_card_lost_replacement, name='id_card_lost_replacement'),
    path('id-cards/employee/<int:employee_id>/history/', views.id_card_history, name='id_card_history'),
    
    # إدارة الدفعات
    path('id-cards/batches/', views.id_card_batch_list, name='id_card_batch_list'),
    path('id-cards/batch/<int:batch_id>/preview/', views.id_card_batch_preview, name='id_card_batch_preview'),
    path('id-cards/batch/<int:batch_id>/print-pdf/', views.id_card_batch_print_pdf, name='id_card_batch_print_pdf'),
    
    # قوالب التصميم
    path('id-cards/templates/', views.id_card_template_list, name='id_card_template_list'),
    path('id-cards/templates/create/', views.id_card_template_create, name='id_card_template_create'),
    path('id-cards/templates/<int:template_id>/edit/', views.id_card_template_edit, name='id_card_template_edit'),
    path('id-cards/templates/<int:template_id>/delete/', views.id_card_template_delete, name='id_card_template_delete'),
    
    # التحقق والتقارير
    path('id-cards/verify-qr/', views.id_card_verify_qr, name='id_card_verify_qr'),
    path('id-cards/reports/', views.id_card_reports, name='id_card_reports'),
    
    # =============================
    # إدارة سلف الموظفين
    # =============================
    path('loans/', views_loans.loans_dashboard, name='loans_dashboard'),
    path('loans/list/', views_loans.loans_list, name='loans_list'),
    path('loans/request/', views_loans.loan_request, name='loan_request'),
    path('loans/<int:pk>/', views_loans.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/receipt/', views_loans.loan_receipt, name='loan_receipt'),
    path('loans/<int:pk>/approve/', views_loans.loan_approve, name='loan_approve'),
    path('loans/installment/<int:pk>/defer/', views_loans.installment_defer, name='installment_defer'),
    path('loans/employee/<int:employee_id>/', views_loans.employee_loans, name='employee_loans'),
    path('loans/api/employee/<int:employee_id>/', views_loans.get_employee_loan_info, name='get_employee_loan_info'),
    
    # كشف الراتب الشامل
    path('payroll/comprehensive-report/', views_loans.payroll_comprehensive_report, name='payroll_comprehensive_report'),
]
# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('department-delete/<int:pk>/', stub_view, name='department_delete'),
    path('department-edit/<int:pk>/', stub_view, name='department_edit'),
    path('position-detail/<int:pk>/', stub_view, name='position_detail'),
    path('position-edit/<int:pk>/', stub_view, name='position_edit'),
]

# REST API v1 endpoints
urlpatterns += [
    path('api/v1/', include(hr_api_router.urls)),
]
