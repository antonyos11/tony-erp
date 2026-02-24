from rest_framework import serializers
from .models import Invoice, InvoicePayment

class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePayment
        fields = ['id', 'invoice', 'customer', 'receipt_number', 'date', 'amount', 'payment_method', 'reference', 'description', 'locked', 'printed_count']
        read_only_fields = ['receipt_number', 'locked', 'printed_count', 'customer']

class SalesInvoiceDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for sales.Invoice with computed fields"""
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'customer', 'date', 'due_date', 'discount', 'paid', 'total', 'remaining']
        read_only_fields = ['paid', 'total', 'remaining']


# Alias for backward compatibility
InvoiceSerializer = SalesInvoiceDetailSerializer
