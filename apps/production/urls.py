"""
URLs تطبيق الإنتاج — RITA ERP
"""
from django.urls import path
from apps.production import views

app_name = 'production'

urlpatterns = [
    path('orders/', views.ProductionOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.ProductionOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.ProductionOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/confirm/', views.ConfirmOrderView.as_view(), name='order_confirm'),
    path('orders/<int:pk>/start/', views.StartProductionView.as_view(), name='order_start'),
    path('orders/<int:pk>/complete/', views.CompleteProductionView.as_view(), name='order_complete'),
    path('orders/<int:pk>/cancel/', views.CancelOrderView.as_view(), name='order_cancel'),
    path('orders/<int:pk>/labor/', views.AddLaborCostView.as_view(), name='add_labor'),
    path('orders/<int:pk>/overhead/', views.AddOverheadCostView.as_view(), name='add_overhead'),
    path('stages/<int:pk>/complete/', views.CompleteStageView.as_view(), name='stage_complete'),
    path('reports/cost/', views.ProductionCostReportView.as_view(), name='cost_report'),
    # AJAX
    path('ajax/boms/', views.GetBOMForProductView.as_view(), name='ajax_boms'),
    path('ajax/bom-details/', views.GetBOMDetailsView.as_view(), name='ajax_bom_details'),
]
