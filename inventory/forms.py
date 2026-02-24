"""
نماذج المخزون
"""
from django import forms
from .models import Product, Category, Location


class ProductForm(forms.ModelForm):
    """نموذج إضافة/تعديل المنتج"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'barcode', 'description', 'category',
            'price', 'cost', 'min_stock',
            'show_in_store', 'store_featured', 'is_new', 'new_until', 'store_description',
            'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'store_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'new_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
