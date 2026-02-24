from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Tender, Bid, TenderEvaluation
from django.db.models import Count, Sum

@login_required
def dashboard(request):
    tenders = Tender.objects.all().order_by('-created_at')[:10]
    total_tenders = Tender.objects.count()
    active_tenders = Tender.objects.filter(status='open').count()
    pending_tenders = Tender.objects.filter(status='published').count()
    total_bids = Bid.objects.count()
    
    context = {
        'page_title': 'المناقصات والعطاءات',
        'tenders': tenders,
        'total_tenders': total_tenders,
        'active_tenders': active_tenders,
        'pending_tenders': pending_tenders,
        'total_bids': total_bids,
    }
    return render(request, 'tender_bidding/dashboard.html', context)

@login_required
def tender_list(request):
    """قائمة جميع المناقصات"""
    tenders = Tender.objects.all().order_by('-created_at')
    paginator = Paginator(tenders, 20)
    page = request.GET.get('page')
    tenders = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة المناقصات',
        'tenders': tenders,
    }
    return render(request, 'tender_bidding/tender_list.html', context)

@login_required
def tender_create(request):
    """إنشاء مناقصة جديدة"""
    if request.method == 'POST':
        try:
            tender = Tender.objects.create(
                reference_number=request.POST.get('reference_number'),
                title=request.POST.get('title'),
                description=request.POST.get('description', ''),
                direction=request.POST.get('direction', 'outgoing'),
                tender_type=request.POST.get('tender_type', 'open'),
                status='draft',
                issuing_organization=request.POST.get('issuing_organization', ''),
                submission_deadline=request.POST.get('submission_deadline'),
                estimated_value=request.POST.get('estimated_value', 0),
            )
            messages.success(request, f'تم إنشاء المناقصة "{tender.title}" بنجاح!')
            return redirect('tender_bidding:tender_detail', pk=tender.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة مناقصة جديدة',
        'tender_types': Tender.TENDER_TYPES,
        'direction_choices': Tender.DIRECTION_CHOICES,
        'status_choices': Tender.STATUS_CHOICES,
    }
    return render(request, 'tender_bidding/tender_form.html', context)

@login_required
def tender_detail(request, pk):
    """عرض تفاصيل المناقصة"""
    tender = get_object_or_404(Tender, pk=pk)
    bids = Bid.objects.filter(tender=tender).order_by('-submitted_at')
    
    context = {
        'page_title': f'مناقصة: {tender.title}',
        'tender': tender,
        'bids': bids,
    }
    return render(request, 'tender_bidding/tender_detail.html', context)

@login_required
def tender_edit(request, pk):
    """تعديل المناقصة"""
    tender = get_object_or_404(Tender, pk=pk)
    
    if request.method == 'POST':
        tender.reference_number = request.POST.get('reference_number', tender.reference_number)
        tender.title = request.POST.get('title', tender.title)
        tender.description = request.POST.get('description', tender.description)
        tender.direction = request.POST.get('direction', tender.direction)
        tender.tender_type = request.POST.get('tender_type', tender.tender_type)
        tender.status = request.POST.get('status', tender.status)
        tender.issuing_organization = request.POST.get('issuing_organization', tender.issuing_organization)
        tender.estimated_value = request.POST.get('estimated_value', tender.estimated_value)
        tender.save()
        messages.success(request, 'تم تحديث المناقصة بنجاح!')
        return redirect('tender_bidding:tender_detail', pk=tender.id)
    
    context = {
        'page_title': f'تعديل: {tender.title}',
        'tender': tender,
        'tender_types': Tender.TENDER_TYPES,
        'direction_choices': Tender.DIRECTION_CHOICES,
        'status_choices': Tender.STATUS_CHOICES,
    }
    return render(request, 'tender_bidding/tender_form.html', context)

@login_required
def tender_delete(request, pk):
    """حذف المناقصة"""
    tender = get_object_or_404(Tender, pk=pk)
    if request.method == 'POST':
        tender.delete()
        messages.success(request, 'تم حذف المناقصة بنجاح!')
        return redirect('tender_bidding:tender_list')
    
    context = {
        'page_title': f'حذف: {tender.title}',
        'tender': tender,
    }
    return render(request, 'tender_bidding/tender_confirm_delete.html', context)

@login_required
def bid_list(request):
    """قائمة العطاءات"""
    bids = Bid.objects.select_related('tender').order_by('-submitted_at')
    paginator = Paginator(bids, 20)
    page = request.GET.get('page')
    bids = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة العطاءات',
        'bids': bids,
    }
    return render(request, 'tender_bidding/bid_list.html', context)

@login_required
def bid_create(request):
    """إنشاء عطاء جديد"""
    tenders = Tender.objects.filter(status='open')
    
    if request.method == 'POST':
        tender = get_object_or_404(Tender, pk=request.POST.get('tender_id'))
        bid = Bid.objects.create(
            tender=tender,
            bid_number=request.POST.get('bid_number'),
            bidder_name=request.POST.get('bidder_name'),
            bid_amount=request.POST.get('bid_amount', 0),
            notes=request.POST.get('notes', ''),
            status='submitted',
        )
        messages.success(request, f'تم تقديم العطاء بنجاح!')
        return redirect('tender_bidding:bid_detail', pk=bid.id)
    
    context = {
        'page_title': 'تقديم عطاء جديد',
        'tenders': tenders,
    }
    return render(request, 'tender_bidding/bid_form.html', context)

@login_required
def bid_detail(request, pk):
    """عرض تفاصيل العطاء"""
    bid = get_object_or_404(Bid, pk=pk)
    
    context = {
        'page_title': f'عطاء: {bid.bid_number}',
        'bid': bid,
    }
    return render(request, 'tender_bidding/bid_detail.html', context)
