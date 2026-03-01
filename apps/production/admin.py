"""
تسجيل نماذج الإنتاج في لوحة الإدارة
"""
from django.contrib import admin
from .models import ProductionLine, ProductionStageTemplate, StageStep, ProductionOrder, ProductionStage, MaterialConsumption


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = ['name', 'supervisor', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']


class StageStepInline(admin.TabularInline):
    model = StageStep
    extra = 1
    ordering = ['order']


@admin.register(ProductionStageTemplate)
class ProductionStageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_category']
    search_fields = ['name']
    inlines = [StageStepInline]


class ProductionStageInline(admin.TabularInline):
    model = ProductionStage
    extra = 0


class MaterialConsumptionInline(admin.TabularInline):
    model = MaterialConsumption
    extra = 0


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'date', 'product', 'quantity', 'quantity_produced', 'status', 'production_line']
    list_filter = ['status', 'production_line']
    search_fields = ['order_number', 'product__name', 'product__code']
    ordering = ['-date']
    inlines = [ProductionStageInline, MaterialConsumptionInline]


@admin.register(ProductionStage)
class ProductionStageAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'step', 'status', 'started_at', 'completed_at', 'worker_count']
    list_filter = ['status']
    search_fields = ['production_order__order_number']


@admin.register(MaterialConsumption)
class MaterialConsumptionAdmin(admin.ModelAdmin):
    list_display = ['production_order', 'raw_material', 'planned_quantity', 'actual_quantity', 'waste_quantity', 'total_cost']
    list_filter = ['raw_material']
    search_fields = ['production_order__order_number', 'raw_material__name']

