"""
تسجيل نماذج المخزون في لوحة الإدارة
"""
from django.contrib import admin
from .models import Category, UnitOfMeasure, Product, BillOfMaterials, BOMLine, StockMove, StockLevel


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']
    search_fields = ['name']
    ordering = ['name']


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol']
    search_fields = ['name', 'symbol']
    ordering = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'product_type', 'category', 'unit', 'cost_price', 'retail_price', 'is_active']
    list_filter = ['product_type', 'category', 'valuation_method', 'is_taxable', 'is_active']
    search_fields = ['code', 'name', 'barcode']
    ordering = ['code']


class BOMLineInline(admin.TabularInline):
    model = BOMLine
    extra = 1


@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'is_default', 'is_active']
    list_filter = ['is_default', 'is_active']
    search_fields = ['name', 'product__name', 'product__code']
    inlines = [BOMLineInline]


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ['move_number', 'date', 'move_type', 'product', 'quantity', 'unit_cost', 'warehouse_from', 'warehouse_to']
    list_filter = ['move_type', 'warehouse_from', 'warehouse_to']
    search_fields = ['move_number', 'product__name', 'product__code']
    ordering = ['-date']


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'average_cost', 'last_updated']
    list_filter = ['warehouse']
    search_fields = ['product__name', 'product__code']

