"""
Admin لتحليلات الذكاء الاصطناعي
"""

from django.contrib import admin
from .models import PredictionModel, Prediction, AIInsight, DataAnalysis


@admin.register(PredictionModel)
class PredictionModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'is_trained', 'training_accuracy', 'is_active', 'created_at']
    list_filter = ['model_type', 'is_trained', 'is_active']
    search_fields = ['name']


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['model', 'confidence', 'created_by', 'created_at']
    list_filter = ['model', 'created_at']
    readonly_fields = ['uuid', 'created_at']


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'priority', 'is_read', 'is_actioned', 'created_at']
    list_filter = ['insight_type', 'priority', 'is_read', 'is_actioned']
    search_fields = ['title', 'description']


@admin.register(DataAnalysis)
class DataAnalysisAdmin(admin.ModelAdmin):
    list_display = ['title', 'analysis_type', 'data_source', 'created_by', 'created_at']
    list_filter = ['analysis_type', 'created_at']
    search_fields = ['title']
