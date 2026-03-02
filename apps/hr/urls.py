"""
URLs الموارد البشرية — RITA ERP
"""
from django.urls import path
from apps.hr import views

app_name = 'hr'

urlpatterns = [
    # الموظفون
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/terminate/', views.EmployeeTerminateView.as_view(), name='employee_terminate'),

    # الحضور والانصراف
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/bulk/', views.AttendanceBulkCreateView.as_view(), name='attendance_bulk'),

    # الإجازات
    path('leaves/', views.LeaveRequestListView.as_view(), name='leave_list'),
    path('leaves/create/', views.LeaveRequestCreateView.as_view(), name='leave_create'),
    path('leaves/<int:pk>/approve/', views.LeaveApproveView.as_view(), name='leave_approve'),

    # الجزاءات والمكافآت
    path('penalties/', views.PenaltyListView.as_view(), name='penalty_list'),
    path('penalties/create/', views.PenaltyCreateView.as_view(), name='penalty_create'),

    # السلف
    path('advances/', views.SalaryAdvanceListView.as_view(), name='advance_list'),
    path('advances/create/', views.SalaryAdvanceCreateView.as_view(), name='advance_create'),

    # مسيّرات الرواتب
    path('payroll/', views.PayrollListView.as_view(), name='payroll_list'),
    path('payroll/calculate/', views.PayrollCalculateView.as_view(), name='payroll_calculate'),
    path('payroll/<int:pk>/', views.PayrollDetailView.as_view(), name='payroll_detail'),
    path('payroll/<int:pk>/approve/', views.PayrollApproveView.as_view(), name='payroll_approve'),
    path('payroll/<int:pk>/pay/', views.PayrollPayView.as_view(), name='payroll_pay'),
    path('payroll/<int:pk>/payslip/<int:employee_pk>/', views.PayslipView.as_view(), name='payslip'),

    # الأقسام
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),

    # عمل بالقطعة
    path('piece-work/', views.PieceWorkListView.as_view(), name='piece_work_list'),
    path('piece-work/create/', views.PieceWorkCreateView.as_view(), name='piece_work_create'),
]
