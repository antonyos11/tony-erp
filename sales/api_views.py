from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Invoice, InvoicePayment
from .api_serializers import InvoiceSerializer, InvoicePaymentSerializer
from partners.models import Customer
from core.models import AuditLog
from .utils import build_customer_statement, bump_customer_statement_version
from rest_framework.exceptions import ValidationError
from showrooms.mixins import ActiveShowroomScopedQuerysetMixin

class InvoiceViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related('customer').all().order_by('-id')
    serializer_class = InvoiceSerializer
    filterset_fields = ['customer']
    search_fields = ['number', 'customer__name']
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """إنشاء فاتورة جديدة مع ربط المستخدم والمعرض"""
        extra = {}
        sid = getattr(self.request, 'active_showroom_id', None)
        if sid:
            extra['showroom_id'] = sid
        invoice = serializer.save(created_by=self.request.user, **extra)
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action=AuditLog.ACTION_CREATE,
                model_name='Invoice',
                app_label='sales',
                object_id=str(invoice.pk),
                object_repr=str(invoice),
            )
        except Exception:
            pass

    def perform_update(self, serializer):
        """تحديث فاتورة مع التحقق من الحالة"""
        instance = serializer.instance
        if hasattr(instance, 'status') and instance.status in ('posted', 'cancelled'):
            raise ValidationError({'detail': 'لا يمكن تعديل فاتورة مرحّلة أو ملغاة'})
        obj = serializer.save()
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action=AuditLog.ACTION_UPDATE,
                model_name='Invoice',
                app_label='sales',
                object_id=str(obj.pk),
                object_repr=str(obj),
                changes={'api': 'update'},
            )
        except Exception:
            pass

    def destroy(self, request, *args, **kwargs):
        """حذف فاتورة مع التحقق من الحالة"""
        instance = self.get_object()
        if hasattr(instance, 'status') and instance.status in ('posted', 'cancelled'):
            return Response(
                {'detail': 'لا يمكن حذف فاتورة مرحّلة أو ملغاة'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_DELETE,
                model_name='Invoice',
                app_label='sales',
                object_id=str(instance.pk),
                object_repr=str(instance),
            )
        except Exception:
            pass
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        # simple redirect to existing HTML or summary JSON
        invoice = self.get_object()
        return Response({'id': invoice.id, 'number': invoice.number, 'remaining': invoice.remaining, 'paid': invoice.paid})

    @action(detail=True, methods=['post'])
    def post_invoice(self, request, pk=None):
        """ترحيل الفاتورة"""
        invoice = self.get_object()
        if hasattr(invoice, 'status') and invoice.status == 'posted':
            return Response({'error': 'الفاتورة مرحّلة بالفعل'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if hasattr(invoice, 'post'):
                invoice.post()
            else:
                invoice.status = 'posted'
                invoice.save(update_fields=['status'])
            return Response({'status': 'تم ترحيل الفاتورة بنجاح'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """إلغاء الفاتورة"""
        invoice = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'يجب إدخال سبب الإلغاء'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if hasattr(invoice, 'cancel'):
                invoice.cancel(reason=reason, cancelled_by=request.user)
            else:
                invoice.status = 'cancelled'
                invoice.save(update_fields=['status'])
            return Response({'status': 'تم إلغاء الفاتورة'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_invoice_api(request):
    """
    API endpoint لإنشاء فاتورة جديدة
    """
    try:
        # التحقق من البيانات المطلوبة
        customer_id = request.data.get('customer')
        if not customer_id:
            return Response({
                'error': True,
                'status_code': 400,
                'details': {'customer': ['This field is required.']}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # التحقق من وجود العميل
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'error': True,
                'status_code': 400,
                'details': {'customer': ['Invalid customer ID.']}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # إنشاء الفاتورة
        with transaction.atomic():
            invoice_data = {
                'customer': customer,
                'date': request.data.get('date'),
                'due_date': request.data.get('due_date'),
                'discount': request.data.get('discount', 0),
                'created_by': request.user,
            }
            
            # إضافة showroom إذا كان موجود
            showroom_id = getattr(request, 'active_showroom_id', None)
            if showroom_id:
                invoice_data['showroom_id'] = showroom_id
            
            invoice = Invoice.objects.create(**invoice_data)
            
            # Audit log
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.ACTION_CREATE,
                    model_name='Invoice',
                    app_label='sales',
                    object_id=str(invoice.pk),
                    object_repr=str(invoice),
                )
            except Exception:
                pass  # Don't fail if audit log fails
        
        # إرجاع الفاتورة المنشأة
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': True,
            'status_code': 500,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InvoicePaymentViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = InvoicePayment.objects.select_related('invoice', 'customer').all().order_by('-date', '-id')
    serializer_class = InvoicePaymentSerializer
    filterset_fields = ['invoice', 'customer', 'payment_method']
    search_fields = ['receipt_number', 'reference', 'invoice__number']
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        invoice = get_object_or_404(Invoice, pk=self.request.data.get('invoice'))
        extra = {}
        sid = getattr(self.request, 'active_showroom_id', None)
        if sid and 'showroom' in [f.name for f in serializer.Meta.model._meta.fields]:
            extra['showroom_id'] = sid
        try:
            with transaction.atomic():
                inst = serializer.save(invoice=invoice, customer=invoice.customer, created_by=self.request.user, **extra)
            bump_customer_statement_version(invoice.customer_id)
            try:
                AuditLog.objects.create(
                    user=self.request.user,
                    action=AuditLog.ACTION_CREATE,
                    model_name='InvoicePayment',
                    app_label='sales',
                    object_id=str(inst.pk),
                    object_repr=str(inst),
                    changes={'api': 'create'}
                )
            except Exception:
                pass
            return inst
        except ValueError as e:
            raise ValidationError({'detail': str(e)})

    def perform_update(self, serializer):
        inst = serializer.instance
        if inst.locked:
            raise ValidationError({'detail': 'Locked (printed) payment cannot be modified'})
        try:
            obj = serializer.save()
            bump_customer_statement_version(obj.customer_id)
        except ValueError as e:
            raise ValidationError({'detail': str(e)})
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action=AuditLog.ACTION_UPDATE,
                model_name='InvoicePayment',
                app_label='sales',
                object_id=str(obj.pk),
                object_repr=str(obj),
                changes={'api': 'update'}
            )
        except Exception:
            pass
        return obj

    def destroy(self, request, *args, **kwargs):
        inst = self.get_object()
        if inst.locked:
            return Response({'detail': 'Locked (printed) payment cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            bump_customer_statement_version(inst.customer_id)
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.ACTION_DELETE,
                model_name='InvoicePayment',
                app_label='sales',
                object_id=str(inst.pk),
                object_repr=str(inst),
                changes={'api': 'delete'}
            )
        except Exception:
            pass
        return super().destroy(request, *args, **kwargs)


class CustomerStatementSerializer(serializers.Serializer):
    """Serializer for customer statement response - for API documentation"""
    customer = serializers.CharField(read_only=True)
    customer_id = serializers.IntegerField(read_only=True)
    html_url = serializers.URLField(read_only=True)
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    transactions = serializers.ListField(read_only=True)
    closing_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


@extend_schema(tags=['Sales'])
class CustomerStatementViewSet(viewsets.ViewSet):
    """ViewSet for customer statement generation"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomerStatementSerializer  # For drf-spectacular

    def list(self, request):
        return Response({'detail': 'Provide customer id e.g. /api/sales/statements/<id>/'})

    def retrieve(self, request, pk=None):
        customer = get_object_or_404(Customer, pk=pk)
        if not request.user.has_perm('sales.print_customerstatement'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('no permission to view customer statement')
        from django.utils.dateparse import parse_date
        date_from = parse_date(request.GET.get('date_from')) if request.GET.get('date_from') else None
        date_to = parse_date(request.GET.get('date_to')) if request.GET.get('date_to') else None
        if date_from and not date_to:
            from datetime import date as _date
            date_to = _date.today()
        data = build_customer_statement(customer, date_from=date_from, date_to=date_to)
        from django.urls import reverse
        data.update({
            'customer': customer.name,
            'customer_id': customer.id,
            'html_url': request.build_absolute_uri(reverse('sales:customer_statement', args=[customer.pk]))
        })
        return Response(data)
