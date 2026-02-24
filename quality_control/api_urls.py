"""
API URLs for Quality Control Module - Tony ERP
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'standards', api.QualityStandardViewSet, basename='quality-standard')
router.register(r'inspection-types', api.InspectionTypeViewSet, basename='inspection-type')
router.register(r'inspections', api.QualityInspectionViewSet, basename='quality-inspection')
router.register(r'issues', api.QualityIssueViewSet, basename='quality-issue')

urlpatterns = [
    path('', include(router.urls)),
]
