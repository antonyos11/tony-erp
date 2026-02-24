from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes
from django.db import models
from .models import (
    Showroom,
    ShowroomEmployee,
    ShowroomExpense,
    ShowroomPurchase,
    ShowroomPurchaseItem,
    ShowroomStockMovement,
    ShowroomPayrollEntry,
    ShowroomShift,
    ShowroomShiftAssignment,
    TemporaryWorker,
    ShowroomRentPayment,
)
from .serializers import (
    ShowroomSerializer,
    ShowroomEmployeeSerializer,
    ShowroomExpenseSerializer,
    ShowroomPurchaseSerializer,
    ShowroomStockMovementSerializer,
    ShowroomPayrollEntrySerializer,
    ShowroomTransferSerializer,
    ShowroomShiftSerializer,
    ShowroomShiftAssignmentSerializer,
    TemporaryWorkerSerializer,
    ShowroomRentPaymentSerializer,
)
from .permissions import HasShowroomAccess
from rest_framework.views import APIView
from .mixins import ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, get_active_showroom_id
from django.utils import timezone
from accounting.models import JournalEntry, JournalEntryItem, Account
from pos.models import POSOrder
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import path
from django.contrib.auth.decorators import login_required
from inventory.models import Location, Product, StockTransfer, StockTransferItem
from datetime import datetime, date


def _get_accessible_showroom_ids(user):
    if user.is_superuser:
        return list(Showroom.objects.values_list('id', flat=True))
    assigned = ShowroomEmployee.objects.filter(user=user, active=True)
    if assigned.filter(can_cross_access=True).exists():
        return list(Showroom.objects.values_list('id', flat=True))
    return list(assigned.values_list('showroom_id', flat=True))

class ShowroomViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Showroom.objects.select_related('location','manager').all()
    serializer_class = ShowroomSerializer
    permission_classes = [HasShowroomAccess]
    search_fields = ['code','name','name_ar']
    ordering_fields = ['code','name','opening_date']
    force_scope = False  # نسمح للـ cross_access أو السوبر برؤية الجميع

    def get_queryset(self):
        # استخدم الميراث + السماح بالوصول الكامل حسب منطق سابق عند الحاجة
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        from .models import ShowroomEmployee
        assigned = ShowroomEmployee.objects.filter(user=user, active=True)
        if assigned.filter(can_cross_access=True).exists():
            return qs
        allowed_ids = assigned.values_list('showroom_id', flat=True)
        return qs.filter(id__in=allowed_ids)

class ShowroomEmployeeViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomEmployee.objects.select_related('showroom','user').all()
    serializer_class = ShowroomEmployeeSerializer
    permission_classes = [HasShowroomAccess]
    search_fields = ['user__username','showroom__code']
    force_scope = False

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        from .models import ShowroomEmployee as SE
        assigned = SE.objects.filter(user=user, active=True)
        if assigned.filter(can_cross_access=True).exists():
            return qs
        allowed_ids = assigned.values_list('showroom_id', flat=True)
        return qs.filter(showroom_id__in=allowed_ids)

@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ShowroomPnLView(ShowroomActionPermissionMixin, APIView):
    permission_classes = [HasShowroomAccess]
    required_module = 'pos'
    required_action = 'view'
    def get(self, request, *args, **kwargs):
        showroom_id = request.query_params.get('showroom')
        period = request.query_params.get('period')  # YYYY-MM
        if not showroom_id:
            return Response({'detail':'showroom required'}, status=400)
        qs = JournalEntry.objects.filter(showroom_id=showroom_id, is_posted=True)
        if period:
            try:
                year, month = map(int, period.split('-'))
                qs = qs.filter(date__year=year, date__month=month)
            except Exception:
                return Response({'detail':'invalid period'}, status=400)
        item_qs = JournalEntryItem.objects.filter(journal_entry__in=qs).select_related('account')
        revenue = 0; expense = 0
        for it in item_qs:
            if it.account.account_type == 'revenue':
                revenue += float(it.amount) * (1 if it.type=='credit' else -1)
            elif it.account.account_type == 'expense':
                expense += float(it.amount) * (1 if it.type=='debit' else -1)
        gross_profit = revenue - expense
        return Response({'showroom': int(showroom_id), 'period': period, 'revenue': revenue, 'expenses': expense, 'gross_profit': gross_profit})

@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ShowroomKPIsView(ShowroomActionPermissionMixin, APIView):
    permission_classes = [HasShowroomAccess]
    required_module = 'pos'
    required_action = 'view'
    def get(self, request, *args, **kwargs):
        showroom_id = request.query_params.get('showroom')
        from pos.models import POSOrder
        today = timezone.now().date()
        # Filter by POSOrder.showroom directly; Location.showroom is a compatibility alias and not a real FK
        paid_qs = POSOrder.objects.filter(
            showroom_id=showroom_id,
            created_at__date=today,
            status='paid',
        )
        sales_today = (
            paid_qs.filter(is_return=False)
            .aggregate(total=models.Sum('total'))
            .get('total')
            or 0
        )
        returns_today = (
            paid_qs.filter(is_return=True)
            .aggregate(total=models.Sum('total'))
            .get('total')
            or 0
        )
        net_sales = (sales_today or 0) - (returns_today or 0)
        order_count = paid_qs.count()
        avg_ticket = float(net_sales) / order_count if order_count else 0
        return Response(
            {
                'showroom': int(showroom_id) if showroom_id else None,
                'sales_today': sales_today,
                'returns_today': returns_today,
                'net_sales': net_sales,
                'orders': order_count,
                'avg_ticket': avg_ticket,
            }
        )

@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ActiveShowroomView(APIView):
    """API بسيط لجلب أو تعيين المعرض النشط في الجلسة.
    GET => {'active_showroom': id or null}
    POST {"showroom": <id>} => يضبط المفتاح بعد التحقق من التعيين للمستخدم.
    """
    def get(self, request, *args, **kwargs):
        sid = get_active_showroom_id(request)
        return Response({'active_showroom': sid})

    def post(self, request, *args, **kwargs):
        showroom_id = request.data.get('showroom')
        if not showroom_id:
            return Response({'detail':'showroom required'}, status=400)
        try:
            showroom_id = int(showroom_id)
        except Exception:
            return Response({'detail':'invalid showroom id'}, status=400)
        user = request.user
        if not user.is_authenticated:
            return Response({'detail':'auth required'}, status=401)
        from .models import ShowroomEmployee
        if not (user.is_superuser or ShowroomEmployee.objects.filter(user=user, showroom_id=showroom_id, active=True).exists()):
            return Response({'detail':'not assigned to this showroom'}, status=403)
        # تحقق إضافي: لو المستخدم له عدة معارض لكن ليس cross_access نسمح له التبديل بينها طالما معين لها
        request.session['ACTIVE_SHOWROOM_ID'] = showroom_id
        request.session.modified = True
        return Response({'active_showroom': showroom_id})


class ShowroomExpenseViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomExpense.objects.select_related('showroom','created_by','approved_by')
    serializer_class = ShowroomExpenseSerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'expenses'
    search_fields = ['description','category']
    ordering_fields = ['created_at','amount']

    def initial(self, request, *args, **kwargs):
        # ضبط الفعل المطلوب حسب العملية
        if self.action in ['create']:
            self.required_action = 'add'
        elif self.action in ['update', 'partial_update']:
            self.required_action = 'change'
        elif self.action in ['approve_expense', 'reject_expense']:
            self.required_action = 'approve'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_expense(self, request, pk=None):
        obj = self.get_object()
        obj.approve(user=request.user)
        return Response({'status': obj.status})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_expense(self, request, pk=None):
        obj = self.get_object()
        reason = request.data.get('reason','')
        obj.reject(user=request.user, reason=reason)
        return Response({'status': obj.status, 'reason': obj.rejection_note})


class ShowroomPurchaseViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomPurchase.objects.select_related('showroom','supplier','location','created_by','confirmed_by').prefetch_related('items__product')
    serializer_class = ShowroomPurchaseSerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'purchases'
    search_fields = ['number','supplier__name']
    ordering_fields = ['created_at','status','total']

    def initial(self, request, *args, **kwargs):
        if self.action in ['create']:
            self.required_action = 'add'
        elif self.action in ['update', 'partial_update']:
            self.required_action = 'change'
        elif self.action in ['confirm_purchase']:
            self.required_action = 'approve'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_purchase(self, request, pk=None):
        obj = self.get_object()
        obj.confirm(user=request.user)
        return Response({'status': obj.status})


class ShowroomStockMovementViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomStockMovement.objects.select_related('showroom','location','product','created_by')
    serializer_class = ShowroomStockMovementSerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'inventory'
    search_fields = ['reference','note']
    ordering_fields = ['created_at']

    def initial(self, request, *args, **kwargs):
        if self.action in ['create']:
            self.required_action = 'add'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ShowroomPayrollEntryViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomPayrollEntry.objects.select_related('showroom','employee','approved_by')
    serializer_class = ShowroomPayrollEntrySerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'payroll'
    search_fields = ['note','employee__user__username']
    ordering_fields = ['period','amount','status']

    def initial(self, request, *args, **kwargs):
        if self.action in ['create']:
            self.required_action = 'add'
        elif self.action in ['approve_entry']:
            self.required_action = 'approve'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_entry(self, request, pk=None):
        obj = self.get_object()
        obj.approve(user=request.user)
        return Response({'status': obj.status})


class ShowroomShiftViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomShift.objects.select_related('showroom')
    serializer_class = ShowroomShiftSerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'hr'
    search_fields = ['name']
    ordering_fields = ['start_time','name']

    def initial(self, request, *args, **kwargs):
        if self.action in ['create']:
            self.required_action = 'add'
        elif self.action in ['update', 'partial_update']:
            self.required_action = 'change'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)


class ShowroomShiftAssignmentViewSet(ShowroomActionPermissionMixin, ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ShowroomShiftAssignment.objects.select_related('shift','employee','employee__showroom')
    serializer_class = ShowroomShiftAssignmentSerializer
    permission_classes = [HasShowroomAccess]
    required_module = 'hr'
    SHOWROOM_FIELD_CANDIDATES = ActiveShowroomScopedQuerysetMixin.SHOWROOM_FIELD_CANDIDATES + ['shift__showroom', 'employee__showroom']
    search_fields = ['employee__user__username','shift__name']
    ordering_fields = ['day_of_week']

    def initial(self, request, *args, **kwargs):
        if self.action in ['create']:
            self.required_action = 'add'
        elif self.action in ['update', 'partial_update']:
            self.required_action = 'change'
        else:
            self.required_action = 'view'
        super().initial(request, *args, **kwargs)


@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ShowroomTransferAPIView(ShowroomActionPermissionMixin, APIView):
    permission_classes = [HasShowroomAccess]
    required_module = 'inventory'
    required_action = 'transfer'

    def post(self, request, *args, **kwargs):
        sid = get_active_showroom_id(request)
        if not sid:
            return Response({'detail': 'showroom required'}, status=400)
        ser = ShowroomTransferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        to_sid = data['to_showroom']
        if sid == to_sid:
            return Response({'detail': 'cannot transfer to same showroom'}, status=400)
        # تحقق من صلاحية المستخدم على المعرض المصدر
        if not (request.user.is_superuser or ShowroomEmployee.objects.filter(user=request.user, active=True).filter(models.Q(showroom_id=sid) | models.Q(can_cross_access=True)).exists()):
            return Response({'detail': 'not assigned to source showroom'}, status=403)
        src_loc = Location.objects.filter(showroom_link_id=sid).first()
        dst_loc = Location.objects.filter(showroom_link_id=to_sid).first()
        if not src_loc or not dst_loc:
            return Response({'detail': 'source/destination location missing'}, status=400)
        product = get_object_or_404(Product, pk=data['product_id'])
        qty = data['quantity']
        note = data.get('note', '')
        try:
            transfer = StockTransfer.objects.create(source=src_loc, destination=dst_loc, status='draft', notes=note, number='')
            StockTransferItem.objects.create(transfer=transfer, product=product, quantity=qty)
            transfer.confirm()
            # سجل حركتين
            ShowroomStockMovement.objects.create(
                showroom_id=sid,
                location=src_loc,
                product=product,
                quantity=-qty,
                movement_type=ShowroomStockMovement.MovementType.TRANSFER_OUT,
                reference=transfer.number,
                created_by=request.user,
                note=note,
            )
            ShowroomStockMovement.objects.create(
                showroom_id=to_sid,
                location=dst_loc,
                product=product,
                quantity=qty,
                movement_type=ShowroomStockMovement.MovementType.TRANSFER_IN,
                reference=transfer.number,
                created_by=request.user,
                note=note,
            )
            return Response({'transfer': transfer.number, 'from': sid, 'to': to_sid, 'product': product.id, 'quantity': qty})
        except Exception as exc:
            return Response({'detail': str(exc)}, status=400)

def manage_extra_perms(request, showroom_id, employee_id):
    emp = get_object_or_404(ShowroomEmployee, pk=employee_id, showroom_id=showroom_id, active=True)
    # يسمح فقط لمدير المعرض أو سوبر يوزر
    if not (request.user.is_superuser or ShowroomEmployee.objects.filter(showroom_id=showroom_id, user=request.user, role__in=['manager','supervisor'], active=True).exists()):
        return render(request, '403.html', status=403)
    if request.method == 'POST':
        raw = request.POST.get('extra_perms','').strip()
        entries = [e.strip() for e in raw.split('\n') if e.strip()]
        emp.extra_perms = entries
        emp.save(update_fields=['extra_perms'])
        messages.success(request, 'تم تحديث الصلاحيات الإضافية')
        return redirect(request.path)
    current_list = '\n'.join(emp.extra_perms)
    return render(request, 'showrooms/manage_extra_perms.html', {'employee': emp, 'current_list': current_list})


def _apply_date_filters(qs, date_field, start_date, end_date):
    if start_date:
        qs = qs.filter(**{f"{date_field}__date__gte": start_date})
    if end_date:
        qs = qs.filter(**{f"{date_field}__date__lte": end_date})
    return qs


def _parse_date_param(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def _aggregate_showroom_summary(showroom_id, start_date=None, end_date=None):
    sales_qs = POSOrder.objects.filter(showroom_id=showroom_id, status='paid')
    sales_qs = _apply_date_filters(sales_qs, 'created_at', start_date, end_date)
    sales_total = sales_qs.filter(is_return=False).aggregate(total=models.Sum('total'))['total'] or 0
    returns_total = sales_qs.filter(is_return=True).aggregate(total=models.Sum('total'))['total'] or 0

    expense_qs = ShowroomExpense.objects.filter(showroom_id=showroom_id, status=ShowroomExpense.Status.APPROVED)
    expense_qs = _apply_date_filters(expense_qs, 'created_at', start_date, end_date)
    expenses_total = expense_qs.aggregate(total=models.Sum('amount'))['total'] or 0

    purchase_qs = ShowroomPurchase.objects.filter(showroom_id=showroom_id, status='confirmed')
    purchase_qs = _apply_date_filters(purchase_qs, 'created_at', start_date, end_date)
    purchases_total = purchase_qs.aggregate(total=models.Sum('total'))['total'] or 0

    payroll_qs = ShowroomPayrollEntry.objects.filter(showroom_id=showroom_id, status__in=[ShowroomPayrollEntry.Status.APPROVED, ShowroomPayrollEntry.Status.PAID])
    if start_date:
        payroll_qs = payroll_qs.filter(period__gte=start_date)
    if end_date:
        payroll_qs = payroll_qs.filter(period__lte=end_date)
    payroll_total = payroll_qs.aggregate(total=models.Sum('amount'))['total'] or 0

    net_sales = (sales_total or 0) - (returns_total or 0)
    return {
        'showroom': showroom_id,
        'sales': sales_total,
        'returns': returns_total,
        'net_sales': net_sales,
        'expenses': expenses_total,
        'purchases': purchases_total,
        'payroll': payroll_total,
        'net_after_costs': net_sales - (expenses_total or 0) - (purchases_total or 0) - (payroll_total or 0),
    }


@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ShowroomSummaryView(ShowroomActionPermissionMixin, APIView):
    permission_classes = [HasShowroomAccess]
    required_module = 'pos'
    required_action = 'view'

    def get(self, request, *args, **kwargs):
        showroom_id = request.query_params.get('showroom')
        if not showroom_id:
            return Response({'detail': 'showroom required'}, status=400)
        try:
            showroom_id = int(showroom_id)
        except Exception:
            return Response({'detail': 'invalid showroom id'}, status=400)
        try:
            start = _parse_date_param(request.query_params.get('start'))
            end = _parse_date_param(request.query_params.get('end'))
        except ValueError:
            return Response({'detail': 'invalid date format, use YYYY-MM-DD'}, status=400)
        data = _aggregate_showroom_summary(showroom_id, start, end)
        return Response(data)


@extend_schema(tags=['Showrooms'], responses=OpenApiTypes.OBJECT)
class ShowroomComparisonView(ShowroomActionPermissionMixin, APIView):
    permission_classes = [HasShowroomAccess]
    required_module = 'pos'
    required_action = 'view'

    def get(self, request, *args, **kwargs):
        try:
            start = _parse_date_param(request.query_params.get('start'))
            end = _parse_date_param(request.query_params.get('end'))
        except ValueError:
            return Response({'detail': 'invalid date format, use YYYY-MM-DD'}, status=400)
        ids = _get_accessible_showroom_ids(request.user)
        data = [_aggregate_showroom_summary(sid, start, end) for sid in ids]
        return Response({'showrooms': data})


class TemporaryWorkerViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet لإدارة العمالة المؤقتة
    """
    queryset = TemporaryWorker.objects.select_related('showroom', 'created_by', 'expense_account').all()
    serializer_class = TemporaryWorkerSerializer
    permission_classes = [HasShowroomAccess]
    filterset_fields = ['showroom', 'worker_type', 'is_paid', 'is_active']
    search_fields = ['worker_name', 'job_title', 'national_id']
    ordering_fields = ['start_date', 'total_amount', 'created_at']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        from .models import ShowroomEmployee
        assigned = ShowroomEmployee.objects.filter(user=user, active=True)
        if assigned.filter(can_cross_access=True).exists():
            return qs
        allowed_ids = assigned.values_list('showroom_id', flat=True)
        return qs.filter(showroom_id__in=allowed_ids)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """تحديد العامل كمدفوع"""
        worker = self.get_object()
        payment_ref = request.data.get('payment_reference', '')
        
        worker.is_paid = True
        worker.payment_date = timezone.now().date()
        if payment_ref:
            worker.payment_reference = payment_ref
        worker.save()
        
        # إنشاء القيد المحاسبي إذا كان مطلوب
        if request.data.get('create_journal_entry', False):
            try:
                from .accounting_helpers import create_temporary_worker_payment_entry
                entry = create_temporary_worker_payment_entry(worker, user=request.user)
                return Response({
                    'status': 'paid',
                    'journal_entry': entry.id if entry else None,
                    'message': 'تم السداد وإنشاء القيد المحاسبي'
                })
            except Exception as e:
                return Response({
                    'status': 'paid',
                    'journal_entry': None,
                    'message': f'تم السداد لكن فشل إنشاء القيد: {str(e)}'
                }, status=status.HTTP_206_PARTIAL_CONTENT)
        
        return Response({'status': 'paid', 'message': 'تم السداد بنجاح'})


class ShowroomRentPaymentViewSet(ActiveShowroomScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet لإدارة دفعات الإيجار
    """
    queryset = ShowroomRentPayment.objects.select_related('showroom', 'created_by', 'journal_entry').all()
    serializer_class = ShowroomRentPaymentSerializer
    permission_classes = [HasShowroomAccess]
    filterset_fields = ['showroom', 'status']
    search_fields = ['payment_reference', 'notes']
    ordering_fields = ['payment_date', 'amount', 'created_at']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        from .models import ShowroomEmployee
        assigned = ShowroomEmployee.objects.filter(user=user, active=True)
        if assigned.filter(can_cross_access=True).exists():
            return qs
        allowed_ids = assigned.values_list('showroom_id', flat=True)
        return qs.filter(showroom_id__in=allowed_ids)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """تحديد الدفعة كمدفوعة"""
        payment = self.get_object()
        payment_ref = request.data.get('payment_reference', '')
        
        payment.mark_as_paid(user=request.user, payment_ref=payment_ref)
        
        # إنشاء القيد المحاسبي
        if request.data.get('create_journal_entry', True):
            try:
                from .accounting_helpers import create_rent_payment_entry
                entry = create_rent_payment_entry(payment, user=request.user)
                return Response({
                    'status': 'paid',
                    'journal_entry': entry.id if entry else None,
                    'message': 'تم السداد وإنشاء القيد المحاسبي'
                })
            except Exception as e:
                return Response({
                    'status': 'paid',
                    'journal_entry': None,
                    'message': f'تم السداد لكن فشل إنشاء القيد: {str(e)}'
                }, status=status.HTTP_206_PARTIAL_CONTENT)
        
        return Response({'status': 'paid', 'message': 'تم السداد بنجاح'})
    
    @action(detail=False, methods=['post'])
    def check_overdue(self, request):
        """فحص جميع الدفعات المتأخرة"""
        from .accounting_helpers import check_and_mark_overdue_payments
        count = check_and_mark_overdue_payments()
        return Response({
            'overdue_count': count,
            'message': f'تم تحديد {count} دفعة كمتأخرة'
        })
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """الحصول على جميع الدفعات المتأخرة"""
        qs = self.get_queryset().filter(status=ShowroomRentPayment.PaymentStatus.OVERDUE)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def auto_generate(self, request):
        """إنشاء دفعات إيجار تلقائية لمعرض"""
        showroom_id = request.data.get('showroom_id')
        months = request.data.get('months', 12)
        
        if not showroom_id:
            return Response({'error': 'showroom_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            showroom = Showroom.objects.get(id=showroom_id)
            from .accounting_helpers import auto_create_monthly_rent_payments
            payments = auto_create_monthly_rent_payments(showroom, months=months)
            
            return Response({
                'count': len(payments),
                'message': f'تم إنشاء {len(payments)} دفعة بنجاح',
                'payments': [{'id': p.id, 'date': p.payment_date, 'amount': str(p.amount)} for p in payments]
            })
        except Showroom.DoesNotExist:
            return Response({'error': 'المعرض غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@login_required
def property_management_view(request):
    """
    صفحة إدارة الملكية والعقود
    """
    return render(request, 'showrooms/property_management.html')
