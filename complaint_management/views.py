from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Complaint, ImprovementInitiative
from django.db.models import Count

@login_required
def dashboard(request):
    complaints = Complaint.objects.select_related('customer').order_by('-received_at')[:10]
    initiatives = ImprovementInitiative.objects.order_by('-created_at')[:5]
    
    total_complaints = Complaint.objects.count()
    open_complaints = Complaint.objects.filter(status='open').count()
    resolved_complaints = Complaint.objects.filter(status='resolved').count()
    total_initiatives = ImprovementInitiative.objects.count()
    
    context = {
        'page_title': 'إدارة الشكاوى',
        'complaints': complaints,
        'initiatives': initiatives,
        'total_complaints': total_complaints,
        'open_complaints': open_complaints,
        'resolved_complaints': resolved_complaints,
        'total_initiatives': total_initiatives,
    }
    return render(request, 'complaint_management/dashboard.html', context)

@login_required
def complaint_list(request):
    complaints = Complaint.objects.all().order_by('-received_at')
    paginator = Paginator(complaints, 20)
    page = request.GET.get('page')
    complaints = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة الشكاوى',
        'complaints': complaints,
    }
    return render(request, 'complaint_management/complaint_list.html', context)

@login_required
def complaint_create(request):
    if request.method == 'POST':
        try:
            complaint = Complaint.objects.create(
                complaint_number=request.POST.get('complaint_number'),
                subject=request.POST.get('subject'),
                description=request.POST.get('description', ''),
                priority=request.POST.get('priority', 'medium'),
                category=request.POST.get('category', 'service'),
                status='open',
                created_by=request.user,
            )
            messages.success(request, f'تم إنشاء الشكوى بنجاح!')
            return redirect('complaint_management:complaint_detail', pk=complaint.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'تسجيل شكوى جديدة',
    }
    return render(request, 'complaint_management/complaint_form.html', context)

@login_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    
    context = {
        'page_title': f'شكوى: {complaint.complaint_number}',
        'complaint': complaint,
    }
    return render(request, 'complaint_management/complaint_detail.html', context)

@login_required
def complaint_edit(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        complaint.subject = request.POST.get('subject', complaint.subject)
        complaint.description = request.POST.get('description', complaint.description)
        complaint.priority = request.POST.get('priority', complaint.priority)
        complaint.status = request.POST.get('status', complaint.status)
        complaint.save()
        messages.success(request, 'تم تحديث الشكوى بنجاح!')
        return redirect('complaint_management:complaint_detail', pk=complaint.id)
    
    context = {
        'page_title': f'تعديل: {complaint.complaint_number}',
        'complaint': complaint,
    }
    return render(request, 'complaint_management/complaint_form.html', context)

@login_required
def complaint_delete(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    if request.method == 'POST':
        complaint.delete()
        messages.success(request, 'تم حذف الشكوى بنجاح!')
        return redirect('complaint_management:complaint_list')
    
    context = {
        'page_title': f'حذف: {complaint.complaint_number}',
        'complaint': complaint,
    }
    return render(request, 'complaint_management/complaint_confirm_delete.html', context)
