from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Campaign, CustomerSegment

@login_required
def dashboard(request):
    campaigns = Campaign.objects.all().order_by('-created_at')[:10]
    total_campaigns = Campaign.objects.count()
    active_campaigns = Campaign.objects.filter(status='active').count()
    
    context = {
        'campaigns': campaigns,
        'page_title': 'الحملات التسويقية',
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
    }
    return render(request, 'marketing_campaigns/dashboard.html', context)

@login_required
def campaign_list(request):
    campaigns = Campaign.objects.all().order_by('-created_at')
    paginator = Paginator(campaigns, 20)
    page = request.GET.get('page')
    campaigns = paginator.get_page(page)
    
    context = {
        'campaigns': campaigns,
        'page_title': 'قائمة الحملات',
    }
    return render(request, 'marketing_campaigns/campaign_list.html', context)

@login_required
def campaign_create(request):
    if request.method == 'POST':
        try:
            campaign = Campaign.objects.create(
                name=request.POST.get('name'),
                campaign_type=request.POST.get('campaign_type', 'awareness'),
                status='draft',
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date') or None,
                budget=request.POST.get('budget', 0),
                description=request.POST.get('description', ''),
                created_by=request.user,
            )
            messages.success(request, f'تم إنشاء الحملة "{campaign.name}" بنجاح!')
            return redirect('marketing_campaigns:campaign_detail', pk=campaign.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة حملة جديدة',
        'campaign_types': Campaign.CAMPAIGN_TYPES,
        'status_choices': Campaign.STATUS_CHOICES,
    }
    return render(request, 'marketing_campaigns/campaign_form.html', context)

@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    context = {
        'page_title': f'حملة: {campaign.name}',
        'campaign': campaign,
    }
    return render(request, 'marketing_campaigns/campaign_detail.html', context)

@login_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if request.method == 'POST':
        campaign.name = request.POST.get('name', campaign.name)
        campaign.campaign_type = request.POST.get('campaign_type', campaign.campaign_type)
        campaign.status = request.POST.get('status', campaign.status)
        campaign.description = request.POST.get('description', campaign.description)
        campaign.budget = request.POST.get('budget', campaign.budget)
        campaign.save()
        messages.success(request, 'تم تحديث الحملة بنجاح!')
        return redirect('marketing_campaigns:campaign_detail', pk=campaign.id)
    
    context = {
        'page_title': f'تعديل: {campaign.name}',
        'campaign': campaign,
        'campaign_types': Campaign.CAMPAIGN_TYPES,
        'status_choices': Campaign.STATUS_CHOICES,
    }
    return render(request, 'marketing_campaigns/campaign_form.html', context)

@login_required
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'تم حذف الحملة بنجاح!')
        return redirect('marketing_campaigns:campaign_list')
    
    context = {
        'page_title': f'حذف: {campaign.name}',
        'campaign': campaign,
    }
    return render(request, 'marketing_campaigns/campaign_confirm_delete.html', context)
