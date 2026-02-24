from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Competitor, CompetitorProduct, MarketTrend, CompetitiveAnalysis
from django.db.models import Count

@login_required
def dashboard(request):
    competitors = Competitor.objects.filter(is_active=True)
    products = CompetitorProduct.objects.select_related('competitor').order_by('-created_at')[:10]
    trends = MarketTrend.objects.order_by('-identified_date')[:5]
    analyses = CompetitiveAnalysis.objects.order_by('-analysis_date')[:5]
    
    total_competitors = competitors.count()
    total_products = CompetitorProduct.objects.count()
    total_trends = MarketTrend.objects.count()
    total_analyses = CompetitiveAnalysis.objects.count()
    
    context = {
        'page_title': 'الذكاء التنافسي',
        'competitors': competitors,
        'products': products,
        'trends': trends,
        'analyses': analyses,
        'total_competitors': total_competitors,
        'total_products': total_products,
        'total_trends': total_trends,
        'total_analyses': total_analyses,
    }
    return render(request, 'competitive_intelligence/dashboard.html', context)

@login_required
def competitor_list(request):
    competitors = Competitor.objects.all().order_by('name')
    paginator = Paginator(competitors, 20)
    page = request.GET.get('page')
    competitors = paginator.get_page(page)
    
    context = {
        'page_title': 'قائمة المنافسين',
        'competitors': competitors,
    }
    return render(request, 'competitive_intelligence/competitor_list.html', context)

@login_required
def competitor_create(request):
    if request.method == 'POST':
        try:
            competitor = Competitor.objects.create(
                name=request.POST.get('name'),
                website=request.POST.get('website', ''),
                description=request.POST.get('description', ''),
                industry=request.POST.get('industry', ''),
                threat_level=request.POST.get('threat_level', 'medium'),
                is_active=True,
            )
            messages.success(request, f'تم إضافة المنافس بنجاح!')
            return redirect('competitive_intelligence:competitor_detail', pk=competitor.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إضافة منافس جديد',
    }
    return render(request, 'competitive_intelligence/competitor_form.html', context)

@login_required
def competitor_detail(request, pk):
    competitor = get_object_or_404(Competitor, pk=pk)
    products = CompetitorProduct.objects.filter(competitor=competitor)
    analyses = CompetitiveAnalysis.objects.filter(competitor=competitor).order_by('-analysis_date')
    
    context = {
        'page_title': f'منافس: {competitor.name}',
        'competitor': competitor,
        'products': products,
        'analyses': analyses,
    }
    return render(request, 'competitive_intelligence/competitor_detail.html', context)

@login_required
def competitor_edit(request, pk):
    competitor = get_object_or_404(Competitor, pk=pk)
    
    if request.method == 'POST':
        competitor.name = request.POST.get('name', competitor.name)
        competitor.website = request.POST.get('website', competitor.website)
        competitor.description = request.POST.get('description', competitor.description)
        competitor.threat_level = request.POST.get('threat_level', competitor.threat_level)
        competitor.is_active = request.POST.get('is_active') == 'on'
        competitor.save()
        messages.success(request, 'تم تحديث المنافس بنجاح!')
        return redirect('competitive_intelligence:competitor_detail', pk=competitor.id)
    
    context = {
        'page_title': f'تعديل: {competitor.name}',
        'competitor': competitor,
    }
    return render(request, 'competitive_intelligence/competitor_form.html', context)

@login_required
def competitor_delete(request, pk):
    competitor = get_object_or_404(Competitor, pk=pk)
    if request.method == 'POST':
        competitor.delete()
        messages.success(request, 'تم حذف المنافس بنجاح!')
        return redirect('competitive_intelligence:competitor_list')
    
    context = {
        'page_title': f'حذف: {competitor.name}',
        'competitor': competitor,
    }
    return render(request, 'competitive_intelligence/competitor_confirm_delete.html', context)
