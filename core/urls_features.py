"""
URLs للميزات الجديدة
Enterprise Features URLs

مسارات للميزات التسعة الجديدة
"""

from django.urls import path
from core import views_features

app_name = 'features'

urlpatterns = [
    # Delivery Promise
    path('production/delivery-promise/', views_features.delivery_promise_view, name='delivery_promise'),
    path('production/delivery-promise/calculate/', views_features.calculate_delivery_promise, name='calculate_delivery_promise'),
    
    # Traceability
    path('quality-control/traceability/', views_features.traceability_view, name='traceability'),
    path('quality-control/traceability/journey/', views_features.trace_product_journey, name='trace_journey'),
    
    # Break-Even Analysis
    path('accounting/break-even/', views_features.breakeven_analysis_view, name='breakeven'),
    path('accounting/break-even/calculate/', views_features.calculate_breakeven, name='calculate_breakeven'),
    
    # Supplier Evaluation
    path('purchases/supplier-evaluation/', views_features.supplier_evaluation_view, name='supplier_evaluation'),
    path('purchases/supplier-evaluation/evaluate/', views_features.evaluate_supplier, name='evaluate_supplier'),
    
    # Executive Dashboard
    path('monitoring/executive-dashboard/', views_features.executive_dashboard_view, name='executive_dashboard'),
    
    # Loss Prevention
    path('smart-pricing/loss-prevention/', views_features.loss_prevention_view, name='loss_prevention'),
    path('smart-pricing/loss-prevention/validate/', views_features.validate_price, name='validate_price'),
    
    # Anomaly Detection
    path('monitoring/anomaly-detection/', views_features.anomaly_detection_view, name='anomaly_detection'),
    path('monitoring/anomaly-detection/run/', views_features.run_anomaly_detection, name='run_anomaly_detection'),
    path('monitoring/anomaly-detection/predict/', views_features.run_proactive_predictions, name='run_predictions'),
    
    # Mobile API
    path('api/mobile/', views_features.mobile_api_view, name='mobile_api'),
    
    # White Label
    path('white-label/', views_features.white_label_view, name='white_label'),
]
