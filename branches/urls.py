"""
URLs وحدة الفروع الموحدة
"""
from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    # Dashboard
    path('', views.branches_dashboard, name='dashboard'),
    
    # ==================== الفروع ====================
    path('list/', views.branch_list, name='branch_list'),
    path('create/', views.branch_create, name='branch_create'),
    path('<int:pk>/', views.branch_detail, name='branch_detail'),
    path('<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('<int:pk>/delete/', views.branch_delete, name='branch_delete'),
    path('<int:pk>/toggle-status/', views.branch_toggle_status, name='branch_toggle_status'),
    
    # ==================== التحويلات ====================
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/approve/', views.transfer_approve, name='transfer_approve'),
    path('transfers/<int:pk>/ship/', views.transfer_ship, name='transfer_ship'),
    path('transfers/<int:pk>/receive/', views.transfer_receive, name='transfer_receive'),
    path('transfers/<int:pk>/cancel/', views.transfer_cancel, name='transfer_cancel'),
    
    # ==================== الموظفين ====================
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    
    # ==================== المصروفات ====================
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    
    # ==================== الحضور ====================
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/punch/', views.attendance_punch, name='attendance_punch'),
    
    # ==================== أجهزة نقاط البيع ====================
    path('pos-devices/', views.pos_device_list, name='pos_device_list'),
    path('pos-devices/create/', views.pos_device_create, name='pos_device_create'),
    
    # ==================== الرواتب ====================
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/create/', views.payroll_create, name='payroll_create'),
    
    # ==================== الورديات ====================
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/create/', views.shift_create, name='shift_create'),
    
    # ==================== التقارير ====================
    path('reports/<int:pk>/stock/', views.branch_stock_report, name='branch_stock_report'),
    path('reports/transfers/', views.transfer_report, name='transfer_report'),
    path('reports/expenses/', views.expense_report, name='expense_report'),
    path('reports/consolidated/', views.consolidated_report, name='consolidated_report'),
    
    # ==================== API ====================
    path('api/list/', views.api_branches_list, name='api_branches_list'),
    path('api/<int:pk>/stock/', views.api_branch_stock, name='api_branch_stock'),
    path('api/<int:pk>/staff/', views.api_branch_staff, name='api_branch_staff'),
    path('api/staff/', views.api_staff_by_branch, name='api_staff_by_branch'),
]

# --- Advanced Branch URLs ---
from branches import views_advanced as br_adv  # noqa: E402

urlpatterns += [
    # أهداف الفروع
    path('targets/', br_adv.target_list, name='target_list'),
    path('targets/create/', br_adv.target_create, name='target_create'),
    path('targets/<int:pk>/', br_adv.target_detail, name='target_detail'),
    path('targets/<int:pk>/edit/', br_adv.target_edit, name='target_edit'),

    # التحويلات بين الفروع
    path('inter-transfers/', br_adv.inter_transfer_list, name='inter_transfer_list'),
    path('inter-transfers/create/', br_adv.inter_transfer_create, name='inter_transfer_create'),
    path('inter-transfers/<int:pk>/', br_adv.inter_transfer_detail, name='inter_transfer_detail'),
    path('inter-transfers/<int:pk>/approve/', br_adv.inter_transfer_approve, name='inter_transfer_approve'),
    path('inter-transfers/<int:pk>/receive/', br_adv.inter_transfer_receive, name='inter_transfer_receive'),

    # ربحية الفروع
    path('profitability/', br_adv.profitability_list, name='profitability_list'),
    path('profitability/<int:pk>/', br_adv.profitability_detail, name='profitability_detail'),
]

# --- Stub URL patterns (auto-generated) ---

from core.views_stub import stub_view  # noqa: E402

urlpatterns += [
    path('attendance-create/', stub_view, name='attendance_create'),
    path('create-location/', stub_view, name='create_location'),
    path('edit-location/<int:pk>/', stub_view, name='edit_location'),
    path('expense-edit/<int:pk>/', stub_view, name='expense_edit'),
    path('location-detail/<int:pk>/', stub_view, name='location_detail'),
    path('payroll-detail/<int:pk>/', stub_view, name='payroll_detail'),
    path('pos-device-delete/<int:pk>/', stub_view, name='pos_device_delete'),
    path('pos-device-update/<int:pk>/', stub_view, name='pos_device_update'),
    path('set-current-location/', stub_view, name='set_current_location'),
    path('toggle-status/', stub_view, name='toggle_status'),
    path('unified-dashboard/', stub_view, name='unified_dashboard'),
    path('unified-list/', stub_view, name='unified_list'),
]
