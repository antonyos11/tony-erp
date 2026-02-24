"""
REST API للفوترة الإلكترونية ZATCA
"""

from rest_framework import serializers
from .models import ZATCAConfiguration, EInvoice, EInvoiceLog


class ZATCAConfigurationSerializer(serializers.ModelSerializer):
    """إعدادات ZATCA"""
    
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = ZATCAConfiguration
        fields = '__all__'
        extra_kwargs = {
            'private_key': {'write_only': True},
            'certificate_password': {'write_only': True},
        }


class EInvoiceLogSerializer(serializers.ModelSerializer):
    """سجل الفواتير الإلكترونية"""
    
    class Meta:
        model = EInvoiceLog
        fields = '__all__'


class EInvoiceSerializer(serializers.ModelSerializer):
    """الفاتورة الإلكترونية"""
    
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    invoice_date = serializers.DateField(source='invoice.invoice_date', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer.name', read_only=True)
    total_amount = serializers.DecimalField(
        source='invoice.total_amount',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    logs = EInvoiceLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = EInvoice
        fields = '__all__'
        read_only_fields = [
            'uuid', 'invoice_hash', 'previous_invoice_hash',
            'qr_code', 'xml_invoice', 'signed_xml',
            'zatca_response', 'reported_at', 'cleared_at'
        ]


class EInvoiceListSerializer(serializers.ModelSerializer):
    """قائمة الفواتير الإلكترونية المبسطة"""
    
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    customer_name = serializers.CharField(source='invoice.customer.name', read_only=True)
    
    class Meta:
        model = EInvoice
        fields = [
            'id', 'invoice', 'invoice_number', 'customer_name',
            'invoice_type', 'status', 'reported_at', 'cleared_at'
        ]


class QRCodeResponseSerializer(serializers.Serializer):
    """استجابة توليد QR Code"""
    
    qr_code = serializers.CharField()
    success = serializers.BooleanField()
    message = serializers.CharField()


class XMLResponseSerializer(serializers.Serializer):
    """استجابة توليد XML"""
    
    xml_invoice = serializers.CharField()
    invoice_hash = serializers.CharField()
    success = serializers.BooleanField()
    message = serializers.CharField()


class ZATCAReportResponseSerializer(serializers.Serializer):
    """استجابة الإبلاغ لـ ZATCA"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    zatca_response = serializers.JSONField()
    reported_at = serializers.DateTimeField(required=False)
