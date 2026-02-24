#!/usr/bin/env python
"""
سكربت لإصلاح عناوين صفحات النماذج
"""
import os
import re

BASE_DIR = '/var/www/tony_erp'
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# تخطيط العناوين للوحدات المختلفة
TITLE_MAP = {
    # eservices
    'eservices/recharge_form.html': ('إعادة شحن', 'bi-phone', 'eservices'),
    'eservices/bill_form.html': ('دفع فاتورة', 'bi-file-text', 'eservices'),
    'eservices/category_form.html': ('تصنيف خدمة', 'bi-folder', 'eservices'),
    'eservices/transfer_form.html': ('تحويل رصيد', 'bi-arrow-left-right', 'eservices'),
    'eservices/service_form.html': ('خدمة إلكترونية', 'bi-phone', 'eservices'),
    'eservices/provider_form.html': ('مقدم خدمة', 'bi-building', 'eservices'),
    'eservices/operator_form.html': ('مشغل اتصالات', 'bi-broadcast', 'eservices'),
    
    # partners
    'partners/partner_form.html': ('شريك تجاري', 'bi-people-fill', 'partners'),
    
    # production
    'production/work_center_form.html': ('مركز عمل', 'bi-gear-fill', 'production'),
    'production/order_form.html': ('أمر إنتاج', 'bi-gear-fill', 'production'),
    'production/warranty/register_form.html': ('تسجيل ضمان', 'bi-shield-check', 'production'),
    
    # hr
    'hr/employee_form.html': ('موظف', 'bi-person-badge', 'hr'),
    'hr/employee_allowance_form.html': ('بدل موظف', 'bi-cash-stack', 'hr'),
    'hr/employee_deduction_form.html': ('خصم موظف', 'bi-dash-circle', 'hr'),
    'hr/training_enroll_form.html': ('تسجيل تدريب', 'bi-mortarboard', 'hr'),
    'hr/training_program_form.html': ('برنامج تدريب', 'bi-book', 'hr'),
    'hr/allowance_type_form.html': ('نوع بدل', 'bi-cash', 'hr'),
    'hr/deduction_type_form.html': ('نوع خصم', 'bi-dash-circle', 'hr'),
    'hr/department_form.html': ('قسم', 'bi-diagram-3', 'hr'),
    'hr/position_form.html': ('منصب وظيفي', 'bi-briefcase', 'hr'),
    'hr/target_form.html': ('هدف أداء', 'bi-bullseye', 'hr'),
    'hr/job_vacancy_form.html': ('وظيفة شاغرة', 'bi-person-plus', 'hr'),
    'hr/manual_attendance_form.html': ('تسجيل حضور', 'bi-clock', 'hr'),
    'hr/leave_request_form.html': ('طلب إجازة', 'bi-calendar-check', 'hr'),
    'hr/performance_review_form.html': ('تقييم أداء', 'bi-star', 'hr'),
    
    # shipping
    'shipping/shipment_form.html': ('شحنة', 'bi-truck', 'shipping'),
    'shipping/zone_form.html': ('منطقة شحن', 'bi-geo-alt', 'shipping'),
    'shipping/rate_form.html': ('سعر شحن', 'bi-currency-dollar', 'shipping'),
    'shipping/company_form.html': ('شركة شحن', 'bi-building', 'shipping'),
    'shipping/pickup_form.html': ('طلب استلام', 'bi-box-arrow-up', 'shipping'),
    
    # projects
    'projects/project_form.html': ('مشروع', 'bi-kanban', 'projects'),
    'projects/labour/attendance_form.html': ('حضور عمال', 'bi-clock', 'projects'),
    
    # maintenance
    'maintenance/maintenance_request_form.html': ('طلب صيانة', 'bi-wrench', 'maintenance'),
    'maintenance/maintenance_schedule_form.html': ('جدولة صيانة', 'bi-calendar3', 'maintenance'),
    'maintenance/machine_form.html': ('ماكينة', 'bi-gear-wide-connected', 'maintenance'),
    
    # home_services
    'home_services/admin/package_form.html': ('باقة خدمات', 'bi-box', 'home_services'),
    'home_services/admin/category_form.html': ('تصنيف خدمات', 'bi-folder', 'home_services'),
    
    # purchases
    'purchases/purchase_return_form.html': ('مرتجع مشتريات', 'bi-arrow-return-left', 'purchases'),
    
    # accounting
    'accounting/fiscal_year_form.html': ('سنة مالية', 'bi-calendar2-check', 'accounting'),
    'accounting/cheque_form.html': ('شيك', 'bi-credit-card', 'accounting'),
    
    # inventory
    'inventory/location_form.html': ('موقع مخزني', 'bi-geo-alt-fill', 'inventory'),
    
    # contracting
    'contracting/attendance_form.html': ('حضور مقاولات', 'bi-clock', 'contracting'),
    'contracting/contract_form.html': ('عقد مقاولة', 'bi-file-earmark-text', 'contracting'),
    'contracting/equipment_form.html': ('معدة', 'bi-tools', 'contracting'),
    'contracting/expense_form.html': ('مصروف مقاولات', 'bi-cash', 'contracting'),
    'contracting/material_form.html': ('مادة بناء', 'bi-box-seam', 'contracting'),
    'contracting/project_form.html': ('مشروع مقاولات', 'bi-building', 'contracting'),
    'contracting/receipt_form.html': ('إيصال مقاولات', 'bi-receipt', 'contracting'),
    'contracting/worker_form.html': ('عامل مقاولات', 'bi-person-hard-hat', 'contracting'),
    
    # crm
    'crm/activity_form.html': ('نشاط', 'bi-activity', 'crm'),
    'crm/appointment_form.html': ('موعد', 'bi-calendar-event', 'crm'),
    'crm/contact_person_form.html': ('جهة اتصال', 'bi-person-lines-fill', 'crm'),
    'crm/contract_form.html': ('عقد', 'bi-file-earmark-text', 'crm'),
    'crm/customer_form.html': ('عميل CRM', 'bi-person-circle', 'crm'),
    'crm/followup_form.html': ('متابعة', 'bi-arrow-repeat', 'crm'),
    'crm/opportunity_form.html': ('فرصة بيع', 'bi-graph-up', 'crm'),
    'crm/plan_form.html': ('خطة مبيعات', 'bi-clipboard-data', 'crm'),
    'crm/quotation_form.html': ('عرض سعر', 'bi-file-earmark-spreadsheet', 'crm'),
    'crm/task_form.html': ('مهمة', 'bi-check2-square', 'crm'),
    'crm/ticket_form.html': ('تذكرة دعم', 'bi-ticket', 'crm'),
    'crm/tickets/ticket_form.html': ('تذكرة دعم', 'bi-ticket', 'crm'),
}

def fix_template(file_path, title, icon, module):
    """إصلاح قالب واحد"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # إصلاح العنوان
        content = re.sub(
            r"{% block page_title %}{% trans 'نموذج جديد' %}{% endblock %}",
            f"{{% block page_title %}}{{% trans '{title}' %}}{{% endblock %}}",
            content
        )
        
        # إصلاح الأيقونة
        content = re.sub(
            r"{% block page_icon %}bi-file-earmark-text{% endblock %}",
            f"{{% block page_icon %}}{icon}{{% endblock %}}",
            content
        )
        
        # إصلاح الوحدة
        content = re.sub(
            r"{% block page_module %}default{% endblock %}",
            f"{{% block page_module %}}{module}{{% endblock %}}",
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"   خطأ: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 إصلاح عناوين صفحات النماذج")
    print("=" * 60)
    
    fixed = 0
    errors = 0
    
    for template_path, (title, icon, module) in TITLE_MAP.items():
        full_path = os.path.join(TEMPLATES_DIR, template_path)
        if os.path.exists(full_path):
            if fix_template(full_path, title, icon, module):
                print(f"✅ {template_path}: {title}")
                fixed += 1
            else:
                errors += 1
        else:
            print(f"⏭️  {template_path}: غير موجود")
    
    print("=" * 60)
    print(f"📊 تم إصلاح {fixed} ملف، {errors} خطأ")
    print("=" * 60)

if __name__ == '__main__':
    main()
