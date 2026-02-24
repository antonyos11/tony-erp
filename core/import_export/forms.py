# -*- coding: utf-8 -*-
"""
نماذج موديول الاستيراد والتصدير
"""

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import (
    ShippingAgent, ExportOrder, ExportOrderItem, ExportCertificate,
    FinancialApproval, PreExportInvoice,
    CustomsClearance, ImportOrder, ImportOrderItem, ImportCertificate,
    ReleaseOrder, ImportWaiver
)


class ShippingAgentForm(forms.ModelForm):
    """نموذج وكيل الشحن"""
    
    class Meta:
        model = ShippingAgent
        fields = [
            'name', 'name_en', 'agent_type', 'phone', 'mobile', 'email', 'fax',
            'website', 'address', 'city', 'country', 'license_number', 'license_expiry',
            'tax_number', 'commercial_reg', 'contact_person', 'contact_phone',
            'contact_email', 'credit_limit', 'payment_terms', 'currency', 'account',
            'is_active', 'is_preferred', 'rating', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'agent_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'fax': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'commercial_reg': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_preferred': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExportOrderForm(forms.ModelForm):
    """نموذج طلب التصدير"""
    
    class Meta:
        model = ExportOrder
        fields = [
            'reference', 'customer', 'destination_country', 'destination_port',
            'origin_port', 'order_date', 'expected_ship_date', 'expected_arrival_date',
            'shipment_type', 'shipping_agent', 'container_type', 'container_count',
            'incoterm', 'shipping_cost', 'insurance_cost', 'customs_cost', 'other_costs',
            'currency', 'exchange_rate', 'notes', 'special_instructions'
        ]
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-select select2'}),
            'destination_country': forms.Select(attrs={'class': 'form-select select2'}),
            'destination_port': forms.TextInput(attrs={'class': 'form-control'}),
            'origin_port': forms.TextInput(attrs={'class': 'form-control'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_ship_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_arrival_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shipment_type': forms.Select(attrs={'class': 'form-select'}),
            'shipping_agent': forms.Select(attrs={'class': 'form-select select2'}),
            'container_type': forms.TextInput(attrs={'class': 'form-control'}),
            'container_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'incoterm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FOB, CIF, EXW...'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customs_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_costs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExportOrderItemForm(forms.ModelForm):
    """نموذج بند طلب التصدير"""
    
    class Meta:
        model = ExportOrderItem
        fields = [
            'product', 'description', 'quantity', 'unit', 'unit_price',
            'hs_code', 'country_of_origin', 'gross_weight', 'net_weight',
            'packages_count', 'package_type', 'notes'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hs_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country_of_origin': forms.Select(attrs={'class': 'form-select'}),
            'gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'packages_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'package_type': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


ExportOrderItemFormSet = inlineformset_factory(
    ExportOrder, ExportOrderItem,
    form=ExportOrderItemForm,
    extra=1,
    can_delete=True
)


class FinancialApprovalForm(forms.ModelForm):
    """نموذج الموافقة المالية"""
    
    class Meta:
        model = FinancialApproval
        fields = [
            'export_order', 'requested_amount', 'currency',
            'justification', 'notes'
        ]
        widgets = {
            'export_order': forms.Select(attrs={'class': 'form-select select2'}),
            'requested_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'justification': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PreExportInvoiceForm(forms.ModelForm):
    """نموذج الفاتورة المبدئية"""
    
    class Meta:
        model = PreExportInvoice
        fields = [
            'export_order', 'invoice_date', 'validity_date', 'subtotal',
            'discount', 'tax_amount', 'shipping_cost', 'currency',
            'payment_terms', 'bank_details', 'notes'
        ]
        widgets = {
            'export_order': forms.Select(attrs={'class': 'form-select select2'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'validity_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'bank_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ExportCertificateForm(forms.ModelForm):
    """نموذج شهادة التصدير"""
    
    class Meta:
        model = ExportCertificate
        fields = [
            'number', 'certificate_type', 'export_order', 'issuing_authority',
            'issue_date', 'expiry_date', 'cost', 'document', 'notes'
        ]
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_type': forms.Select(attrs={'class': 'form-select'}),
            'export_order': forms.Select(attrs={'class': 'form-select select2'}),
            'issuing_authority': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CustomsClearanceForm(forms.ModelForm):
    """نموذج المخلص الجمركي"""
    
    class Meta:
        model = CustomsClearance
        fields = [
            'name', 'name_en', 'phone', 'mobile', 'email', 'address',
            'license_number', 'license_expiry', 'account', 'status', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ImportOrderForm(forms.ModelForm):
    """نموذج أمر الاستيراد"""
    
    class Meta:
        model = ImportOrder
        fields = [
            'reference', 'supplier', 'origin_country', 'origin_port', 'destination_port',
            'order_date', 'expected_ship_date', 'expected_arrival_date', 'shipment_type',
            'shipping_agent', 'customs_clearance', 'bl_number', 'container_numbers',
            'incoterm', 'shipping_cost', 'insurance_cost', 'customs_duties', 'customs_vat',
            'clearance_fees', 'other_costs', 'currency', 'exchange_rate', 'notes'
        ]
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select select2'}),
            'origin_country': forms.Select(attrs={'class': 'form-select select2'}),
            'origin_port': forms.TextInput(attrs={'class': 'form-control'}),
            'destination_port': forms.TextInput(attrs={'class': 'form-control'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_ship_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_arrival_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shipment_type': forms.Select(attrs={'class': 'form-select'}),
            'shipping_agent': forms.Select(attrs={'class': 'form-select select2'}),
            'customs_clearance': forms.Select(attrs={'class': 'form-select select2'}),
            'bl_number': forms.TextInput(attrs={'class': 'form-control'}),
            'container_numbers': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'incoterm': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'insurance_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customs_duties': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customs_vat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'clearance_fees': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_costs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ImportOrderItemForm(forms.ModelForm):
    """نموذج بند أمر الاستيراد"""
    
    class Meta:
        model = ImportOrderItem
        fields = [
            'product', 'description', 'quantity', 'unit', 'unit_price',
            'hs_code', 'customs_rate', 'gross_weight', 'net_weight', 'notes'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hs_code': forms.TextInput(attrs={'class': 'form-control'}),
            'customs_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


ImportOrderItemFormSet = inlineformset_factory(
    ImportOrder, ImportOrderItem,
    form=ImportOrderItemForm,
    extra=1,
    can_delete=True
)


class ImportCertificateForm(forms.ModelForm):
    """نموذج شهادة الاستيراد"""
    
    class Meta:
        model = ImportCertificate
        fields = [
            'number', 'certificate_type', 'import_order', 'issuing_authority',
            'issue_date', 'expiry_date', 'document', 'notes'
        ]
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_type': forms.Select(attrs={'class': 'form-select'}),
            'import_order': forms.Select(attrs={'class': 'form-select select2'}),
            'issuing_authority': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ReleaseOrderForm(forms.ModelForm):
    """نموذج إذن الإفراج"""
    
    class Meta:
        model = ReleaseOrder
        fields = [
            'import_order', 'customs_declaration_number', 'customs_office',
            'request_date', 'duties_paid', 'vat_paid', 'other_fees', 'notes'
        ]
        widgets = {
            'import_order': forms.Select(attrs={'class': 'form-select select2'}),
            'customs_declaration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'customs_office': forms.TextInput(attrs={'class': 'form-control'}),
            'request_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'duties_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'vat_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_fees': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ImportWaiverForm(forms.ModelForm):
    """نموذج التنازل"""
    
    class Meta:
        model = ImportWaiver
        fields = [
            'import_order', 'waiver_type', 'waivee_name', 'waivee_id',
            'waivee_phone', 'waiver_date', 'reason', 'waiver_amount', 'notes'
        ]
        widgets = {
            'import_order': forms.Select(attrs={'class': 'form-select select2'}),
            'waiver_type': forms.Select(attrs={'class': 'form-select'}),
            'waivee_name': forms.TextInput(attrs={'class': 'form-control'}),
            'waivee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'waivee_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'waiver_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'waiver_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
