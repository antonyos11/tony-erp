# Tony ERP — Comprehensive REST API Summary

> Generated: 2026-02-13 | Project: `/var/www/tony_erp`

---

## 1. Tech Stack

| Component | Version / Detail |
|---|---|
| **Python** | 3.12.3 |
| **Django** | 5.2.9 (requirements pin 5.2.5, runtime 5.2.9) |
| **Django REST Framework** | 3.16.1 |
| **Database** | SQLite3 (dev default), PostgreSQL / MySQL supported via env vars (`DB_ENGINE`, `DATABASE_URL`) |
| **Auth – primary** | JWT via `djangorestframework-simplejwt` 5.5.1 (token blacklisting enabled) |
| **Auth – secondary** | BasicAuthentication (kept for backward compat) |
| **Default permission** | `IsAuthenticated` |
| **Filtering** | `django-filter` 25.1, DRF `SearchFilter` + `OrderingFilter` |
| **Pagination** | `PageNumberPagination`, page_size=20 |
| **Throttling** | Anon 200/hr, User 2000/hr, Reports 120/hr |
| **API docs** | `drf-spectacular` 0.28.0 → OpenAPI 3 schema at `/api/schema/`, Swagger at `/api/docs/`, ReDoc at `/api/redoc/` |
| **CORS** | `django-cors-headers` 4.7.0 |
| **Task queue** | Celery 5.5.3 + Redis 6.4.0 |
| **Static files** | WhiteNoise 6.9.0 |
| **2FA / OTP** | `django-otp` 1.6.1 (TOTP + static) |
| **Security** | CSP (`django-csp`), custom rate-limit middleware, security headers middleware |
| **ASGI (optional)** | Django Channels (if installed) |
| **Project name** | `accountant_pro` |

---

## 2. Authentication Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | Refresh an access token |
| POST | `/api/token/verify/` | Verify a token |
| POST | `/api/logout/` | Logout (via `api_app`) |

---

## 3. API Feature Groups

### 3.1 Central API (`api_app`) — prefix `/api/`

All DRF ViewSet endpoints use the DefaultRouter (list, create, retrieve, update, partial_update, destroy).

**Files:** `api_app/urls.py`, `api/views.py`, `api/crm_views.py`, `api/production_views.py`, `api/inventory_views.py`, `api/reporting_endpoints.py`, `api/urls_enterprise.py`, `api/test_views.py`

#### Core Resources (CRUD via Router)

| Resource | Router prefix | Basename |
|---|---|---|
| Companies | `api/companies/` | — |
| Products | `api/products/` | — |
| Locations | `api/locations/` | — |
| Stock | `api/stock/` | — |
| Customers | `api/customers/` | — |
| Suppliers | `api/suppliers/` | — |
| Invoices | `api/invoices/` | — |
| Purchase Bills | `api/purchases/` | — |
| Purchase Orders | `api/purchase_orders/` | — |
| Revenues | `api/revenues/` | — |
| Expenses | `api/expenses/` | — |
| Branches | `api/branches/` | branches |
| Notifications | `api/notifications/` | notifications |
| Audit Logs | `api/audit-logs/` | audit-logs |
| Users | `api/users/` | user |
| Roles | `api/roles/` | role |
| Modules | `api/modules/` | module |
| Test Resource | `api/resource/` | test-resource |

#### CRM Resources (CRUD via Router)

| Resource | Router prefix |
|---|---|
| CRM Customers | `api/crm/customers/` |
| Customer Types | `api/crm/customer-types/` |
| Customer Sources | `api/crm/customer-sources/` |
| Contacts | `api/crm/contacts/` |
| Opportunities | `api/crm/opportunities/` |
| Opportunity Stages | `api/crm/opportunity-stages/` |
| Activities | `api/crm/activities/` |
| Activity Types | `api/crm/activity-types/` |
| Quotations | `api/crm/quotations/` |
| Support Tickets | `api/crm/tickets/` |
| Ticket Categories | `api/crm/ticket-categories/` |
| Campaigns | `api/crm/campaigns/` |
| CRM Dashboard | `api/crm/dashboard/` |

#### Production Resources (CRUD via Router)

| Resource | Router prefix |
|---|---|
| BOMs | `api/production/boms/` |
| Production Orders | `api/production/orders/` |
| Raw Material Issues | `api/production/raw-material-issues/` |
| Production Processes | `api/production/processes/` |
| Quality Inspections | `api/production/quality-inspections/` |
| Cost Calculations | `api/production/cost-calculations/` |
| Inventory Additions | `api/inventory/additions/` |

#### Additional Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health/` | API health check |
| POST | `/api/logout/` | JWT logout |
| GET | `/api/accounts/search/` | Account search |
| POST | `/api/autosave/` | Unified autosave (legacy) |
| POST | `/api/autosave/draft/` | Save draft |
| GET | `/api/autosave/draft/load/` | Load draft |
| DELETE | `/api/autosave/draft/clear/` | Clear draft |
| POST | `/api/autosave/lock/` | Acquire edit lock |
| POST | `/api/autosave/lock/release/` | Release edit lock |
| POST | `/api/invoices/{id}/approve/` | Invoice approval |

#### Reporting API (under `/api/reports/`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/reports/overview/` | Reports overview |
| GET | `/api/reports/full/` | Full system report |
| GET | `/api/reports/sales/` | Sales report |
| GET | `/api/reports/inventory/` | Inventory report |
| GET | `/api/reports/purchases/` | Purchases report |
| GET | `/api/reports/profit-loss/` | Profit & loss |
| GET | `/api/reports/ar-aging/` | AR aging |
| GET | `/api/reports/ap-aging/` | AP aging |
| GET | `/api/reports/balance-sheet/` | Balance sheet |
| GET | `/api/reports/cash-flow/` | Cash flow |
| GET | `/api/reports/crm-pipeline/` | CRM pipeline |
| GET | `/api/reports/inventory-turnover/` | Inventory turnover |
| GET | `/api/reports/stock-aging/` | Stock aging |
| GET | `/api/reports/snapshots/` | Snapshot series |
| GET | `/api/reports/health/` | Reports health check |
| GET | `/api/reports/variance-incidents/` | Variance incidents |

#### Enterprise API (`/api/enterprise/`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/enterprise/mrp/requirements/` | MRP material requirements |
| GET | `/api/enterprise/mrp/schedule/` | Production schedule |
| GET | `/api/enterprise/mrp/purchase-suggestions/` | Purchase suggestions |
| GET | `/api/enterprise/mrp/alerts/` | MRP alerts |
| GET | `/api/enterprise/mrp/capacity/` | Capacity planning |
| GET | `/api/enterprise/costing/standard/` | Standard costs |
| GET | `/api/enterprise/costing/actual/` | Actual costs |
| GET | `/api/enterprise/costing/variances/` | Cost variances |
| GET | `/api/enterprise/costing/margin/` | Product margins |
| GET | `/api/enterprise/costing/analysis/` | Costing analysis |
| GET | `/api/enterprise/distribution/stock-levels/` | Distribution stock |
| GET | `/api/enterprise/distribution/replenishment/` | Replenishment suggestions |
| POST | `/api/enterprise/distribution/create-replenishment/` | Create replenishment |
| GET | `/api/enterprise/distribution/dashboard/` | Distribution dashboard |
| GET | `/api/enterprise/dashboard/unified/` | Unified dashboard |
| GET | `/api/enterprise/integration/demands/` | Integration demands |

---

### 3.2 System API — prefix `/api/system/` and `/dashboard/api/`

**Files:** `core/system_api.py`, `core/urls.py`, `core/api_search.py`, `core/code_generator_api.py`, `core/help_api.py`

| Method | Path | Description |
|---|---|---|
| POST | `/api/system/backup/` | Create system backup |
| GET | `/api/system/download-backup/{filename}/` | Download backup file |
| POST | `/api/system/clear-cache/` | Clear system cache |
| POST | `/dashboard/api/system/maintenance/` | Maintenance action |
| GET | `/dashboard/api/notifications/recent/` | Recent notifications |
| GET | `/dashboard/api/dashboard/daily-profit/` | Daily profit summary |
| GET | `/dashboard/api/dashboard/hr-attendance/` | HR attendance data |
| GET | `/dashboard/api/dashboard/periodic-updates/` | Periodic updates status |
| POST | `/dashboard/api/dashboard/run-updates/` | Run periodic updates |
| GET | `/dashboard/api/reports/profit-by-category/` | Profit by category |
| GET | `/dashboard/api/global-search/` | Global search |
| POST | `/dashboard/api/generate-code/` | Auto-generate code |
| GET | `/dashboard/api/generate-code/models/` | Available models for code gen |
| GET | `/dashboard/api/help/` | Contextual help |
| GET | `/dashboard/api/keyboard-shortcuts/` | Keyboard shortcuts |
| GET | `/dashboard/api/help/search/` | Help search |

---

### 3.3 Dashboard API — prefix `/dashboard-api/`

**Files:** `dashboard/urls.py`, `dashboard/api_views.py`

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard-api/api/data/` | Full dashboard data |
| GET | `/dashboard-api/api/kpis/` | KPI metrics |
| GET | `/dashboard-api/api/kpis/comparison/` | KPI comparison |
| GET | `/dashboard-api/api/charts/sales/` | Sales chart data |
| GET | `/dashboard-api/api/charts/inventory/` | Inventory chart data |
| POST | `/dashboard-api/api/cache/clear/` | Clear dashboard cache |

---

### 3.4 Inventory — prefix `/inventory/`

**Files:** `inventory/urls.py`, `inventory/api_views.py`, `inventory/views.py`, `inventory/views_reports.py`, `inventory/views_conversions.py`

#### DRF Router (`/inventory/api/v1/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Products | `inventory/api/v1/products/` | api-products |
| Categories | `inventory/api/v1/categories/` | api-categories |
| Locations | `inventory/api/v1/locations/` | api-locations |
| Stock | `inventory/api/v1/stock/` | api-stock |

#### Inline JSON API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/inventory/api/supplier/{id}/products/` | Supplier's products |
| GET | `/inventory/api/supplier/{id}/materials/` | Supplier's raw materials |
| GET | `/inventory/api/supplier/{id}/price-info/` | Supplier price info |
| POST | `/inventory/api/categories/create/` | Create category (JSON) |
| GET | `/inventory/api/barcode/lookup/` | Barcode lookup |
| GET | `/inventory/api/notifications/` | Inventory notifications |
| GET | `/inventory/api/stock/{product_id}/` | Real-time stock update |
| GET | `/inventory/api/price-change-preview/` | Price change preview |
| POST | `/inventory/api/recalculate-costs/` | Recalculate all costs |
| GET | `/inventory/api/material/{id}/price-history/` | Material price history |
| GET | `/inventory/api/notifications/unread-count/` | Unread notifications count |
| GET | `/inventory/api/conversion/get-factor/` | Get conversion factor |
| POST | `/inventory/api/conversion/convert/` | Convert value |
| GET | `/inventory/api/conversion/available/` | Available conversions |
| GET | `/inventory/analytics/api/reorder-point/{product_id}/` | Reorder point AJAX |

---

### 3.5 Accounting — prefix `/accounting/`

**Files:** `accounting/urls.py`, `accounting/api_views.py`, `accounting/entry_api.py`, `accounting/views.py`

#### DRF Router (`/accounting/api/v1/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Accounts | `accounting/api/v1/accounts/` | api-accounts |
| Journal Entries | `accounting/api/v1/journal-entries/` | api-journal-entries |
| Cost Centers | `accounting/api/v1/cost-centers/` | api-cost-centers |

#### Inline JSON API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/accounting/api/autosave/` | Autosave entry |
| GET | `/accounting/api/invoice/{number}/` | Get invoice data |
| GET | `/accounting/api/supplier/{id}/credit/` | Check supplier credit |
| GET | `/accounting/api/entry-history/` | Entry history |
| GET | `/accounting/api/accounts/search-advanced/` | Advanced account search |
| GET | `/accounting/api/entry-templates/` | Get entry templates |
| POST | `/accounting/api/entry-templates/save/` | Save entry template |
| GET | `/accounting/api/tax-settings/` | Tax settings |
| GET | `/accounting/api/badges/` | Badges data |
| GET | `/accounting/api/accounts/search/` | Account search |
| POST | `/accounting/api/journal-entry/validate/` | Validate journal entry |
| POST | `/accounting/api/journal-entry/draft/save/` | Save journal entry draft |
| GET | `/accounting/api/templates/` | Journal templates |

---

### 3.6 Sales — prefix `/sales/`

**Files:** `sales/urls.py`, `sales/api_views.py`, `sales/invoice_api_views.py`

#### DRF Router (`/sales/api/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Invoices | `sales/api/invoices/` | api-invoices |
| Invoice Payments | `sales/api/payments/` | api-invoice-payments |
| Customer Statements | `sales/api/statements/` | api-customer-statements |

#### Inline JSON API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/sales/api/invoices/create/` | Create invoice |
| POST | `/sales/api/autosave/` | Autosave invoice |
| GET | `/sales/api/autosave/load/` | Load autosaved invoice |
| GET | `/sales/api/templates/` | List templates |
| POST | `/sales/api/templates/create/` | Create template |
| POST | `/sales/api/templates/{id}/increment/` | Increment template usage |
| GET | `/sales/api/customers/search/` | Smart customer search |
| GET | `/sales/api/customers/{id}/last-transactions/` | Customer last transactions |
| GET | `/sales/api/customers/{id}/credit-check/` | Credit limit check |
| GET | `/sales/api/invoice/{number}/details/` | Invoice details |
| POST | `/sales/api/attachments/upload/` | Upload attachment |
| GET | `/sales/api/invoice/{id}/history/` | Invoice history |
| GET | `/sales/api/customers/search/` | Customer search (quick) |
| POST | `/sales/api/customers/quick-create/` | Quick-create customer |
| GET | `/sales/api/customers/{id}/` | Customer details |
| GET | `/sales/api/next-numbers/` | Next invoice numbers |

---

### 3.7 Purchases — prefix `/purchases/`

**Files:** `purchases/urls.py`, `purchases/api_views.py`

#### DRF Router (`/purchases/api/v1/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Suppliers | `purchases/api/v1/suppliers/` | api-suppliers |
| Purchase Orders | `purchases/api/v1/orders/` | api-orders |
| Purchase Bills | `purchases/api/v1/bills/` | api-bills |

---

### 3.8 HR — prefix `/hr/`

**Files:** `hr/urls.py`, `hr/api_views.py`

#### DRF Router (`/hr/api/v1/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Employees | `hr/api/v1/employees/` | api-employees |
| Departments | `hr/api/v1/departments/` | api-departments |
| Job Positions | `hr/api/v1/positions/` | api-positions |

#### Inline API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/hr/api/positions/` | Positions by department (AJAX) |
| GET | `/hr/loans/api/employee/{id}/` | Employee loan info |

---

### 3.9 Branches — prefix `/branches/`

**Files:** `branches/urls.py`, `branches/views.py`

| Method | Path | Description |
|---|---|---|
| GET | `/branches/api/list/` | List all branches (JSON) |
| GET | `/branches/api/{id}/stock/` | Branch stock levels |
| GET | `/branches/api/{id}/staff/` | Branch staff |
| GET | `/branches/api/staff/` | Staff filtered by branch |

---

### 3.10 E-Commerce — prefix `/store/` (public) + `/api/ecommerce/` (REST API)

**Files:** `ecommerce/urls.py`, `ecommerce/api_urls.py`, `ecommerce/api_views.py`, `ecommerce/api_views_optimized.py`, `ecommerce/views_push.py`

#### DRF Router (`/api/ecommerce/`)

| Resource | Router prefix | Basename |
|---|---|---|
| Products | `api/ecommerce/products/` | product |
| Categories | `api/ecommerce/categories/` | category |
| Brands | `api/ecommerce/brands/` | brand |
| Cart | `api/ecommerce/cart/` | cart |
| Orders | `api/ecommerce/orders/` | order |
| Wishlist | `api/ecommerce/wishlist/` | wishlist |
| Reviews | `api/ecommerce/reviews/` | review |
| Coupons | `api/ecommerce/coupons/` | coupon |

#### Optimized v2 endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/ecommerce/v2/products/` | Products (cached) |
| GET | `/api/ecommerce/v2/products/search/` | Product search |
| GET | `/api/ecommerce/v2/products/{id}/` | Product detail (cached) |
| GET | `/api/ecommerce/v2/categories/` | Categories (cached) |
| GET | `/api/ecommerce/v2/brands/` | Brands (cached) |
| GET | `/api/ecommerce/v2/homepage/` | Homepage data |
| GET | `/api/ecommerce/v2/cart/` | Cart (cached) |
| GET | `/api/ecommerce/v2/wishlist/` | Wishlist (cached) |

#### Auth (store-scoped JWT)

| Method | Path | Description |
|---|---|---|
| POST | `/api/ecommerce/auth/token/` | Store JWT obtain |
| POST | `/api/ecommerce/auth/token/refresh/` | Store JWT refresh |
| POST | `/api/ecommerce/auth/token/verify/` | Store JWT verify |

#### Push Notifications

| Method | Path | Description |
|---|---|---|
| POST | `/api/ecommerce/push/subscribe/` | Subscribe to push |
| POST | `/api/ecommerce/push/unsubscribe/` | Unsubscribe |
| GET | `/api/ecommerce/push/vapid-key/` | VAPID public key |
| GET | `/api/ecommerce/push/preferences/` | Notification preferences |
| POST | `/api/ecommerce/push/preferences/update/` | Update preferences |
| POST | `/api/ecommerce/push/test/` | Test notification |

---

### 3.11 POS (Point of Sale) — prefix `/pos/`

**Files:** `pos/urls.py`, `pos/api_views.py`, `pos/views.py`, `pos/views_enhanced.py`

| Method | Path | Description |
|---|---|---|
| POST | `/pos/api/orders/create/` | Create POS order |
| GET | `/pos/api/orders/` | List POS orders |
| GET | `/pos/api/product-lookup/` | Product lookup (barcode/name) |
| POST | `/pos/api/hold-order/` | Hold order |
| GET | `/pos/api/held-orders/` | List held orders |
| GET | `/pos/api/held-order/{id}/` | Get held order |
| POST | `/pos/api/held-order/{id}/restore/` | Restore held order |
| DELETE | `/pos/api/held-order/{id}/delete/` | Delete held order |
| POST | `/pos/api/toggle-favorite/` | Toggle favorite product |
| GET | `/pos/api/favorites/` | List favorites |
| GET | `/pos/api/top-selling/` | Top selling products |
| GET | `/pos/api/recent-products/` | Recent products |
| GET | `/pos/api/quick-amounts/` | Quick payment amounts |
| GET | `/pos/api/keyboard-shortcuts/` | POS keyboard shortcuts |
| POST | `/pos/api/complete-order/` | Complete order & pay |
| POST | `/pos/api/create-installment/` | Create installment order |
| GET | `/pos/api/print-thermal/{order_id}/` | Print thermal receipt |
| GET | `/pos/api/printers/` | List printers |
| POST | `/pos/api/printer/test/` | Test printer |
| POST | `/pos/api/printer/print-barcode/` | Print barcode |
| GET | `/pos/api/printer/status/` | Printer status |
| POST | `/pos/api/installment/calculate/` | Calculate installment |
| GET | `/pos/api/installment/plans/` | Installment plans |
| GET | `/pos/api/customer-installments/` | Customer installments |
| POST | `/pos/api/pay-installment/` | Pay customer installment |

---

### 3.12 Fleet Management — prefix `/api/fleet/`

**Files:** `fleet/api_urls.py`, `fleet/api_views.py`

DRF Router (full CRUD):

| Resource | Router prefix |
|---|---|
| Vehicles | `api/fleet/vehicles/` |
| Drivers | `api/fleet/drivers/` |
| Trips | `api/fleet/trips/` |
| Vehicle Expenses | `api/fleet/expenses/` |
| Vehicle Documents | `api/fleet/documents/` |
| Driver Violations | `api/fleet/violations/` |
| Driver Advances | `api/fleet/advances/` |
| Driver Locations | `api/fleet/locations/` |

---

### 3.13 Shipping — prefix `/api/shipping/`

**Files:** `shipping/api_urls.py`, `shipping/api.py`

DRF Router (full CRUD):

| Resource | Router prefix |
|---|---|
| Shipping Companies | `api/shipping/companies/` |
| Shipping Zones | `api/shipping/zones/` |
| Shipping Rates | `api/shipping/rates/` |
| Shipments | `api/shipping/shipments/` |

---

### 3.14 Quality Control — prefix `/api/quality-control/`

**Files:** `quality_control/api_urls.py`, `quality_control/api.py`

DRF Router (full CRUD):

| Resource | Router prefix |
|---|---|
| Quality Standards | `api/quality-control/standards/` |
| Inspection Types | `api/quality-control/inspection-types/` |
| Quality Inspections | `api/quality-control/inspections/` |
| Quality Issues | `api/quality-control/issues/` |

---

### 3.15 Showrooms — prefix `/api/` (via `api_app`)

**Files:** `showrooms/urls.py`, `showrooms/views.py`

DRF Router (full CRUD):

| Resource | Router prefix |
|---|---|
| Showrooms | `api/showrooms/` |
| Showroom Employees | `api/showroom-employees/` |
| Showroom Expenses | `api/showroom-expenses/` |
| Showroom Purchases | `api/showroom-purchases/` |
| Stock Movements | `api/showroom-movements/` |
| Payroll Entries | `api/showroom-payroll/` |
| Shifts | `api/showroom-shifts/` |
| Shift Assignments | `api/showroom-shift-assignments/` |
| Temporary Workers | `api/temporary-workers/` |
| Rent Payments | `api/rent-payments/` |

#### Additional API views

| Method | Path | Description |
|---|---|---|
| GET | `/api/showrooms/pnl/` | Showroom P&L |
| GET | `/api/showrooms/kpis/` | Showroom KPIs |
| GET | `/api/showrooms/active/` | Active showroom |
| POST | `/api/showrooms/transfer/` | Showroom transfer |
| GET | `/api/showrooms/summary/` | Showroom summary |
| GET | `/api/showrooms/compare/` | Showroom comparison |

---

### 3.16 Production — prefix `/production/`

**Files:** `production/urls.py`, `production/views_lifecycle.py`

| Method | Path | Description |
|---|---|---|
| GET | `/production/api/orders/{id}/status/` | Production order status |
| GET | `/production/api/orders/{id}/materials/` | Check materials availability |
| GET | `/production/api/orders/{id}/variance/` | Cost variance |
| GET | `/production/api/products/{id}/boms/` | Product BOMs (AJAX) |
| GET | `/production/api/products/{id}/uom/` | Product UoM (AJAX) |
| POST | `/production/units/verify/` | Unit verify (barcode) |

---

### 3.17 WhatsApp AI — prefix `/api/whatsapp-ai/`

**Files:** `whatsapp_ai/urls.py`, `whatsapp_ai/views.py`

DRF Router:

| Resource | Router prefix |
|---|---|
| Conversations | `api/whatsapp-ai/api/conversations/` |
| Product Knowledge | `api/whatsapp-ai/api/products-knowledge/` |
| Social Conversations | `api/whatsapp-ai/api/social-conversations/` |

| Method | Path | Description |
|---|---|---|
| POST | `/api/whatsapp-ai/webhook/{platform}/` | Unified webhook (whatsapp/facebook/instagram) |
| POST | `/api/whatsapp-ai/callback/social/` | Social callback from n8n |
| GET | `/api/whatsapp-ai/ai/context/` | AI context |
| GET | `/api/whatsapp-ai/ai/context/{platform}/` | Platform-specific AI context |
| POST | `/api/whatsapp-ai/sync/products/` | Sync products to AI |

---

### 3.18 Users — prefix `/users/`

**Files:** `users/urls.py`, `users/views.py`

| Method | Path | Description |
|---|---|---|
| GET | `/users/api/permissions/{user_id}/` | User permissions |
| GET | `/users/api/details/{user_id}/` | User details (JSON) |

---

### 3.19 Reports Builder — prefix `/reports/`

**Files:** `reports/urls.py`, `reports/views_builder.py`

| Method | Path | Description |
|---|---|---|
| GET | `/reports/api/model-fields/` | Available model fields |
| POST | `/reports/api/validate-config/` | Validate report config |
| POST | `/reports/api/duplicate/{template_id}/` | Duplicate report template |

---

### 3.20 Health & Diagnostics

| Method | Path | Description |
|---|---|---|
| GET | `/health/live/` | Liveness probe (no auth) |
| GET | `/health/ready/` | Readiness probe (no auth) |
| GET | `/dashboard/health/live/` | Liveness (core app) |
| GET | `/dashboard/health/ready/` | Readiness (core app) |
| GET | `/dashboard/status/` | Full system status |
| GET | `/diagnostic/` | Diagnostic page |

---

## 4. Installed Apps Count

**Total INSTALLED_APPS:** ~90+ Django apps including:
- **Core business:** `core`, `inventory`, `sales`, `purchases`, `accounting`, `hr`, `crm`, `production`
- **Commerce:** `ecommerce`, `pos`, `showrooms`, `woocommerce_integration`
- **Finance:** `payments`, `installments`, `fixed_assets`, `budgeting`, `bank_reconciliation`, `bank_integration`, `treasury_management`
- **Operations:** `fleet`, `shipping`, `quality_control`, `maintenance`, `contracting`, `projects`, `warehouse` (via branches)
- **HR Extended:** `attendance`, `branches`
- **AI/Comms:** `ai_assistant`, `ai_analytics`, `whatsapp_integration`, `whatsapp_ai`, `voice_assistant`
- **Advanced:** `smart_pricing`, `subscriptions`, `zatca_integration`, `risk_management`, `contract_management`, `compliance_management`, `business_intelligence`

---

## 5. Summary Statistics

| Metric | Count |
|---|---|
| DRF Router-registered ViewSets | ~55 |
| Standalone API endpoints (JSON) | ~120+ |
| Total REST API endpoints (estimated) | ~400+ (including Router CRUD actions) |
| Apps with dedicated `api_views.py` | inventory, accounting, sales, purchases, hr, fleet, shipping, quality_control, ecommerce, pos, showrooms, dashboard, whatsapp_ai |
| OpenAPI schema | Auto-generated at `/api/schema/` |
