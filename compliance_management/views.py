from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import ComplianceStandard, ComplianceChecklist, Audit, AuditFinding, ComplianceReport
from django.db.models import Count

@login_required
def dashboard(request):
    standards = ComplianceStandard.objects.filter(is_active=True)
    audits = Audit.objects.order_by('-scheduled_date')[:10]
    reports = ComplianceReport.objects.order_by('-report_period_end')[:5]
    findings = AuditFinding.objects.select_related('audit').order_by('-created_at')[:10]
    
    total_standards = standards.count()
    total_audits = Audit.objects.count()
    completed_audits = Audit.objects.filter(status='completed').count()
    total_findings = AuditFinding.objects.count()
    
    context = {
        'page_title': 'الامتثال والمراجعة',
        'standards': standards,
        'audits': audits,
        'reports': reports,
        'findings': findings,
        'total_standards': total_standards,
        'total_audits': total_audits,
        'completed_audits': completed_audits,
        'total_findings': total_findings,
    }
    return render(request, 'compliance_management/dashboard.html', context)

@login_required
def requirement_list(request):
    requirements = ComplianceStandard.objects.all().order_by('-created_at')
    paginator = Paginator(requirements, 20)
    page = request.GET.get('page')
    requirements = paginator.get_page(page)
    
    context = {
        'page_title': 'متطلبات الامتثال',
        'requirements': requirements,
    }
    return render(request, 'compliance_management/requirement_list.html', context)

@login_required
def requirement_create(request):
    if request.method == 'POST':
        try:
            req = ComplianceStandard.objects.create(
                name=request.POST.get('name'),
                code=request.POST.get('code', ''),
                description=request.POST.get('description', ''),
                category=request.POST.get('category', 'regulatory'),
                is_active=True,
            )
            messages.success(request, f'تم إنشاء المتطلب بنجاح!')
            return redirect('compliance_management:requirement_detail', pk=req.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة متطلب جديد',
    }
    return render(request, 'compliance_management/requirement_form.html', context)

@login_required
def requirement_detail(request, pk):
    requirement = get_object_or_404(ComplianceStandard, pk=pk)
    
    context = {
        'page_title': f'متطلب: {requirement.name}',
        'requirement': requirement,
    }
    return render(request, 'compliance_management/requirement_detail.html', context)

@login_required
def requirement_edit(request, pk):
    requirement = get_object_or_404(ComplianceStandard, pk=pk)
    
    if request.method == 'POST':
        requirement.name = request.POST.get('name', requirement.name)
        requirement.code = request.POST.get('code', requirement.code)
        requirement.description = request.POST.get('description', requirement.description)
        requirement.is_active = request.POST.get('is_active') == 'on'
        requirement.save()
        messages.success(request, 'تم تحديث المتطلب بنجاح!')
        return redirect('compliance_management:requirement_detail', pk=requirement.id)
    
    context = {
        'page_title': f'تعديل: {requirement.name}',
        'requirement': requirement,
    }
    return render(request, 'compliance_management/requirement_form.html', context)

@login_required
def requirement_delete(request, pk):
    requirement = get_object_or_404(ComplianceStandard, pk=pk)
    if request.method == 'POST':
        requirement.delete()
        messages.success(request, 'تم حذف المتطلب بنجاح!')
        return redirect('compliance_management:requirement_list')
    
    context = {
        'page_title': f'حذف: {requirement.name}',
        'requirement': requirement,
    }
    return render(request, 'compliance_management/requirement_confirm_delete.html', context)
