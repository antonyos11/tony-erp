from rest_framework import viewsets, permissions, filters, pagination, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import models
from django.utils import timezone
from inventory.models import Product, Location, Stock
from partners.models import Customer, Supplier
from sales.models import Invoice
from purchases.models import PurchaseBill, PurchaseOrder
from accounting.models import Revenue, Expense, Account, JournalEntry
from core.models import Company, AuditLog
from crm.models import Customer as CRMCustomer
from branches.models import Branch
from notifications.models import Notification
from users.models import UserRole, ModulePermission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .permissions import DjangoModelViewPermissions, RequireAuditViewPerm
from .serializers import (
    ProductSerializer, LocationSerializer, StockSerializer,
    CustomerSerializer, SupplierSerializer,
    InvoiceSerializer, PurchaseBillSerializer,
    RevenueSerializer, ExpenseSerializer, CompanySerializer, AuditLogSerializer,
    CRMCustomerSerializer, EnhancedInvoiceSerializer, BranchSerializer, NotificationSerializer,
    PurchaseOrderSerializer, PurchaseOrderItemSerializer,
    UserSerializer, UserRoleSerializer, ModulePermissionSerializer
)


from showrooms.mixins import scope_queryset_to_active_showroom, get_active_showroom_id


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer

    @action(detail=True, methods=['get'])
    def modules(self, request, pk=None):
        role = self.get_object()
        # Return list of modules this role has access to
        perms = ModulePermission.objects.filter(role=role, is_allowed=True)
        # Unique modules
        modules_seen = set()
        data = []
        for p in perms:
            if p.module not in modules_seen:
                data.append({'id': p.module, 'name': p.get_module_display()})
                modules_seen.add(p.module)
        return Response(data)


class ModuleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        data = []
        for code, label in ModulePermission.MODULE_CHOICES:
            data.append({'id': code, 'name': str(label)})
        return Response(data)

    def retrieve(self, request, pk=None):
        # Check permission for this module
        if not request.user.has_module_permission(pk, 'view'):
             return Response({'detail': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        # Determine name
        name = pk
        for code, label in ModulePermission.MODULE_CHOICES:
            if code == pk:
                name = str(label)
                break
        return Response({'id': pk, 'name': name})
from showrooms.models import ShowroomEmployee


class BaseReadWriteViewSet(viewsets.ModelViewSet):
    """قاعدة عامة لعزل المعرض عند توفره دون فرضه إجبارياً.
    يمكن ضبط STRICT_SHOWROOM_SCOPE=True في subclass لجعل عدم وجود showroom => queryset.none()."""
    STRICT_SHOWROOM_SCOPE = False

    def get_queryset(self):
        qs = super().get_queryset()
        sid = getattr(self.request, 'active_showroom_id', None)
        if not sid:
            return qs.none() if self.STRICT_SHOWROOM_SCOPE else qs
        fields = [
            'showroom', 'showroom_id',
            'showroom_link', 'showroom_link__id',
            'location__showroom', 'location__showroom_id',
            'location__showroom_link', 'location__showroom_link__id',
        ]
        return scope_queryset_to_active_showroom(self.request, qs, showroom_field_candidates=fields)


class CompanyViewSet(BaseReadWriteViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class ProductViewSet(BaseReadWriteViewSet):
    queryset = Product.objects.all().order_by('sku')
    serializer_class = ProductSerializer
    filterset_fields = ['sku', 'name']
    search_fields = ['sku', 'name']


class LocationViewSet(BaseReadWriteViewSet):
    STRICT_SHOWROOM_SCOPE = False  # Disabled for REST API - use user profile showroom instead
    queryset = Location.objects.all().order_by('code')
    serializer_class = LocationSerializer

    def get_queryset(self):
        """Return locations based on active showroom session key for REST API"""
        request = getattr(self, 'request', None)
        base = Location.objects.all().order_by('code')
        if not request or not request.user.is_authenticated:
            return base.none()
        
        # For superusers, return all locations
        if request.user.is_superuser:
            return base
        
        # Check if user is a showroom employee
        from showrooms.models import ShowroomEmployee, Showroom
        is_showroom_employee = ShowroomEmployee.objects.filter(
            user=request.user, active=True
        ).exists()
        if not is_showroom_employee:
            return base  # non-showroom users see everything

        # Use session-based active showroom (consistent with StockViewSet)
        sess = getattr(request, 'session', None)
        sid = None
        if sess:
            sid = sess.get('ACTIVE_SHOWROOM_ID') or sess.get('active_showroom_id')
        if not sid:
            return base.none()

        # Verify showroom exists and user has access
        try:
            showroom = Showroom.objects.get(id=sid)
        except Showroom.DoesNotExist:
            return base.none()

        has_access = ShowroomEmployee.objects.filter(
            showroom=showroom, user=request.user, active=True
        ).exists()
        if not has_access:
            return base.none()

        if showroom.location_id:
            return base.filter(id=showroom.location_id)
        return base.none()

    def list(self, request, *args, **kwargs):
        """Return locations based on user permissions"""
        return super().list(request, *args, **kwargs)


class StockViewSet(BaseReadWriteViewSet):
    STRICT_SHOWROOM_SCOPE = True
    # اعداد افتراضي فارغ لمنع أي تسرب قبل تطبيق منطق العزل في get_queryset
    queryset = Stock.objects.none()
    serializer_class = StockSerializer
    filterset_fields = ['product', 'location']

    def get_queryset(self):
        qs = Stock.objects.select_related('product', 'location', 'location__showroom_link').all()
        request = getattr(self, 'request', None)
        if not request or not request.user.is_authenticated:
            return qs.none()
        
        # Allow superusers to see all stock
        if request.user.is_superuser:
            return qs

        sess = getattr(request, 'session', None)
        sid = None
        if sess:
            sid = sess.get('ACTIVE_SHOWROOM_ID') or sess.get('active_showroom_id')
        if not sid:
            return qs.none()
        from showrooms.models import Showroom
        showroom_loc_id = Showroom.objects.filter(id=sid).values_list('location_id', flat=True).first()
        if not showroom_loc_id:
            return qs.none()
        scoped = qs.filter(location_id=showroom_loc_id).order_by('id')
        return scoped

    def list(self, request, *args, **kwargs):
        """Return empty list when no active showroom session key is set (explicit hard stop), 
        unless user is superuser."""
        if request.user.is_superuser:
            return super().list(request, *args, **kwargs)
            
        sess = getattr(request, 'session', None)
        sid = None
        if sess:
            sid = sess.get('ACTIVE_SHOWROOM_ID') or sess.get('active_showroom_id')
        if not sid:
            return Response([])
        return super().list(request, *args, **kwargs)


class CustomerViewSet(BaseReadWriteViewSet):
    """Deprecated: Uses partners.Customer - Use CRMCustomerViewSet instead"""
    queryset = Customer.objects.all().order_by('name')
    serializer_class = CustomerSerializer


class CRMCustomerViewSet(BaseReadWriteViewSet):
    """
    ViewSet for CRM Customer (crm.Customer) with auto customer_code generation.
    Recommended for all new integrations.
    """
    queryset = CRMCustomer.objects.all().order_by('-created_at')
    serializer_class = CRMCustomerSerializer
    filterset_fields = ['customer_code', 'first_name', 'last_name', 'phone', 'mobile', 'email', 'status']
    search_fields = ['customer_code', 'first_name', 'last_name', 'phone', 'mobile', 'company_name']


class SupplierViewSet(BaseReadWriteViewSet):
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer


class InvoiceViewSet(BaseReadWriteViewSet):
    queryset = Invoice.objects.select_related('customer').prefetch_related('items').all()
    serializer_class = EnhancedInvoiceSerializer  # Updated to use enhanced serializer
    filterset_fields = ['customer', 'date', 'number', 'is_approved']
    search_fields = ['number']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        اعتماد فاتورة وتعيين approved_by و approved_at
        Approve an invoice and set approved_by and approved_at fields
        """
        invoice = self.get_object()
        
        if invoice.is_approved:
            return Response({
                'success': False,
                'error': 'الفاتورة معتمدة بالفعل'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set approval fields
        invoice.is_approved = True
        invoice.approved_by = request.user
        invoice.approved_at = timezone.now()
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response({
            'success': True,
            'message': 'تم اعتماد الفاتورة بنجاح',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def totals(self, request):
        total = sum(inv.total for inv in self.get_queryset())
        paid = sum(inv.paid for inv in self.get_queryset())
        return Response({'total': total, 'paid': paid, 'due': total - paid})


class PurchaseBillViewSet(BaseReadWriteViewSet):
    queryset = PurchaseBill.objects.select_related('supplier').prefetch_related('items').all()
    serializer_class = PurchaseBillSerializer
    filterset_fields = ['supplier', 'date', 'number']
    search_fields = ['number']

    @action(detail=False, methods=['get'])
    def totals(self, request):
        total = sum(b.total for b in self.get_queryset())
        paid = sum(b.paid for b in self.get_queryset())
        return Response({'total': total, 'paid': paid, 'due': total - paid})


class PurchaseOrderViewSet(BaseReadWriteViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items').all()
    serializer_class = PurchaseOrderSerializer
    filterset_fields = ['supplier', 'date', 'status']
    search_fields = ['number']

    @action(detail=True, methods=['put', 'post'])
    def approve(self, request, pk=None):
        po = self.get_object()
        po.status = 'confirmed'
        po.save()
        return Response({'status': 'approved', 'message': 'Purchase order approved (confirmed)'})

    @action(detail=True, methods=['put', 'post'])
    def receive_goods(self, request, pk=None):
        po = self.get_object()
        po.status = 'completed'
        po.save()
        return Response({'status': 'goods_received', 'message': 'Goods received (completed)'})


class RevenueViewSet(BaseReadWriteViewSet):
    queryset = Revenue.objects.all().order_by('-date')
    serializer_class = RevenueSerializer


class ExpenseViewSet(BaseReadWriteViewSet):
    queryset = Expense.objects.all().order_by('-date')
    serializer_class = ExpenseSerializer


# ================================
# Branch and Notification ViewSets
# ================================
class BranchViewSet(BaseReadWriteViewSet):
    """
    ViewSet for branches management via REST API.
    Provides CRUD operations for Branch model with JWT authentication.
    """
    queryset = Branch.objects.all().order_by('name')
    serializer_class = BranchSerializer
    filterset_fields = ['name', 'code', 'is_active']
    search_fields = ['name', 'code', 'address']


class NotificationViewSet(BaseReadWriteViewSet):
    """
    ViewSet for notifications via REST API.
    Returns notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer
    filterset_fields = ['is_read', 'level']  # Fixed: 'level' instead of 'notification_type'
    search_fields = ['title', 'message']
    
    def get_queryset(self):
        """Return notifications for current user only"""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    # Explicitly require core.view_auditlog
    permission_classes = [RequireAuditViewPerm]
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['app_label', 'model_name', 'object_id', 'object_repr', 'user__username', 'ip_address']
    # Allow server-side filtering if DjangoFilterBackend is enabled in REST_FRAMEWORK
    filterset_fields = ['action', 'user', 'app_label', 'model_name', 'created_at', 'object_id']
    pagination_class = type('AuditPagination', (pagination.PageNumberPagination,), {'page_size': 50})


# ================================
# Logout API View
# ================================
class LogoutAPIView(APIView):
    """
    API endpoint for user logout that properly blacklists JWT refresh tokens.
    
    **Authentication Required:**
    - Include access token in Authorization header: `Authorization: Bearer <access_token>`
    
    **Request Body:**
    - `refresh_token`: JWT refresh token to blacklist (required)
    
    **Example:**
    ```
    POST /api/logout/
    Headers:
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
    Body:
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
    ```
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            
            if not refresh_token:
                return Response({
                    'success': False,
                    'error': 'لم يتم تقديم refresh token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'تم تسجيل الخروج بنجاح'
            }, status=status.HTTP_200_OK)
            
        except TokenError as e:
            return Response({
                'success': False,
                'error': f'Token غير صالح: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# Account Search API View
# ================================
class AccountSearchAPIView(APIView):
    """
    API endpoint for searching accounts using POST method.
    Accepts POST request with 'query' or 'q' parameter in the body.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            query = request.data.get('query') or request.data.get('q', '').strip()
            
            if not query:
                return Response({
                    'success': False,
                    'results': [],
                    'message': 'لم يتم تقديم نص للبحث'
                }, status=status.HTTP_200_OK)
            
            # Search in accounts by code or name
            accounts = Account.objects.filter(
                models.Q(code__icontains=query) |
                models.Q(name__icontains=query)
            ).values('id', 'code', 'name', 'account_type')[:20]
            
            return Response({
                'success': True,
                'results': list(accounts),
                'count': len(accounts)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'حدث خطأ أثناء البحث: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# Unified Autosave API View
# ================================
class UnifiedAutosaveAPIView(APIView):
    """
    Unified autosave endpoint that delegates to module-specific autosave logic.
    Accepts POST request with 'module' and 'data' in the body.
    Supported modules: 'accounting', 'invoice'
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            module = request.data.get('module', '').lower()
            data = request.data.get('data', {})
            
            if not module:
                return Response({
                    'success': False,
                    'error': 'لم يتم تحديد الوحدة (module)'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if module == 'accounting':
                # Delegate to accounting autosave logic
                from accounting.views import autosave_journal_entry
                return autosave_journal_entry(request)
            elif module == 'invoice':
                # Delegate to invoice autosave logic
                from sales.views import autosave_invoice
                return autosave_invoice(request)
            else:
                return Response({
                    'success': False,
                    'error': f'الوحدة {module} غير مدعومة'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# Invoice Approval API View
# ================================
class InvoiceApprovalAPIView(APIView):
    """
    API endpoint for approving invoices.
    Accepts POST request to /api/invoices/<pk>/approve/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
            
            # Check if invoice is already approved
            if invoice.is_approved:
                return Response({
                    'success': False,
                    'message': 'الفاتورة معتمدة بالفعل'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update invoice status
            invoice.is_approved = True
            invoice.approved_by = request.user
            invoice.approved_at = timezone.now()
            invoice.save()
            
            return Response({
                'success': True,
                'message': 'تم اعتماد الفاتورة بنجاح',
                'data': {
                    'id': invoice.id,
                    'number': invoice.number,
                    'is_approved': invoice.is_approved,
                    'approved_at': invoice.approved_at
                }
            }, status=status.HTTP_200_OK)
            
        except Invoice.DoesNotExist:
            return Response({
                'success': False,
                'error': 'الفاتورة غير موجودة'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

