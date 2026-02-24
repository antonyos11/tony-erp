"""
Advanced filters for inventory management
"""

import django_filters
from django import forms
from django.db import models
from .models import Product, Location, Stock

class ProductFilter(django_filters.FilterSet):
    """Advanced product filtering"""
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المنتج...'
        })
    )
    
    sku = django_filters.CharFilter(
        field_name='sku',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز المنتج...'
        })
    )
    
    barcode = django_filters.CharFilter(
        field_name='barcode',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'الباركود...'
        })
    )
    
    STOCK_STATUS_CHOICES = [
        ('', 'جميع الحالات'),
        ('in_stock', 'متوفر'),
        ('low_stock', 'مخزون منخفض'),
        ('out_of_stock', 'نفد المخزون'),
    ]
    
    stock_status = django_filters.ChoiceFilter(
        choices=STOCK_STATUS_CHOICES,
        method='filter_stock_status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    location = django_filters.ModelChoiceFilter(
        queryset=Location.objects.filter(is_active=True),
        method='filter_by_location',
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='جميع المواقع'
    )
    
    PRICE_RANGES = [
        ('', 'جميع الأسعار'),
        ('0-100', '0 - 100'),
        ('100-500', '100 - 500'),
        ('500-1000', '500 - 1000'),
        ('1000+', '1000+'),
    ]
    
    price_range = django_filters.ChoiceFilter(
        choices=PRICE_RANGES,
        method='filter_price_range',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    COST_RANGES = [
        ('', 'جميع التكاليف'),
        ('0-50', '0 - 50'),
        ('50-200', '50 - 200'),
        ('200-500', '200 - 500'),
        ('500+', '500+'),
    ]
    
    cost_range = django_filters.ChoiceFilter(
        choices=COST_RANGES,
        method='filter_cost_range',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    purchase_uom = django_filters.ChoiceFilter(
        field_name='purchase_uom',
        choices=Product.UOM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='جميع وحدات الشراء'
    )
    
    usage_uom = django_filters.ChoiceFilter(
        field_name='usage_uom',
        choices=Product.UOM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='جميع وحدات الاستخدام'
    )
    
    has_stock = django_filters.BooleanFilter(
        method='filter_has_stock',
        widget=forms.NullBooleanSelect(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Product
        fields = ['name', 'sku', 'barcode', 'stock_status', 'location', 
                 'price_range', 'cost_range', 'purchase_uom', 'usage_uom', 'has_stock']
    
    def filter_stock_status(self, queryset, name, value):
        if value == 'in_stock':
            return queryset.filter(
                id__in=[p.id for p in queryset if p.current_stock > p.min_stock]
            )
        elif value == 'low_stock':
            return queryset.filter(
                id__in=[p.id for p in queryset if p.is_low_stock and p.current_stock > 0]
            )
        elif value == 'out_of_stock':
            return queryset.filter(
                id__in=[p.id for p in queryset if p.current_stock == 0]
            )
        return queryset
    
    def filter_by_location(self, queryset, name, value):
        if value:
            return queryset.filter(stocks__location=value).distinct()
        return queryset
    
    def filter_price_range(self, queryset, name, value):
        if value == '0-100':
            return queryset.filter(price__lte=100)
        elif value == '100-500':
            return queryset.filter(price__gte=100, price__lte=500)
        elif value == '500-1000':
            return queryset.filter(price__gte=500, price__lte=1000)
        elif value == '1000+':
            return queryset.filter(price__gte=1000)
        return queryset
    
    def filter_cost_range(self, queryset, name, value):
        if value == '0-50':
            return queryset.filter(cost__lte=50)
        elif value == '50-200':
            return queryset.filter(cost__gte=50, cost__lte=200)
        elif value == '200-500':
            return queryset.filter(cost__gte=200, cost__lte=500)
        elif value == '500+':
            return queryset.filter(cost__gte=500)
        return queryset
    
    def filter_has_stock(self, queryset, name, value):
        """فلتر وجود مخزون - يتجاهل None"""
        if value is None:
            return queryset
        if value is True:
            return queryset.filter(id__in=[p.id for p in queryset if p.current_stock > 0])
        elif value is False:
            return queryset.filter(id__in=[p.id for p in queryset if p.current_stock == 0])
        return queryset


class LocationFilter(django_filters.FilterSet):
    """Advanced location filtering"""
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم الموقع...'
        })
    )
    
    code = django_filters.CharFilter(
        field_name='code',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز الموقع...'
        })
    )
    
    # نستخدم getattr لتفادي خطأ مؤقت إذا لم تُحمّل الخاصية بعد أثناء إعادة التحميل التلقائي
    _location_type_choices = getattr(Location, 'TYPE_CHOICES', getattr(Location, 'WAREHOUSE_TYPES', []))
    type = django_filters.ChoiceFilter(
        field_name='type',
        choices=_location_type_choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='جميع الأنواع'
    )
    
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    is_default = django_filters.BooleanFilter(
        field_name='is_default',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Location
        fields = ['name', 'code', 'type', 'is_active', 'is_default']


class StockFilter(django_filters.FilterSet):
    """Advanced stock filtering"""
    
    product__name = django_filters.CharFilter(
        field_name='product__name',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المنتج...'
        })
    )
    
    location = django_filters.ModelChoiceFilter(
        queryset=Location.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='جميع المواقع'
    )
    
    QUANTITY_RANGES = [
        ('', 'جميع الكميات'),
        ('0', 'بدون مخزون'),
        ('1-10', '1 - 10'),
        ('10-50', '10 - 50'),
        ('50-100', '50 - 100'),
        ('100+', '100+'),
    ]
    
    quantity_range = django_filters.ChoiceFilter(
        choices=QUANTITY_RANGES,
        method='filter_quantity_range',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Stock
        fields = ['product__name', 'location', 'quantity_range']
    
    def filter_quantity_range(self, queryset, name, value):
        if value == '0':
            return queryset.filter(quantity=0)
        elif value == '1-10':
            return queryset.filter(quantity__gte=1, quantity__lte=10)
        elif value == '10-50':
            return queryset.filter(quantity__gte=10, quantity__lte=50)
        elif value == '50-100':
            return queryset.filter(quantity__gte=50, quantity__lte=100)
        elif value == '100+':
            return queryset.filter(quantity__gte=100)
        return queryset