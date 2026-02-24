from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import CustomerProfitabilityAnalysis, CustomerValueScore
from django.db.models import Avg, Sum

@login_required
def dashboard(request):
    analyses = CustomerProfitabilityAnalysis.objects.select_related('customer').order_by('-analysis_period_end')[:10]
    scores = CustomerValueScore.objects.select_related('customer').order_by('-total_score')[:10]
    
    total_analyses = CustomerProfitabilityAnalysis.objects.count()
    avg_clv = CustomerProfitabilityAnalysis.objects.aggregate(avg=Avg('customer_lifetime_value'))['avg'] or 0
    total_revenue = CustomerProfitabilityAnalysis.objects.aggregate(total=Sum('total_revenue'))['total'] or 0
    
    context = {
        'page_title': 'ربحية العملاء',
        'analyses': analyses,
        'scores': scores,
        'total_analyses': total_analyses,
        'avg_clv': avg_clv,
        'total_revenue': total_revenue,
    }
    return render(request, 'customer_profitability/dashboard.html', context)

@login_required
def analysis_list(request):
    analyses = CustomerProfitabilityAnalysis.objects.all().order_by('-analysis_period_end')
    paginator = Paginator(analyses, 20)
    page = request.GET.get('page')
    analyses = paginator.get_page(page)
    
    context = {
        'page_title': 'تحليلات ربحية العملاء',
        'analyses': analyses,
    }
    return render(request, 'customer_profitability/analysis_list.html', context)

@login_required
def analysis_create(request):
    if request.method == 'POST':
        try:
            analysis = CustomerProfitabilityAnalysis.objects.create(
                analysis_date=request.POST.get('analysis_date'),
                total_revenue=request.POST.get('total_revenue', 0),
                total_costs=request.POST.get('total_costs', 0),
                lifetime_value=request.POST.get('lifetime_value', 0),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f'تم إنشاء التحليل بنجاح!')
            return redirect('customer_profitability:analysis_detail', pk=analysis.id)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'page_title': 'إنشاء تحليل جديد',
    }
    return render(request, 'customer_profitability/analysis_form.html', context)

@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(CustomerProfitabilityAnalysis, pk=pk)
    
    context = {
        'page_title': f'تحليل ربحية',
        'analysis': analysis,
    }
    return render(request, 'customer_profitability/analysis_detail.html', context)

@login_required
def analysis_delete(request, pk):
    analysis = get_object_or_404(CustomerProfitabilityAnalysis, pk=pk)
    if request.method == 'POST':
        analysis.delete()
        messages.success(request, 'تم حذف التحليل بنجاح!')
        return redirect('customer_profitability:analysis_list')
    
    context = {
        'page_title': 'حذف التحليل',
        'analysis': analysis,
    }
    return render(request, 'customer_profitability/analysis_confirm_delete.html', context)
