"""
Views لتحليلات الذكاء الاصطناعي
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from .models import PredictionModel, Prediction, AIInsight, DataAnalysis
from .services import SalesForecastService, CustomerChurnService, InventoryOptimizationService, InsightGenerator


@login_required
def dashboard(request):
    """لوحة تحليلات AI"""
    insights = AIInsight.objects.filter(is_read=False)[:10]
    recent_predictions = Prediction.objects.order_by('-created_at')[:5]
    models = PredictionModel.objects.filter(is_active=True)
    
    # Calculate real prediction accuracy
    from django.db.models import Avg
    prediction_accuracy = 0
    try:
        avg_acc = Prediction.objects.filter(accuracy__isnull=False).aggregate(avg=Avg('accuracy'))
        if avg_acc['avg']:
            prediction_accuracy = round(avg_acc['avg'], 1)
    except Exception:
        prediction_accuracy = 0
    
    return render(request, 'ai_analytics/dashboard.html', {
        'insights': insights,
        'recent_predictions': recent_predictions,
        'models': models,
        'prediction_accuracy': prediction_accuracy,
    })


@login_required
def sales_forecast(request):
    """توقع المبيعات"""
    days = int(request.GET.get('days', 30))
    
    service = SalesForecastService(days_ahead=days)
    forecast = service.predict()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(forecast)
    
    return render(request, 'ai_analytics/sales_forecast.html', {
        'forecast': forecast,
        'days': days,
    })


@login_required
def churn_prediction(request):
    """توقع فقدان العملاء"""
    service = CustomerChurnService()
    results = service.predict_churn()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'results': results})
    
    return render(request, 'ai_analytics/churn_prediction.html', {
        'results': results,
    })


@login_required
def inventory_analysis(request):
    """تحليل المخزون"""
    service = InventoryOptimizationService()
    analysis = service.analyze()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(analysis)
    
    return render(request, 'ai_analytics/inventory_analysis.html', {
        'analysis': analysis,
    })


@login_required
def insights_list(request):
    """قائمة الرؤى"""
    insights = AIInsight.objects.all()
    
    insight_type = request.GET.get('type')
    if insight_type:
        insights = insights.filter(insight_type=insight_type)
    
    priority = request.GET.get('priority')
    if priority:
        insights = insights.filter(priority=priority)
    
    return render(request, 'ai_analytics/insights.html', {
        'insights': insights,
    })


@login_required
@require_http_methods(['POST'])
def generate_insights(request):
    """توليد رؤى جديدة"""
    generator = InsightGenerator()
    insights = generator.generate_insights()
    
    return JsonResponse({
        'success': True,
        'count': len(insights)
    })


@login_required
@require_http_methods(['POST'])
def mark_insight_read(request, insight_id):
    """تحديد الرؤية كمقروءة"""
    insight = get_object_or_404(AIInsight, id=insight_id)
    insight.is_read = True
    insight.save()
    
    return JsonResponse({'success': True})


@login_required
def ask_ai(request):
    """سؤال AI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            
            # هنا يمكن استخدام OpenAI أو Anthropic
            # للحصول على إجابة ذكية
            
            response = analyze_question(question)
            
            return JsonResponse({
                'success': True,
                'response': response
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'ai_analytics/ask_ai.html')


def analyze_question(question):
    """تحليل السؤال وإرجاع إجابة"""
    # تحليل بسيط - يمكن استبداله بـ AI API
    
    question_lower = question.lower()
    
    if 'مبيعات' in question_lower or 'sales' in question_lower:
        service = SalesForecastService(days_ahead=7)
        forecast = service.predict()
        return f"توقع المبيعات للأسبوع القادم: متوسط يومي {forecast.get('avg_daily', 0):,.2f}"
    
    if 'عملاء' in question_lower or 'customers' in question_lower:
        service = CustomerChurnService()
        results = service.predict_churn()
        high_risk = len([r for r in results if isinstance(r, dict) and r.get('risk_level') == 'high'])
        return f"عدد العملاء معرضين للفقدان: {high_risk}"
    
    if 'مخزون' in question_lower or 'inventory' in question_lower:
        service = InventoryOptimizationService()
        analysis = service.analyze()
        return f"منتجات تحتاج إعادة طلب: {analysis.get('needs_reorder', 0)}"
    
    return "عذراً، لم أفهم السؤال. يمكنك سؤالي عن المبيعات، العملاء، أو المخزون."
