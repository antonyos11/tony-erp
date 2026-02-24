from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F, Max, Min
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from functools import wraps

from hr.models import (
    Employee, Department, JobPosition, AttendanceRecord, WorkSchedule,
    LeaveRequest, LeaveType, Payroll, PerformanceReview, TrainingProgram,
    TrainingEnrollment, JobVacancy, JobApplication, HRSettings,
    PerformanceTarget, TargetCategory, TargetProgress, TeamTarget,
    TeamTargetMembership, PerformanceMetric, EmployeeMetricValue,
    WeekendDay, PublicHoliday, EmployeeAbsence,
    AllowanceType, DeductionType, EmployeeAllowance, EmployeeDeduction, PayrollItem
)
from accounting.models import JournalEntry, JournalEntryItem
from hr.forms import (
    ComplaintForm, DisciplinaryActionForm, HSEIncidentForm,
    HSEInspectionForm, HSETrainingForm,
    LeaveRequestForm, PerformanceReviewQuickForm, TrainingProgramForm,
    JobVacancyForm, JobApplicationQuickForm, PerformanceTargetQuickForm,
    TeamTargetQuickForm, AttendanceRecordQuickForm
)

# مفردات المرتب والبطاقات المتقدمة

# === مفردات المرتب - البدلات والخصومات ===

@login_required
def payroll_items_dashboard(request):
    """لوحة تحكم مفردات المرتب - البدلات والخصومات"""
    from datetime import date
    
    context = {
        'allowance_types_count': AllowanceType.objects.filter(is_active=True).count(),
        'deduction_types_count': DeductionType.objects.filter(is_active=True).count(),
        'employee_allowances_count': EmployeeAllowance.objects.filter(is_active=True).count(),
        'employee_deductions_count': EmployeeDeduction.objects.filter(is_active=True).count(),
        'recent_allowance_types': AllowanceType.objects.filter(is_active=True).order_by('-created_at')[:5],
        'recent_deduction_types': DeductionType.objects.filter(is_active=True).order_by('-created_at')[:5],
        'total_allowances': EmployeeAllowance.objects.filter(is_active=True).aggregate(
            total=Sum('amount'))['total'] or 0,
        'total_deductions': EmployeeDeduction.objects.filter(is_active=True).aggregate(
            total=Sum('amount'))['total'] or 0,
    }
    return render(request, 'hr/payroll_items_dashboard.html', context)


@login_required
def allowance_type_list(request):
    """قائمة أنواع البدلات"""
    allowance_types = AllowanceType.objects.all().order_by('name')
    context = {'allowance_types': allowance_types}
    return render(request, 'hr/allowance_type_list.html', context)


@login_required
def allowance_type_create(request):
    """إنشاء نوع بدل جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        is_taxable = request.POST.get('is_taxable') == 'on'
        is_fixed = request.POST.get('is_fixed') == 'on'
        percentage = Decimal(request.POST.get('percentage', '0') or '0')
        default_amount = Decimal(request.POST.get('default_amount', '0') or '0')
        
        AllowanceType.objects.create(
            name=name,
            code=code,
            description=description,
            is_taxable=is_taxable,
            is_fixed=is_fixed,
            percentage=percentage,
            default_amount=default_amount
        )
        messages.success(request, 'تم إنشاء نوع البدل بنجاح')
        return redirect('hr:allowance_type_list')
    
    return render(request, 'hr/allowance_type_form.html', {'action': 'create'})


@login_required
def allowance_type_edit(request, pk):
    """تعديل نوع بدل"""
    allowance_type = get_object_or_404(AllowanceType, pk=pk)
    
    if request.method == 'POST':
        allowance_type.name = request.POST.get('name')
        allowance_type.code = request.POST.get('code')
        allowance_type.description = request.POST.get('description', '')
        allowance_type.is_taxable = request.POST.get('is_taxable') == 'on'
        allowance_type.is_fixed = request.POST.get('is_fixed') == 'on'
        allowance_type.percentage = Decimal(request.POST.get('percentage', '0') or '0')
        allowance_type.default_amount = Decimal(request.POST.get('default_amount', '0') or '0')
        allowance_type.is_active = request.POST.get('is_active') == 'on'
        allowance_type.save()
        
        messages.success(request, 'تم تحديث نوع البدل بنجاح')
        return redirect('hr:allowance_type_list')
    
    context = {'allowance_type': allowance_type, 'action': 'edit'}
    return render(request, 'hr/allowance_type_form.html', context)


@login_required
def allowance_type_delete(request, pk):
    """حذف نوع بدل"""
    allowance_type = get_object_or_404(AllowanceType, pk=pk)
    
    if request.method == 'POST':
        allowance_type.is_active = False
        allowance_type.save()
        messages.success(request, 'تم إلغاء تفعيل نوع البدل بنجاح')
    
    return redirect('hr:allowance_type_list')


@login_required
def deduction_type_list(request):
    """قائمة أنواع الخصومات"""
    deduction_types = DeductionType.objects.all().order_by('name')
    context = {'deduction_types': deduction_types}
    return render(request, 'hr/deduction_type_list.html', context)


@login_required
def deduction_type_create(request):
    """إنشاء نوع خصم جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        calculation_type = request.POST.get('calculation_type', 'fixed')
        percentage = Decimal(request.POST.get('percentage', '0') or '0')
        default_amount = Decimal(request.POST.get('default_amount', '0') or '0')
        is_mandatory = request.POST.get('is_mandatory') == 'on'
        
        DeductionType.objects.create(
            name=name,
            code=code,
            description=description,
            calculation_type=calculation_type,
            percentage=percentage,
            default_amount=default_amount,
            is_mandatory=is_mandatory
        )
        messages.success(request, 'تم إنشاء نوع الخصم بنجاح')
        return redirect('hr:deduction_type_list')
    
    context = {'action': 'create', 'calculation_choices': DeductionType.CALCULATION_CHOICES}
    return render(request, 'hr/deduction_type_form.html', context)


@login_required
def deduction_type_edit(request, pk):
    """تعديل نوع خصم"""
    deduction_type = get_object_or_404(DeductionType, pk=pk)
    
    if request.method == 'POST':
        deduction_type.name = request.POST.get('name')
        deduction_type.code = request.POST.get('code')
        deduction_type.description = request.POST.get('description', '')
        deduction_type.calculation_type = request.POST.get('calculation_type', 'fixed')
        deduction_type.percentage = Decimal(request.POST.get('percentage', '0') or '0')
        deduction_type.default_amount = Decimal(request.POST.get('default_amount', '0') or '0')
        deduction_type.is_mandatory = request.POST.get('is_mandatory') == 'on'
        deduction_type.is_active = request.POST.get('is_active') == 'on'
        deduction_type.save()
        
        messages.success(request, 'تم تحديث نوع الخصم بنجاح')
        return redirect('hr:deduction_type_list')
    
    context = {
        'deduction_type': deduction_type, 
        'action': 'edit',
        'calculation_choices': DeductionType.CALCULATION_CHOICES
    }
    return render(request, 'hr/deduction_type_form.html', context)


@login_required
def deduction_type_delete(request, pk):
    """حذف نوع خصم"""
    deduction_type = get_object_or_404(DeductionType, pk=pk)
    
    if request.method == 'POST':
        deduction_type.is_active = False
        deduction_type.save()
        messages.success(request, 'تم إلغاء تفعيل نوع الخصم بنجاح')
    
    return redirect('hr:deduction_type_list')


@login_required
def employee_allowance_list(request):
    """قائمة بدلات الموظفين"""
    employee_allowances = EmployeeAllowance.objects.select_related(
        'employee', 'allowance_type'
    ).filter(is_active=True).order_by('-start_date')
    
    # فلترة
    employee_id = request.GET.get('employee')
    allowance_type_id = request.GET.get('allowance_type')
    
    if employee_id:
        employee_allowances = employee_allowances.filter(employee_id=employee_id)
    if allowance_type_id:
        employee_allowances = employee_allowances.filter(allowance_type_id=allowance_type_id)
    
    context = {
        'employee_allowances': employee_allowances,
        'employees': Employee.objects.filter(status='active'),
        'allowance_types': AllowanceType.objects.filter(is_active=True),
    }
    return render(request, 'hr/employee_allowance_list.html', context)


@login_required
def employee_allowance_create(request):
    """إضافة بدل لموظف"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        allowance_type_id = request.POST.get('allowance_type')
        amount = Decimal(request.POST.get('amount', '0') or '0')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        notes = request.POST.get('notes', '')
        
        EmployeeAllowance.objects.create(
            employee_id=employee_id,
            allowance_type_id=allowance_type_id,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            notes=notes
        )
        messages.success(request, 'تم إضافة البدل للموظف بنجاح')
        return redirect('hr:employee_allowance_list')
    
    context = {
        'employees': Employee.objects.filter(status='active'),
        'allowance_types': AllowanceType.objects.filter(is_active=True),
    }
    return render(request, 'hr/employee_allowance_form.html', context)


@login_required
def employee_deduction_list(request):
    """قائمة خصومات الموظفين"""
    employee_deductions = EmployeeDeduction.objects.select_related(
        'employee', 'deduction_type'
    ).filter(is_active=True).order_by('-start_date')
    
    # فلترة
    employee_id = request.GET.get('employee')
    deduction_type_id = request.GET.get('deduction_type')
    
    if employee_id:
        employee_deductions = employee_deductions.filter(employee_id=employee_id)
    if deduction_type_id:
        employee_deductions = employee_deductions.filter(deduction_type_id=deduction_type_id)
    
    context = {
        'employee_deductions': employee_deductions,
        'employees': Employee.objects.filter(status='active'),
        'deduction_types': DeductionType.objects.filter(is_active=True),
    }
    return render(request, 'hr/employee_deduction_list.html', context)


@login_required
def employee_deduction_create(request):
    """إضافة خصم لموظف"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        deduction_type_id = request.POST.get('deduction_type')
        amount = Decimal(request.POST.get('amount', '0') or '0')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        notes = request.POST.get('notes', '')
        
        EmployeeDeduction.objects.create(
            employee_id=employee_id,
            deduction_type_id=deduction_type_id,
            amount=amount,
            start_date=start_date,
            end_date=end_date,
            notes=notes
        )
        messages.success(request, 'تم إضافة الخصم للموظف بنجاح')
        return redirect('hr:employee_deduction_list')
    
    context = {
        'employees': Employee.objects.filter(status='active'),
        'deduction_types': DeductionType.objects.filter(is_active=True),
    }
    return render(request, 'hr/employee_deduction_form.html', context)


@login_required
def id_card_preview(request, card_id):
    """معاينة بطاقة هوية موظف"""
    from hr.models import EmployeeIDCard
    from datetime import date
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    employee = card.employee
    
    # التحقق من صلاحية البطاقة
    is_valid = card.status == 'active' and card.expiry_date >= date.today()
    
    context = {
        'card': card,
        'employee': employee,
        'is_valid': is_valid,
    }
    return render(request, 'hr/id_card_preview.html', context)


# =============================
# Views إضافية لبطاقات الهوية
# =============================

@login_required
@permission_required('hr.change_employee', raise_exception=True)
@login_required
def id_card_lost_replacement(request, card_id):
    """إيقاف بطاقة مفقودة وإنشاء بطاقة جديدة مع إعادة تعيين كلمة المرور"""
    from hr.models import EmployeeIDCard
    from hr.hr_utils import create_employee_id_card
    import secrets
    import string
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    employee = card.employee
    
    if request.method == 'POST':
        # إلغاء البطاقة القديمة
        card.status = 'revoked'
        card.notes = (card.notes or '') + f'\n[{date.today()}] تم إيقاف البطاقة بسبب الفقدان'
        card.save()
        
        # إنشاء كلمة مرور مؤقتة
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # تحديث كلمة مرور المستخدم إن وجد
        if employee.user:
            employee.user.set_password(temp_password)
            employee.user.save()
        
        # إنشاء بطاقة جديدة
        try:
            new_card = create_employee_id_card(employee, expiry_months=12)
            
            # تحضير بيانات الدخول للعرض
            context = {
                'employee': employee,
                'old_card': card,
                'new_card': new_card,
                'username': employee.user.username if employee.user else None,
                'temp_password': temp_password if employee.user else None,
                'success': True,
            }
            return render(request, 'hr/id_card_replacement_success.html', context)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء البطاقة الجديدة: {str(e)}')
            return redirect('hr:employee_id_cards_list')
    
    context = {
        'card': card,
        'employee': employee,
    }
    return render(request, 'hr/id_card_lost_confirm.html', context)


@login_required
def id_card_deactivate(request, card_id):
    """إلغاء تفعيل بطاقة هوية موظف"""
    from hr.models import EmployeeIDCard
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    
    if request.method == 'POST':
        card.status = 'inactive'
        card.save()
        messages.success(request, f'تم إلغاء تفعيل بطاقة الموظف {card.employee.get_full_name()}')
        return redirect('hr:employee_id_cards_list')
    
    context = {
        'card': card,
        'employee': card.employee,
    }
    return render(request, 'hr/id_card_deactivate_confirm.html', context)


@login_required
def id_card_print_pdf(request, card_id):
    """طباعة بطاقة الهوية كملف PDF"""
    from hr.models import EmployeeIDCard
    from django.template.loader import get_template
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    employee = card.employee
    
    # إعداد السياق
    context = {
        'card': card,
        'employee': employee,
        'company_name': 'شركة الشامل',  # يمكن استبداله بإعدادات الشركة
    }
    
    # محاولة استخدام WeasyPrint أو xhtml2pdf إن وجد
    try:
        from weasyprint import HTML
        template = get_template('hr/id_card_pdf.html')
        html_string = template.render(context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="id_card_{employee.employee_number}.pdf"'
        return response
    except ImportError:
        pass
    
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        
        template = get_template('hr/id_card_pdf.html')
        html_string = template.render(context)
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="id_card_{employee.employee_number}.pdf"'
            return response
    except ImportError:
        pass
    
    # إذا لم تتوفر مكتبات PDF، نعرض صفحة للطباعة
    messages.info(request, 'استخدم Ctrl+P لطباعة البطاقة')
    return render(request, 'hr/id_card_print.html', context)


# =============================================
# نظام بطاقات التعريف المتقدم
# =============================================

@login_required
def id_card_select_employee(request):
    """صفحة اختيار الموظف لإصدار بطاقة"""
    from hr.models import Employee, EmployeeIDCard
    from django.db.models import Exists, OuterRef

    # جلب الموظفين مع معلومة هل لديهم بطاقة نشطة
    employees = Employee.objects.select_related('department', 'position').filter(
        status='active'
    ).order_by('arabic_name', 'first_name')

    # إضافة حقل has_active_card لكل موظف
    for emp in employees:
        emp.has_active_card = EmployeeIDCard.objects.filter(
            employee=emp,
            status='active'
        ).exists()

    departments = Department.objects.filter(is_active=True)

    context = {
        'employees': employees,
        'departments': departments,
    }
    return render(request, 'hr/id_card_select_employee.html', context)


@login_required
def id_card_create_single(request, employee_id=None):
    """إنشاء بطاقة هوية جديدة لموظف واحد (يدعم التوجيه بدون تمرير employee_id)."""
    from hr.models import Employee, EmployeeIDCard, IDCardTemplate
    from .services.advanced_id_card_service import create_employee_id_card_advanced

    # اسمح بتمرير المعرّف عبر مسار أو querystring أو form لتجنب الأخطاء الحالية
    employee_id = employee_id or request.GET.get('employee_id') or request.POST.get('employee_id')
    if not employee_id:
        messages.info(request, 'اختر الموظف الذي تريد إصدار بطاقة له أولاً')
        return redirect('hr:id_card_select_employee')

    employee = get_object_or_404(Employee, id=employee_id)
    templates = IDCardTemplate.objects.filter(is_active=True)
    
    if request.method == 'POST':
        template_id = request.POST.get('template')
        expiry_months = int(request.POST.get('expiry_months', 12))

        template = None
        if template_id:
            template = IDCardTemplate.objects.filter(id=template_id).first()

        try:
            card = create_employee_id_card_advanced(employee, template, expiry_months)
            messages.success(request, f'✅ تم إنشاء بطاقة جديدة للموظف {employee.arabic_name or employee.get_full_name()} بنجاح!')
            return redirect('hr:id_card_preview', card_id=card.id)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating ID card: {error_details}")
            messages.error(request, f'❌ حدث خطأ أثناء إنشاء البطاقة: {str(e)}')
    
    context = {
        'employee': employee,
        'templates': templates,
    }
    return render(request, 'hr/id_card_create.html', context)


@login_required
def id_card_bulk_create(request):
    """إنشاء بطاقات هوية لمجموعة موظفين"""
    from hr.models import EmployeeIDCard, IDCardTemplate, IDCardBatchPrint
    from .services.advanced_id_card_service import create_employee_id_card_advanced
    import uuid
    
    templates = IDCardTemplate.objects.filter(is_active=True)
    departments = Department.objects.filter(is_active=True)
    
    if request.method == 'POST':
        employee_ids = request.POST.getlist('employees')
        template_id = request.POST.get('template')
        expiry_months = int(request.POST.get('expiry_months', 12))
        
        template = None
        if template_id:
            template = IDCardTemplate.objects.filter(id=template_id).first()
        
        created_cards = []
        errors = []
        
        for emp_id in employee_ids:
            try:
                employee = Employee.objects.get(id=emp_id)
                card = create_employee_id_card_advanced(employee, template, expiry_months)
                created_cards.append(card)
            except Employee.DoesNotExist:
                errors.append(f'الموظف #{emp_id} غير موجود')
            except Exception as e:
                errors.append(f'خطأ في الموظف #{emp_id}: {str(e)}')
        
        if created_cards:
            # إنشاء سجل الدفعة
            batch = IDCardBatchPrint.objects.create(
                batch_number=f'BATCH-{uuid.uuid4().hex[:8].upper()}',
                template=template,
                total_cards=len(created_cards),
                status='completed',
                created_by=request.user
            )
            batch.cards.set(created_cards)
            
            messages.success(request, f'تم إنشاء {len(created_cards)} بطاقة بنجاح')
            return redirect('hr:id_card_batch_preview', batch_id=batch.id)
        
        if errors:
            for error in errors[:5]:
                messages.error(request, error)
    
    employees = Employee.objects.filter(status='active').select_related('department', 'position')
    
    context = {
        'employees': employees,
        'templates': templates,
        'departments': departments,
    }
    return render(request, 'hr/id_card_bulk_create.html', context)


@login_required
def id_card_batch_preview(request, batch_id):
    """معاينة دفعة بطاقات"""
    from hr.models import IDCardBatchPrint
    
    batch = get_object_or_404(IDCardBatchPrint, id=batch_id)
    cards = batch.cards.select_related('employee__department', 'employee__position').all()
    
    context = {
        'batch': batch,
        'cards': cards,
    }
    return render(request, 'hr/id_card_batch_preview.html', context)


@login_required
def id_card_batch_print_pdf(request, batch_id):
    """طباعة دفعة بطاقات كـ PDF"""
    from hr.models import IDCardBatchPrint
    from .services.advanced_id_card_service import AdvancedIDCardService
    from io import BytesIO
    
    batch = get_object_or_404(IDCardBatchPrint, id=batch_id)
    cards = batch.cards.select_related('employee__department', 'employee__position').all()
    
    service = AdvancedIDCardService(batch.template)
    
    # تجهيز قائمة البطاقات مع الموظفين
    cards_with_employees = [(card.employee, card) for card in cards]
    
    try:
        pdf_buffer = service.generate_batch_pdf(cards_with_employees)
        
        # تحديث سجل الدفعة
        batch.printed_cards = len(cards_with_employees)
        batch.status = 'completed'
        batch.save()
        
        # تحديث عداد الطباعة لكل بطاقة
        for card in cards:
            card.increment_print_count()
            if not card.printed_by:
                card.printed_by = request.user
                card.save()
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="batch_{batch.batch_number}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء إنشاء PDF: {str(e)}')
        return redirect('hr:id_card_batch_preview', batch_id=batch.id)


@login_required
def id_card_download_pdf(request, card_id):
    """تحميل بطاقة واحدة كـ PDF"""
    from hr.models import EmployeeIDCard
    from .services.advanced_id_card_service import AdvancedIDCardService
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    employee = card.employee
    
    # الحصول على القالب المستخدم (أو الافتراضي)
    from hr.models import IDCardTemplate
    template = IDCardTemplate.objects.filter(is_default=True, is_active=True).first()
    
    service = AdvancedIDCardService(template)
    
    try:
        pdf_buffer = service.generate_single_card_pdf(employee, card)
        
        # تحديث عداد الطباعة
        card.increment_print_count()
        if not card.printed_by:
            card.printed_by = request.user
            card.save()
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="id_card_{employee.employee_id}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء إنشاء PDF: {str(e)}')
        return redirect('hr:id_card_preview', card_id=card.id)


@login_required
def id_card_download_pvc(request, card_id):
    """تحميل بطاقة بحجم PVC للطباعة المباشرة"""
    from hr.models import EmployeeIDCard
    from .services.advanced_id_card_service import AdvancedIDCardService
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    employee = card.employee
    
    from hr.models import IDCardTemplate
    template = IDCardTemplate.objects.filter(is_default=True, is_active=True).first()
    
    service = AdvancedIDCardService(template)
    
    try:
        pdf_buffer = service.generate_pvc_card_pdf(employee, card)
        
        card.increment_print_count()
        if not card.printed_by:
            card.printed_by = request.user
            card.save()
        
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pvc_card_{employee.employee_id}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f'حدث خطأ: {str(e)}')
        return redirect('hr:id_card_preview', card_id=card.id)


@login_required
def id_card_template_list(request):
    """قائمة قوالب البطاقات"""
    from hr.models import IDCardTemplate
    
    templates = IDCardTemplate.objects.all().order_by('-is_default', '-created_at')
    
    context = {
        'templates': templates,
    }
    return render(request, 'hr/id_card_template_list.html', context)


@login_required
def id_card_template_create(request):
    """إنشاء قالب بطاقة جديد"""
    from hr.models import IDCardTemplate
    
    if request.method == 'POST':
        template = IDCardTemplate()
        template.name = request.POST.get('name', 'قالب جديد')
        template.description = request.POST.get('description', '')
        template.orientation = request.POST.get('orientation', 'horizontal')
        template.size = request.POST.get('size', 'pvc')
        template.primary_color = request.POST.get('primary_color', '#0f172a')
        template.secondary_color = request.POST.get('secondary_color', '#0ea5e9')
        template.text_color = request.POST.get('text_color', '#ffffff')
        template.background_color = request.POST.get('background_color', '#f8fafc')
        template.show_qr_code = request.POST.get('show_qr_code') == 'on'
        template.show_barcode = request.POST.get('show_barcode') == 'on'
        template.show_photo = request.POST.get('show_photo') == 'on'
        template.show_department = request.POST.get('show_department') == 'on'
        template.show_position = request.POST.get('show_position') == 'on'
        template.show_employee_id = request.POST.get('show_employee_id') == 'on'
        template.show_national_id = request.POST.get('show_national_id') == 'on'
        template.show_issue_date = request.POST.get('show_issue_date') == 'on'
        template.show_expiry_date = request.POST.get('show_expiry_date') == 'on'
        template.is_default = request.POST.get('is_default') == 'on'
        template.back_instructions = request.POST.get('back_instructions', '')
        template.created_by = request.user
        
        if 'company_logo' in request.FILES:
            template.company_logo = request.FILES['company_logo']
        
        if 'background_image' in request.FILES:
            template.background_image = request.FILES['background_image']
        
        template.save()
        messages.success(request, 'تم إنشاء القالب بنجاح')
        return redirect('hr:id_card_template_list')
    
    return render(request, 'hr/id_card_template_form.html', {'template': None})


@login_required
def id_card_template_edit(request, template_id):
    """تعديل قالب بطاقة"""
    from hr.models import IDCardTemplate
    
    template = get_object_or_404(IDCardTemplate, id=template_id)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.description = request.POST.get('description', '')
        template.orientation = request.POST.get('orientation', 'horizontal')
        template.size = request.POST.get('size', 'pvc')
        template.primary_color = request.POST.get('primary_color', '#0f172a')
        template.secondary_color = request.POST.get('secondary_color', '#0ea5e9')
        template.text_color = request.POST.get('text_color', '#ffffff')
        template.background_color = request.POST.get('background_color', '#f8fafc')
        template.show_qr_code = request.POST.get('show_qr_code') == 'on'
        template.show_barcode = request.POST.get('show_barcode') == 'on'
        template.show_photo = request.POST.get('show_photo') == 'on'
        template.show_department = request.POST.get('show_department') == 'on'
        template.show_position = request.POST.get('show_position') == 'on'
        template.show_employee_id = request.POST.get('show_employee_id') == 'on'
        template.show_national_id = request.POST.get('show_national_id') == 'on'
        template.show_issue_date = request.POST.get('show_issue_date') == 'on'
        template.show_expiry_date = request.POST.get('show_expiry_date') == 'on'
        template.is_default = request.POST.get('is_default') == 'on'
        template.back_instructions = request.POST.get('back_instructions', '')
        
        if 'company_logo' in request.FILES:
            template.company_logo = request.FILES['company_logo']
        
        if 'background_image' in request.FILES:
            template.background_image = request.FILES['background_image']
        
        template.save()
        messages.success(request, 'تم تحديث القالب بنجاح')
        return redirect('hr:id_card_template_list')
    
    return render(request, 'hr/id_card_template_form.html', {'template': template})


@login_required
def id_card_template_delete(request, template_id):
    """حذف قالب بطاقة"""
    from hr.models import IDCardTemplate
    
    template = get_object_or_404(IDCardTemplate, id=template_id)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'تم حذف القالب بنجاح')
        return redirect('hr:id_card_template_list')
    
    return render(request, 'hr/id_card_template_delete_confirm.html', {'template': template})


@login_required
def id_card_verify_qr(request):
    """التحقق من صحة بطاقة عبر QR Code"""
    from hr.models import EmployeeIDCard
    import json
    
    result = None
    
    if request.method == 'POST':
        qr_data = request.POST.get('qr_data', '')
        
        try:
            data = json.loads(qr_data)
            card_number = data.get('card_number')
            
            if card_number:
                card = EmployeeIDCard.objects.filter(card_number=card_number).first()
                
                if card:
                    card.increment_scan_count()
                    
                    result = {
                        'valid': card.is_valid(),
                        'card': card,
                        'employee': card.employee,
                        'status': card.status,
                        'expired': card.expiry_date < date.today() if card.status == 'active' else True,
                    }
                else:
                    result = {'valid': False, 'error': 'البطاقة غير موجودة في النظام'}
            else:
                result = {'valid': False, 'error': 'بيانات غير صالحة'}
        except json.JSONDecodeError:
            result = {'valid': False, 'error': 'تنسيق QR غير صحيح'}
    
    context = {'result': result}
    return render(request, 'hr/id_card_verify_qr.html', context)


@login_required
def id_card_history(request, card_id):
    """سجل تاريخ بطاقة معينة"""
    from hr.models import EmployeeIDCard
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    
    # جلب كل البطاقات السابقة لنفس الموظف
    all_cards = EmployeeIDCard.objects.filter(
        employee=card.employee
    ).order_by('-issue_date')
    
    context = {
        'card': card,
        'all_cards': all_cards,
        'employee': card.employee,
    }
    return render(request, 'hr/id_card_history.html', context)


@login_required
def id_card_batch_list(request):
    """قائمة دفعات الطباعة"""
    from hr.models import IDCardBatchPrint
    
    batches = IDCardBatchPrint.objects.select_related('template', 'created_by').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(batches, 20)
    page = request.GET.get('page')
    batches_page = paginator.get_page(page)
    
    context = {
        'batches': batches_page,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': batches_page,
    }
    return render(request, 'hr/id_card_batch_list.html', context)


@login_required
def id_card_reports(request):
    """تقارير البطاقات"""
    from hr.models import EmployeeIDCard, IDCardBatchPrint
    from django.db.models.functions import TruncMonth, TruncDate
    
    # إحصائيات عامة
    total_cards = EmployeeIDCard.objects.count()
    active_cards = EmployeeIDCard.objects.filter(status='active', expiry_date__gte=date.today()).count()
    expired_cards = EmployeeIDCard.objects.filter(
        Q(status='expired') | Q(expiry_date__lt=date.today())
    ).count()
    lost_cards = EmployeeIDCard.objects.filter(status='lost').count()
    
    # البطاقات المنتهية قريباً (خلال 30 يوم)
    expiring_soon = EmployeeIDCard.objects.filter(
        status='active',
        expiry_date__gte=date.today(),
        expiry_date__lte=date.today() + timedelta(days=30)
    ).count()
    
    # إحصائيات الطباعة الشهرية
    monthly_prints = EmployeeIDCard.objects.filter(
        printed_at__isnull=False
    ).annotate(
        month=TruncMonth('printed_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('-month')[:12]
    
    # آخر البطاقات المصدرة
    recent_cards = EmployeeIDCard.objects.select_related(
        'employee__department'
    ).order_by('-created_at')[:10]
    
    # البطاقات المنتهية قريباً
    expiring_cards = EmployeeIDCard.objects.filter(
        status='active',
        expiry_date__gte=date.today(),
        expiry_date__lte=date.today() + timedelta(days=30)
    ).select_related('employee')[:10]
    
    context = {
        'total_cards': total_cards,
        'active_cards': active_cards,
        'expired_cards': expired_cards,
        'lost_cards': lost_cards,
        'expiring_soon': expiring_soon,
        'monthly_prints': monthly_prints,
        'recent_cards': recent_cards,
        'expiring_cards': expiring_cards,
    }
    return render(request, 'hr/id_card_reports.html', context)


@login_required
@require_POST
def id_card_revoke(request, card_id):
    """إلغاء بطاقة تعريف"""
    from hr.models import EmployeeIDCard
    
    card = get_object_or_404(EmployeeIDCard, id=card_id)
    
    # التحقق من أن البطاقة فعالة
    if card.status != 'active':
        messages.warning(request, 'هذه البطاقة غير فعالة بالفعل')
        return redirect('hr:id_card_preview', card_id=card.id)
    
    # إلغاء البطاقة
    card.status = 'revoked'
    card.save(update_fields=['status'])
    
    messages.success(request, f'تم إلغاء البطاقة {card.card_number} بنجاح')
    return redirect('hr:id_card_preview', card_id=card.id)
