"""
Accounting REST API Views
واجهة برمجية RESTful للمحاسبة
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Account, JournalEntry, JournalEntryItem, CostCenter
from .api_serializers import (
    AccountSerializer,
    JournalEntryListSerializer,
    JournalEntryDetailSerializer,
    JournalEntryCreateSerializer,
    CostCenterSerializer,
)


class AccountViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل لشجرة الحسابات
    GET    /accounting/api/v1/accounts/          → قائمة الحسابات
    POST   /accounting/api/v1/accounts/          → إضافة حساب
    GET    /accounting/api/v1/accounts/{id}/     → تفاصيل حساب
    PUT    /accounting/api/v1/accounts/{id}/     → تعديل حساب
    DELETE /accounting/api/v1/accounts/{id}/     → حذف حساب
    """
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'is_active', 'is_group', 'can_post', 'parent']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'level']
    ordering = ['code']

    def get_queryset(self):
        return Account.objects.select_related('parent', 'default_cost_center').all()

    def create(self, request, *args, **kwargs):
        """Override create to auto-generate code and default account_type if not provided"""
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        # Auto-generate code if not provided
        if not data.get('code'):
            import random
            max_code = Account.objects.order_by('-id').values_list('code', flat=True).first() or '9000'
            try:
                next_code = str(int(max_code) + random.randint(1, 100))
            except (ValueError, TypeError):
                next_code = str(9000 + Account.objects.count() + random.randint(1, 100))
            data['code'] = next_code
        # Default account_type to 'expense' if not provided
        if not data.get('account_type'):
            data['account_type'] = 'expense'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        """عرض شجرة الحسابات"""
        accounts = Account.objects.filter(parent__isnull=True, is_active=True).order_by('code')
        result = []
        for account in accounts:
            result.append(self._build_tree(account))
        return Response(result)

    def _build_tree(self, account):
        children = Account.objects.filter(parent=account, is_active=True).order_by('code')
        return {
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'account_type': account.account_type,
            'is_group': account.is_group,
            'children': [self._build_tree(child) for child in children],
        }


class JournalEntryViewSet(viewsets.ModelViewSet):
    """
    CRUD كامل لقيود اليومية
    GET    /accounting/api/v1/journal-entries/          → قائمة القيود
    POST   /accounting/api/v1/journal-entries/          → إنشاء قيد
    GET    /accounting/api/v1/journal-entries/{id}/     → تفاصيل قيد
    PUT    /accounting/api/v1/journal-entries/{id}/     → تعديل قيد
    POST   /accounting/api/v1/journal-entries/{id}/post/  → ترحيل قيد
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_posted', 'entry_type', 'auto_generated']
    search_fields = ['number', 'description', 'reference']
    ordering_fields = ['date', 'number', 'created_at']
    ordering = ['-date', '-id']

    def get_queryset(self):
        qs = JournalEntry.objects.select_related('created_by', 'showroom').prefetch_related('items__account')
        # فلتر التاريخ
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return JournalEntryListSerializer
        if self.action == 'create':
            return JournalEntryCreateSerializer
        return JournalEntryDetailSerializer

    def create(self, request, *args, **kwargs):
        """Override create to return detailed response with id"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        detail = JournalEntryDetailSerializer(entry)
        return Response(detail.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='post_entry')
    def post_entry(self, request, pk=None):
        """ترحيل القيد"""
        entry = self.get_object()
        if entry.is_posted:
            return Response(
                {'error': 'هذا القيد مُرحّل بالفعل'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry.is_posted = True
        entry.save(update_fields=['is_posted'])
        serializer = JournalEntryDetailSerializer(entry)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='unpost')
    def unpost_entry(self, request, pk=None):
        """إلغاء ترحيل القيد"""
        entry = self.get_object()
        if not entry.is_posted:
            return Response(
                {'error': 'هذا القيد غير مُرحّل'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entry.is_posted = False
        entry.save(update_fields=['is_posted'])
        serializer = JournalEntryDetailSerializer(entry)
        return Response(serializer.data)


class CostCenterViewSet(viewsets.ModelViewSet):
    """
    CRUD لمراكز التكلفة
    """
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'name']
    ordering = ['code']
