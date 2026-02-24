"""
نماذج إدخال نظام الشحن - Tony ERP
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    ShippingCompany, ShippingZone, ShippingRate, Shipment,
    ShipmentTracking, ShippingPickup, ShippingInvoice
)


class ShippingCompanyForm(forms.ModelForm):
    """نموذج شركة الشحن"""
    class Meta:
        model = ShippingCompany
        fields = [
            'name', 'code', 'contact_person', 'phone', 'email',
            'address', 'website', 'api_key', 'api_secret', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ShippingZoneForm(forms.ModelForm):
    """نموذج منطقة الشحن"""
    class Meta:
        model = ShippingZone
        fields = ['name', 'code', 'country', 'cities', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'cities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShippingRateForm(forms.ModelForm):
    """نموذج تعريفة الشحن"""
    class Meta:
        model = ShippingRate
        fields = [
            'company', 'zone', 'weight_from', 'weight_to',
            'base_rate', 'extra_kg_rate', 'delivery_days', 'is_active'
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'weight_from': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight_to': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'extra_kg_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShipmentForm(forms.ModelForm):
    """نموذج الشحنة"""
    class Meta:
        model = Shipment
        fields = [
            'company', 'sender_name', 'sender_phone', 'sender_address', 'sender_city',
            'receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city', 'zone',
            'description', 'weight', 'pieces', 'dimensions',
            'payment_type', 'shipping_cost', 'cod_amount', 'insurance_amount',
            'expected_delivery', 'reference_number', 'order_id', 'notes'
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'sender_name': forms.TextInput(attrs={'class': 'form-control'}),
            'sender_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'sender_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'sender_city': forms.TextInput(attrs={'class': 'form-control'}),
            'receiver_name': forms.TextInput(attrs={'class': 'form-control'}),
            'receiver_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'receiver_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'receiver_city': forms.TextInput(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pieces': forms.NumberInput(attrs={'class': 'form-control'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '30x20x15'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cod_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expected_delivery': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'order_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ShipmentTrackingForm(forms.ModelForm):
    """نموذج تتبع الشحنة"""
    class Meta:
        model = ShipmentTracking
        fields = ['status', 'location', 'description']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ShippingPickupForm(forms.ModelForm):
    """نموذج طلب الاستلام"""
    class Meta:
        model = ShippingPickup
        fields = [
            'company', 'pickup_address', 'pickup_city', 'contact_name', 'contact_phone',
            'scheduled_date', 'scheduled_time_from', 'scheduled_time_to', 'pieces_count', 'notes'
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pickup_city': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'scheduled_time_from': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'scheduled_time_to': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'pieces_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ShippingInvoiceForm(forms.ModelForm):
    """نموذج فاتورة الشحن"""
    class Meta:
        model = ShippingInvoice
        fields = [
            'company', 'invoice_date', 'due_date',
            'subtotal', 'tax_amount', 'discount', 'total', 'notes'
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
