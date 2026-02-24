from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import original viewsets from legacy api package
from api.views import (
    ProductViewSet, LocationViewSet, StockViewSet,
    CustomerViewSet, SupplierViewSet,
    InvoiceViewSet, PurchaseBillViewSet, PurchaseOrderViewSet,
    RevenueViewSet, ExpenseViewSet, CompanyViewSet, AuditLogViewSet,
    BranchViewSet, NotificationViewSet,  # Added for REST API
    LogoutAPIView, AccountSearchAPIView, UnifiedAutosaveAPIView, InvoiceApprovalAPIView,
    UserViewSet, RoleViewSet, ModuleViewSet
)
from api.crm_views import (
    CustomerViewSet as CRMCustomerViewSet, CustomerTypeViewSet, CustomerSourceViewSet, ContactPersonViewSet,
    OpportunityViewSet, OpportunityStageViewSet, ActivityViewSet, ActivityTypeViewSet,
    QuotationViewSet, SupportTicketViewSet, TicketCategoryViewSet,
    CampaignViewSet, CRMDashboardView
)
from api.test_views import TestResourceViewSet, test_api_health
from api.reporting_endpoints import report_urlpatterns
from showrooms.urls import urlpatterns as showroom_urlpatterns

# Import autosave views
from core.api.autosave_views import (
    autosave_draft, load_draft, clear_draft,
    acquire_edit_lock, release_edit_lock
)

API_URLS_IDENT = 'api_app.urls.v1'

router = DefaultRouter()
# Core APIs
router.register(r'companies', CompanyViewSet)
router.register(r'products', ProductViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'stock', StockViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'purchases', PurchaseBillViewSet)
router.register(r'purchase_orders', PurchaseOrderViewSet)
router.register(r'revenues', RevenueViewSet)
router.register(r'expenses', ExpenseViewSet)
router.register(r'branches', BranchViewSet, basename='branches')  # New: Branch REST API
router.register(r'notifications', NotificationViewSet, basename='notifications')  # New: Notification REST API
router.register(r'audit-logs', AuditLogViewSet, basename='audit-logs')
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'modules', ModuleViewSet, basename='module')

# CRM APIs
router.register(r'crm/customers', CRMCustomerViewSet, basename='crm-customers')
router.register(r'crm/customer-types', CustomerTypeViewSet, basename='crm-customer-types')
router.register(r'crm/customer-sources', CustomerSourceViewSet, basename='crm-customer-sources')
router.register(r'crm/contacts', ContactPersonViewSet, basename='crm-contacts')
router.register(r'crm/opportunities', OpportunityViewSet, basename='crm-opportunities')
router.register(r'crm/opportunity-stages', OpportunityStageViewSet, basename='crm-opportunity-stages')
router.register(r'crm/activities', ActivityViewSet, basename='crm-activities')
router.register(r'crm/activity-types', ActivityTypeViewSet, basename='crm-activity-types')
router.register(r'crm/quotations', QuotationViewSet, basename='crm-quotations')
router.register(r'crm/tickets', SupportTicketViewSet, basename='crm-tickets')
router.register(r'crm/ticket-categories', TicketCategoryViewSet, basename='crm-ticket-categories')
router.register(r'crm/campaigns', CampaignViewSet, basename='crm-campaigns')
router.register(r'crm/dashboard', CRMDashboardView, basename='crm-dashboard')

# Test endpoints for automated testing
router.register(r'resource', TestResourceViewSet, basename='test-resource')

from api.production_views import (
    ProductionOrderViewSet, RawMaterialIssueViewSet, 
    ProductionProcessViewSet, QualityInspectionViewSet, CostCalculationViewSet,
    BOMViewSet
)
from api.inventory_views import InventoryAdditionViewSet
from api.views_exports import DataExportViewSet

# Production URLs
router.register(r'production/boms', BOMViewSet, basename='production-bom')
router.register(r'production/orders', ProductionOrderViewSet)
router.register(r'production/raw-material-issues', RawMaterialIssueViewSet, basename='production-raw-material')
router.register(r'production/processes', ProductionProcessViewSet, basename='production-process')
router.register(r'production/quality-inspections', QualityInspectionViewSet, basename='production-quality')
router.register(r'production/cost-calculations', CostCalculationViewSet, basename='production-cost')
router.register(r'inventory/additions', InventoryAdditionViewSet, basename='inventory-addition')
router.register(r'exports', DataExportViewSet, basename='data-exports')

urlpatterns = [
    path('', include(router.urls)),
    # Health check
    path('health/', test_api_health, name='api-health'),
    # Authentication endpoints
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
    # Accounting endpoints
    path('accounts/search/', AccountSearchAPIView.as_view(), name='api-account-search'),
    # Autosave endpoint (legacy)
    path('autosave/', UnifiedAutosaveAPIView.as_view(), name='api-autosave'),
    # New Autosave endpoints
    path('autosave/draft/', autosave_draft, name='api-autosave-draft'),
    path('autosave/draft/load/', load_draft, name='api-load-draft'),
    path('autosave/draft/clear/', clear_draft, name='api-clear-draft'),
    path('autosave/lock/', acquire_edit_lock, name='api-acquire-lock'),
    path('autosave/lock/release/', release_edit_lock, name='api-release-lock'),
    # Invoice endpoints
    path('invoices/<int:pk>/approve/', InvoiceApprovalAPIView.as_view(), name='api-invoice-approve'),
    # Enterprise APIs (MRP, Costing, Distribution, Dashboard, Integration)
    path('enterprise/', include('api.urls_enterprise', namespace='enterprise')),
] + report_urlpatterns + showroom_urlpatterns
