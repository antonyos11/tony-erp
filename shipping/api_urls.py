"""
API URLs for Shipping Module - Tony ERP
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'companies', api.ShippingCompanyViewSet, basename='shipping-company')
router.register(r'zones', api.ShippingZoneViewSet, basename='shipping-zone')
router.register(r'rates', api.ShippingRateViewSet, basename='shipping-rate')
router.register(r'shipments', api.ShipmentViewSet, basename='shipment')

urlpatterns = [
    path('', include(router.urls)),
]
