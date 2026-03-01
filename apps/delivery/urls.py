"""
URLs تطبيق التوصيل — RITA ERP
"""
from django.urls import path
from apps.delivery import views

app_name = 'delivery'

urlpatterns = [
    # مناطق التوصيل
    path('zones/',                        views.DeliveryZoneListView.as_view(),    name='zone_list'),

    # أوامر التوصيل
    path('orders/',                       views.DeliveryOrderListView.as_view(),   name='order_list'),
    path('orders/create/',                views.DeliveryOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/tracking/',     views.DeliveryTrackingView.as_view(),    name='order_tracking'),
]
