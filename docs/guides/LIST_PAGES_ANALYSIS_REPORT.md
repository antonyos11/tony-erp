# تقرير تحليل صفحات القوائم (List Pages)
## تاريخ التقرير: 2 يناير 2026

---

## ملخص تنفيذي

| البند | العدد |
|-------|-------|
| إجمالي ملفات `*_list.html` | **152** |
| إجمالي ملفات `list.html` | **45** |
| **المجموع الكلي** | **197** |

### تصنيف حسب القالب الأساسي:
| القالب | العدد |
|--------|-------|
| `base_v2.html` | 97 |
| `BASE_TEMPLATE` | 70 |
| `base.html` | 26 |
| `_list_professional.html` | 8 |

### تصنيف حسب نوع التصميم:
| نوع التصميم | العدد |
|-------------|-------|
| تصميم بسيط (بدون hero/ds-card) | ~180 |
| تصميم hero-section | 14 |
| تصميم ds-card | 2 |

### التجاوب (Responsiveness):
| الحالة | العدد |
|--------|-------|
| متجاوب (table-responsive) | ~139 |
| **غير متجاوب** | **~58** |

---

## 📋 قائمة مفصلة حسب التطبيق

---

## 1️⃣ تطبيق Partners (الشركاء)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| suppliers_list.html | `/var/www/tony_erp/templates/partners/suppliers_list.html` | ✅ **hero-section** | ✅ نعم |
| partners_list.html | `/var/www/tony_erp/templates/partners/partners_list.html` | ✅ **ds-card** | ✅ نعم |

---

## 2️⃣ تطبيق Sales (المبيعات)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| invoice_list.html | `/var/www/tony_erp/templates/sales/invoice_list.html` | 📦 _list_professional | ❌ **لا** |
| customer_discount_list.html | `/var/www/tony_erp/templates/sales/discount/customer_discount_list.html` | 📦 _list_professional | ❌ **لا** |

---

## 3️⃣ تطبيق Purchases (المشتريات)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| purchase_list.html | `/var/www/tony_erp/templates/purchases/purchase_list.html` | بسيط + card-header | ✅ نعم |
| po_list.html | `/var/www/tony_erp/templates/purchases/po_list.html` | 📦 _list_professional | ❌ **لا** |
| pr_list.html | `/var/www/tony_erp/templates/purchases/pr/pr_list.html` | 📦 _list_professional | ❌ **لا** |
| warehouse_list.html | `/var/www/tony_erp/templates/purchases/pr/warehouse_list.html` | بسيط | ✅ نعم |
| supplier_discount_list.html | `/var/www/tony_erp/templates/purchases/discount/supplier_discount_list.html` | بسيط | ✅ نعم |
| list.html (pr) | `/var/www/tony_erp/templates/purchases/pr/list.html` | بسيط + card-header | ✅ نعم |
| list.html (quotation) | `/var/www/tony_erp/templates/purchases/quotation/list.html` | 📦 _list_professional | ❌ **لا** |
| list.html (shipment) | `/var/www/tony_erp/templates/purchases/shipment/list.html` | 📦 _list_professional | ❌ **لا** |
| list.html (receipt) | `/var/www/tony_erp/templates/purchases/receipt/list.html` | 📦 _list_professional | ❌ **لا** |
| list.html (rfq) | `/var/www/tony_erp/templates/purchases/rfq/list.html` | 📦 _list_professional | ❌ **لا** |
| list.html (price_history) | `/var/www/tony_erp/templates/purchases/price_history/list.html` | بسيط | ✅ نعم |

---

## 4️⃣ تطبيق Inventory (المخزون)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| product_list.html | `/var/www/tony_erp/templates/inventory/product_list.html` | بسيط | ✅ نعم |
| category_list.html | `/var/www/tony_erp/templates/inventory/category_list.html` | بسيط + card-header | ✅ نعم |
| location_list.html | `/var/www/tony_erp/templates/inventory/location_list.html` | بسيط | ✅ نعم |
| transfer_list.html | `/var/www/tony_erp/templates/inventory/transfer_list.html` | بسيط | ✅ نعم |
| bom_list.html | `/var/www/tony_erp/templates/inventory/bom_list.html` | بسيط | ✅ نعم |
| receiving_list.html | `/var/www/tony_erp/templates/inventory/receiving_list.html` | بسيط | ❌ **لا** |
| count_list.html | `/var/www/tony_erp/templates/inventory/count_list.html` | بسيط | ❌ **لا** |
| requisition_list.html | `/var/www/tony_erp/templates/inventory/requisition_list.html` | بسيط | ❌ **لا** |
| issue_list.html | `/var/www/tony_erp/templates/inventory/issue_list.html` | بسيط | ❌ **لا** |
| catalog_list.html | `/var/www/tony_erp/templates/inventory/catalog/catalog_list.html` | بسيط | ❌ **لا** |

---

## 5️⃣ تطبيق HR (الموارد البشرية)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| employee_list.html | `/var/www/tony_erp/templates/hr/employee_list.html` | بسيط | ✅ نعم |
| payroll_list.html | `/var/www/tony_erp/templates/hr/payroll_list.html` | بسيط | ✅ نعم |
| leave_request_list.html | `/var/www/tony_erp/templates/hr/leave_request_list.html` | بسيط | ✅ نعم |
| position_list.html | `/var/www/tony_erp/templates/hr/position_list.html` | بسيط + card-header | ✅ نعم |
| department_list.html | `/var/www/tony_erp/templates/hr/department_list.html` | بسيط | ❌ **لا** |
| complaint_list.html | `/var/www/tony_erp/templates/hr/complaint_list.html` | بسيط | ✅ نعم |
| disciplinary_list.html | `/var/www/tony_erp/templates/hr/disciplinary_list.html` | بسيط | ✅ نعم |
| training_program_list.html | `/var/www/tony_erp/templates/hr/training_program_list.html` | بسيط | ✅ نعم |
| performance_review_list.html | `/var/www/tony_erp/templates/hr/performance_review_list.html` | بسيط | ✅ نعم |
| allowance_type_list.html | `/var/www/tony_erp/templates/hr/allowance_type_list.html` | بسيط | ✅ نعم |
| deduction_type_list.html | `/var/www/tony_erp/templates/hr/deduction_type_list.html` | بسيط | ✅ نعم |
| employee_allowance_list.html | `/var/www/tony_erp/templates/hr/employee_allowance_list.html` | بسيط | ✅ نعم |
| employee_deduction_list.html | `/var/www/tony_erp/templates/hr/employee_deduction_list.html` | بسيط | ✅ نعم |
| targets_list.html | `/var/www/tony_erp/templates/hr/targets_list.html` | بسيط | ✅ نعم |
| team_targets_list.html | `/var/www/tony_erp/templates/hr/team_targets_list.html` | بسيط | ✅ نعم |
| employee_id_cards_list.html | `/var/www/tony_erp/templates/hr/employee_id_cards_list.html` | بسيط | ✅ نعم |
| id_card_batch_list.html | `/var/www/tony_erp/templates/hr/id_card_batch_list.html` | بسيط | ✅ نعم |
| id_card_template_list.html | `/var/www/tony_erp/templates/hr/id_card_template_list.html` | بسيط | ❌ **لا** |
| hse_training_list.html | `/var/www/tony_erp/templates/hr/hse_training_list.html` | بسيط | ✅ نعم |
| hse_inspection_list.html | `/var/www/tony_erp/templates/hr/hse_inspection_list.html` | بسيط | ✅ نعم |
| hse_incident_list.html | `/var/www/tony_erp/templates/hr/hse_incident_list.html` | بسيط | ✅ نعم |
| job_vacancy_list.html | `/var/www/tony_erp/templates/hr/job_vacancy_list.html` | بسيط | ❌ **لا** |
| job_application_list.html | `/var/www/tony_erp/templates/hr/job_application_list.html` | بسيط | ❌ **لا** |

---

## 6️⃣ تطبيق Accounting (المحاسبة)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| journal_entries_list.html | `/var/www/tony_erp/templates/accounting/journal_entries_list.html` | بسيط | ✅ نعم |
| journal_templates_list.html | `/var/www/tony_erp/templates/accounting/journal_templates_list.html` | بسيط | ✅ نعم |
| journal_drafts_list.html | `/var/www/tony_erp/templates/accounting/journal_drafts_list.html` | بسيط | ❌ **لا** |
| cost_centers_list.html | `/var/www/tony_erp/templates/accounting/cost_centers_list.html` | بسيط + card-header | ✅ نعم |
| cost_allocations_list.html | `/var/www/tony_erp/templates/accounting/cost_allocations_list.html` | بسيط | ✅ نعم |
| loan_list.html | `/var/www/tony_erp/templates/accounting/loan_list.html` | بسيط | ❌ **لا** |
| cheque_list.html | `/var/www/tony_erp/templates/accounting/cheque_list.html` | بسيط | ❌ **لا** |
| list.html (fiscal_years) | `/var/www/tony_erp/templates/accounting/fiscal_years/list.html` | بسيط | ✅ نعم |
| list.html (costing) | `/var/www/tony_erp/templates/accounting/costing/list.html` | بسيط | ❌ **لا** |

---

## 7️⃣ تطبيق CRM (إدارة العملاء)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| customer_list.html | `/var/www/tony_erp/templates/crm/customer_list.html` | بسيط | ✅ نعم |
| contact_list.html | `/var/www/tony_erp/templates/crm/contact_list.html` | بسيط | ✅ نعم |
| opportunity_list.html | `/var/www/tony_erp/templates/crm/opportunity_list.html` | بسيط | ❌ **لا** |
| quotation_list.html | `/var/www/tony_erp/templates/crm/quotation_list.html` | بسيط | ✅ نعم |
| ticket_list.html | `/var/www/tony_erp/templates/crm/ticket_list.html` | بسيط | ✅ نعم |
| ticket_list.html (tickets/) | `/var/www/tony_erp/templates/crm/tickets/ticket_list.html` | بسيط | ✅ نعم |
| contract_list.html | `/var/www/tony_erp/templates/crm/contract_list.html` | بسيط | ❌ **لا** |
| subscription_list.html | `/var/www/tony_erp/templates/crm/subscription_list.html` | بسيط | ✅ نعم |
| activity_list.html | `/var/www/tony_erp/templates/crm/activity_list.html` | بسيط | ❌ **لا** |
| followup_list.html | `/var/www/tony_erp/templates/crm/followup_list.html` | بسيط | ✅ نعم |
| task_list.html | `/var/www/tony_erp/templates/crm/task_list.html` | بسيط | ❌ **لا** |
| plan_list.html | `/var/www/tony_erp/templates/crm/plan_list.html` | بسيط | ✅ نعم |
| appointment_list.html | `/var/www/tony_erp/templates/crm/appointment_list.html` | بسيط | ✅ نعم |
| currency_list.html | `/var/www/tony_erp/templates/crm/currency_list.html` | بسيط | ✅ نعم |

---

## 8️⃣ تطبيق Fleet (الأسطول)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| vehicle_list.html | `/var/www/tony_erp/templates/fleet/vehicle_list.html` | بسيط | ❌ **لا** |
| driver_list.html | `/var/www/tony_erp/templates/fleet/driver_list.html` | بسيط | ❌ **لا** |
| trip_list.html | `/var/www/tony_erp/templates/fleet/trip_list.html` | بسيط | ❌ **لا** |
| maintenance_list.html | `/var/www/tony_erp/templates/fleet/maintenance_list.html` | بسيط + card-header | ✅ نعم |
| expense_list.html | `/var/www/tony_erp/templates/fleet/expense_list.html` | بسيط | ❌ **لا** |
| advance_list.html | `/var/www/tony_erp/templates/fleet/advance_list.html` | بسيط | ❌ **لا** |
| violation_list.html | `/var/www/tony_erp/templates/fleet/violation_list.html` | بسيط | ❌ **لا** |
| list.html (vehicle_types) | `/var/www/tony_erp/templates/fleet/vehicle_types/list.html` | ✅ **hero-section** | ❌ **لا** |
| list.html (expense_types) | `/var/www/tony_erp/templates/fleet/expense_types/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (unified_expenses) | `/var/www/tony_erp/templates/fleet/unified_expenses/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (spare_parts) | `/var/www/tony_erp/templates/fleet/spare_parts/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (spare_parts_permissions) | `/var/www/tony_erp/templates/fleet/spare_parts_permissions/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (vehicle_handover) | `/var/www/tony_erp/templates/fleet/vehicle_handover/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (maintenance_types) | `/var/www/tony_erp/templates/fleet/maintenance_types/list.html` | بسيط | ✅ نعم |
| list.html (garages) | `/var/www/tony_erp/templates/fleet/garages/list.html` | بسيط | ✅ نعم |
| list.html (maintenance_permissions) | `/var/www/tony_erp/templates/fleet/maintenance_permissions/list.html` | بسيط | ✅ نعم |
| list.html (odometer_adjustments) | `/var/www/tony_erp/templates/fleet/odometer_adjustments/list.html` | بسيط | ✅ نعم |
| list.html (holidays) | `/var/www/tony_erp/templates/fleet/holidays/list.html` | بسيط | ✅ نعم |
| list.html (fuel) | `/var/www/tony_erp/templates/fleet/fuel/list.html` | بسيط | ✅ نعم |
| list.html (maintenance_alerts) | `/var/www/tony_erp/templates/fleet/maintenance_alerts/list.html` | بسيط | ✅ نعم |
| list.html (oil_types) | `/var/www/tony_erp/templates/fleet/oil_types/list.html` | بسيط | ✅ نعم |

---

## 9️⃣ تطبيق Production (الإنتاج)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| orders_list.html | `/var/www/tony_erp/templates/production/orders_list.html` | بسيط | ✅ نعم |
| bom_list.html | `/var/www/tony_erp/templates/production/bom_list.html` | بسيط | ✅ نعم |
| workers_list.html | `/var/www/tony_erp/templates/production/workers_list.html` | بسيط | ✅ نعم |
| work_centers_list.html | `/var/www/tony_erp/templates/production/work_centers_list.html` | بسيط | ❌ **لا** |
| reports_list.html | `/var/www/tony_erp/templates/production/reports_list.html` | بسيط | ❌ **لا** |
| alerts_list.html | `/var/www/tony_erp/templates/production/alerts_list.html` | بسيط + card-header | ❌ **لا** |
| list.html (units) | `/var/www/tony_erp/templates/production/units/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (work_orders) | `/var/www/tony_erp/templates/production/work_orders/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (stages) | `/var/www/tony_erp/templates/production/stages/list.html` | بسيط + card-header | ❌ **لا** |

---

## 🔟 تطبيق Projects (المشاريع)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| project_list.html | `/var/www/tony_erp/templates/projects/project_list.html` | بسيط | ✅ نعم |
| list.html (quantities) | `/var/www/tony_erp/templates/projects/quantities/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (estimations) | `/var/www/tony_erp/templates/projects/estimations/list.html` | ✅ **hero-section** | ❌ **لا** |
| list.html (purchase_orders) | `/var/www/tony_erp/templates/projects/purchase_orders/list.html` | ✅ **hero-section** | ✅ نعم |
| list.html (types) | `/var/www/tony_erp/templates/projects/types/list.html` | بسيط | ✅ نعم |
| list.html (categories) | `/var/www/tony_erp/templates/projects/categories/list.html` | بسيط | ✅ نعم |
| list.html (contractors) | `/var/www/tony_erp/templates/projects/contractors/list.html` | بسيط | ✅ نعم |
| list.html (owner_statements) | `/var/www/tony_erp/templates/projects/owner_statements/list.html` | بسيط | ✅ نعم |
| list.html (contracts) | `/var/www/tony_erp/templates/projects/contracts/list.html` | بسيط | ✅ نعم |
| list.html (labour) | `/var/www/tony_erp/templates/projects/labour/list.html` | بسيط | ✅ نعم |
| list.html (adjustments) | `/var/www/tony_erp/templates/projects/adjustments/list.html` | بسيط | ✅ نعم |
| list.html (boq) | `/var/www/tony_erp/templates/projects/boq/list.html` | بسيط | ✅ نعم |
| list.html (plans) | `/var/www/tony_erp/templates/projects/plans/list.html` | بسيط | ❌ **لا** |

---

## 1️⃣1️⃣ تطبيق Shipping (الشحن)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| shipment_list.html | `/var/www/tony_erp/templates/shipping/shipment_list.html` | بسيط | ✅ نعم |
| company_list.html | `/var/www/tony_erp/templates/shipping/company_list.html` | بسيط | ✅ نعم |
| invoice_list.html | `/var/www/tony_erp/templates/shipping/invoice_list.html` | بسيط | ✅ نعم |
| pickup_list.html | `/var/www/tony_erp/templates/shipping/pickup_list.html` | بسيط | ✅ نعم |
| rate_list.html | `/var/www/tony_erp/templates/shipping/rate_list.html` | بسيط | ✅ نعم |
| zone_list.html | `/var/www/tony_erp/templates/shipping/zone_list.html` | بسيط | ✅ نعم |

---

## 1️⃣2️⃣ تطبيق Import/Export (الاستيراد والتصدير)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| import_order_list.html | `/var/www/tony_erp/templates/import_export/import_order_list.html` | بسيط | ✅ نعم |
| export_order_list.html | `/var/www/tony_erp/templates/import_export/export_order_list.html` | بسيط | ✅ نعم |
| customs_clearance_list.html | `/var/www/tony_erp/templates/import_export/customs_clearance_list.html` | بسيط | ✅ نعم |
| shipping_agent_list.html | `/var/www/tony_erp/templates/import_export/shipping_agent_list.html` | بسيط | ✅ نعم |
| import_certificate_list.html | `/var/www/tony_erp/templates/import_export/import_certificate_list.html` | بسيط | ✅ نعم |
| export_certificate_list.html | `/var/www/tony_erp/templates/import_export/export_certificate_list.html` | بسيط | ✅ نعم |
| import_waiver_list.html | `/var/www/tony_erp/templates/import_export/import_waiver_list.html` | بسيط | ✅ نعم |
| pre_export_invoice_list.html | `/var/www/tony_erp/templates/import_export/pre_export_invoice_list.html` | بسيط | ✅ نعم |
| release_order_list.html | `/var/www/tony_erp/templates/import_export/release_order_list.html` | بسيط | ✅ نعم |
| financial_approval_list.html | `/var/www/tony_erp/templates/import_export/financial_approval_list.html` | بسيط | ✅ نعم |

---

## 1️⃣3️⃣ تطبيق Installments (الأقساط)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| contract_list.html | `/var/www/tony_erp/templates/installments/contract_list.html` | بسيط | ✅ نعم |
| contracts_list.html | `/var/www/tony_erp/templates/installments/contracts_list.html` | بسيط | ✅ نعم |
| overdue_list.html | `/var/www/tony_erp/templates/installments/overdue_list.html` | بسيط | ❌ **لا** |
| collection_actions_list.html | `/var/www/tony_erp/templates/installments/collection_actions_list.html` | بسيط | ✅ نعم |
| credit_score_list.html | `/var/www/tony_erp/templates/installments/credit_score_list.html` | بسيط | ✅ نعم |
| early_settlement_list.html | `/var/www/tony_erp/templates/installments/early_settlement_list.html` | بسيط | ✅ نعم |
| reschedule_list.html | `/var/www/tony_erp/templates/installments/reschedule_list.html` | بسيط | ✅ نعم |
| transfer_list.html | `/var/www/tony_erp/templates/installments/transfer_list.html` | بسيط | ✅ نعم |
| waiver_list.html | `/var/www/tony_erp/templates/installments/waiver_list.html` | بسيط | ✅ نعم |

---

## 1️⃣4️⃣ تطبيق Ecommerce (التجارة الإلكترونية)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| brands_list.html | `/var/www/tony_erp/templates/ecommerce/brands_list.html` | بسيط | ✅ نعم |
| categories_list.html | `/var/www/tony_erp/templates/ecommerce/categories_list.html` | بسيط | ✅ نعم |
| customers_list.html | `/var/www/tony_erp/templates/ecommerce/admin/customers_list.html` | بسيط | ✅ نعم |
| social_auth_list.html | `/var/www/tony_erp/templates/ecommerce/admin/social_auth_list.html` | بسيط | ✅ نعم |
| card_list.html (warranty) | `/var/www/tony_erp/templates/ecommerce/admin/warranty/card_list.html` | بسيط | ✅ نعم |
| claim_list.html (warranty) | `/var/www/tony_erp/templates/ecommerce/admin/warranty/claim_list.html` | بسيط | ✅ نعم |
| policy_list.html (warranty) | `/var/www/tony_erp/templates/ecommerce/admin/warranty/policy_list.html` | بسيط | ✅ نعم |
| registration_list.html (warranty) | `/var/www/tony_erp/templates/ecommerce/admin/warranty/registration_list.html` | بسيط | ✅ نعم |

---

## 1️⃣5️⃣ تطبيق Eservices (الخدمات الإلكترونية)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| provider_list.html | `/var/www/tony_erp/templates/eservices/provider_list.html` | بسيط | ✅ نعم |
| operator_list.html | `/var/www/tony_erp/templates/eservices/operator_list.html` | بسيط | ✅ نعم |
| service_list.html | `/var/www/tony_erp/templates/eservices/service_list.html` | بسيط | ✅ نعم |
| transaction_list.html | `/var/www/tony_erp/templates/eservices/transaction_list.html` | بسيط | ✅ نعم |
| category_list.html | `/var/www/tony_erp/templates/eservices/category_list.html` | بسيط | ❌ **لا** |

---

## 1️⃣6️⃣ تطبيق Maintenance (الصيانة)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| machine_list.html | `/var/www/tony_erp/templates/maintenance/machine_list.html` | بسيط | ❌ **لا** |
| spare_part_list.html | `/var/www/tony_erp/templates/maintenance/spare_part_list.html` | بسيط | ✅ نعم |
| maintenance_record_list.html | `/var/www/tony_erp/templates/maintenance/maintenance_record_list.html` | بسيط | ✅ نعم |
| maintenance_schedule_list.html | `/var/www/tony_erp/templates/maintenance/maintenance_schedule_list.html` | بسيط | ✅ نعم |
| maintenance_request_list.html | `/var/www/tony_erp/templates/maintenance/maintenance_request_list.html` | بسيط | ✅ نعم |
| schedules_list.html (preventive) | `/var/www/tony_erp/templates/maintenance/preventive/schedules_list.html` | بسيط | ✅ نعم |

---

## 1️⃣7️⃣ تطبيق Fixed Assets (الأصول الثابتة)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| asset_list.html | `/var/www/tony_erp/templates/fixed_assets/asset_list.html` | بسيط | ❌ **لا** |
| category_list.html | `/var/www/tony_erp/templates/fixed_assets/category_list.html` | بسيط | ❌ **لا** |
| maintenance_list.html | `/var/www/tony_erp/templates/fixed_assets/maintenance_list.html` | بسيط | ✅ نعم |

---

## 1️⃣8️⃣ تطبيق Payments (المدفوعات)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| transactions_list.html | `/var/www/tony_erp/templates/payments/transactions_list.html` | بسيط | ✅ نعم |
| installments_list.html | `/var/www/tony_erp/templates/payments/installments_list.html` | ✅ **ds-card** | ✅ نعم |
| loans_list.html | `/var/www/tony_erp/templates/payments/loans_list.html` | بسيط | ❌ **لا** |
| payment_methods_list.html | `/var/www/tony_erp/templates/payments/payment_methods_list.html` | بسيط | ❌ **لا** |

---

## 1️⃣9️⃣ تطبيق Attendance (الحضور)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| attendance_list.html | `/var/www/tony_erp/templates/attendance/attendance_list.html` | بسيط | ✅ نعم |
| locations_list.html | `/var/www/tony_erp/templates/attendance/locations_list.html` | بسيط | ✅ نعم |
| request_list.html | `/var/www/tony_erp/templates/attendance/request_list.html` | بسيط + card-header | ✅ نعم |

---

## 2️⃣0️⃣ تطبيق Contracting (المقاولات)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| project_list.html | `/var/www/tony_erp/templates/contracting/project_list.html` | بسيط | ✅ نعم |
| contract_list.html | `/var/www/tony_erp/templates/contracting/contract_list.html` | بسيط | ❌ **لا** |
| worker_list.html | `/var/www/tony_erp/templates/contracting/worker_list.html` | بسيط | ❌ **لا** |
| material_list.html | `/var/www/tony_erp/templates/contracting/material_list.html` | بسيط | ✅ نعم |
| equipment_list.html | `/var/www/tony_erp/templates/contracting/equipment_list.html` | بسيط | ✅ نعم |
| expense_list.html | `/var/www/tony_erp/templates/contracting/expense_list.html` | بسيط | ❌ **لا** |
| receipt_list.html | `/var/www/tony_erp/templates/contracting/receipt_list.html` | بسيط | ❌ **لا** |
| attendance_list.html | `/var/www/tony_erp/templates/contracting/attendance_list.html` | بسيط | ✅ نعم |

---

## 2️⃣1️⃣ تطبيق Taxes (الضرائب)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| invoice_list.html | `/var/www/tony_erp/templates/taxes/invoice_list.html` | بسيط | ✅ نعم |
| payment_list.html | `/var/www/tony_erp/templates/taxes/payment_list.html` | بسيط | ✅ نعم |
| period_list.html | `/var/www/tony_erp/templates/taxes/period_list.html` | بسيط | ✅ نعم |
| category_list.html | `/var/www/tony_erp/templates/taxes/category_list.html` | بسيط + card-header | ✅ نعم |

---

## 2️⃣2️⃣ تطبيق Users (المستخدمين)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| user_list.html | `/var/www/tony_erp/templates/users/user_list.html` | بسيط | ✅ نعم |
| role_list.html | `/var/www/tony_erp/templates/users/role_list.html` | بسيط | ❌ **لا** |
| list.html (roles) | `/var/www/tony_erp/templates/users/roles/list.html` | بسيط | ✅ نعم |

---

## 2️⃣3️⃣ تطبيق Home Services (الخدمات المنزلية)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| package_list.html | `/var/www/tony_erp/templates/home_services/admin/package_list.html` | ✅ **hero-section** | ✅ نعم |
| category_list.html | `/var/www/tony_erp/templates/home_services/admin/category_list.html` | ✅ **hero-section** | ✅ نعم |
| request_list.html | `/var/www/tony_erp/templates/home_services/admin/request_list.html` | بسيط | ✅ نعم |

---

## 2️⃣4️⃣ تطبيق POS (نقاط البيع)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| installments_list.html | `/var/www/tony_erp/templates/pos/installments_list.html` | بسيط | ✅ نعم |

---

## 2️⃣5️⃣ تطبيق Mosool

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| approval_list.html | `/var/www/tony_erp/templates/mosool/approval_list.html` | بسيط | ✅ نعم |
| preparation_list.html | `/var/www/tony_erp/templates/mosool/preparation_list.html` | بسيط | ✅ نعم |

---

## 2️⃣6️⃣ تطبيق Core (الأساسي)

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| list.html (countries) | `/var/www/tony_erp/templates/core/countries/list.html` | بسيط | ✅ نعم |
| list.html (states) | `/var/www/tony_erp/templates/core/states/list.html` | بسيط | ✅ نعم |
| list.html (branches) | `/var/www/tony_erp/templates/core/branches/list.html` | بسيط | ✅ نعم |
| list.html (pages) | `/var/www/tony_erp/templates/core/pages/list.html` | بسيط + card-header | ✅ نعم |

---

## 2️⃣7️⃣ تطبيقات أخرى

| الملف | المسار الكامل | نوع التصميم | متجاوب |
|-------|---------------|-------------|--------|
| config_list.html (woocommerce) | `/var/www/tony_erp/templates/woocommerce_integration/config_list.html` | بسيط | ❌ **لا** |
| list.html (approvals) | `/var/www/tony_erp/templates/approvals/list.html` | بسيط | ❌ **لا** |
| list.html (showrooms) | `/var/www/tony_erp/templates/showrooms/list.html` | بسيط | ❌ **لا** |
| list.html (notifications) | `/var/www/tony_erp/templates/notifications/list.html` | بسيط | ❌ **لا** |

---

## 🔴 قائمة الصفحات التي تحتاج تحديث عاجل

### الصفحات غير المتجاوبة (بدون table-responsive) - الأولوية القصوى:

1. `/var/www/tony_erp/templates/users/role_list.html`
2. `/var/www/tony_erp/templates/eservices/category_list.html`
3. `/var/www/tony_erp/templates/fleet/advance_list.html`
4. `/var/www/tony_erp/templates/fleet/vehicle_types/list.html`
5. `/var/www/tony_erp/templates/fleet/expense_list.html`
6. `/var/www/tony_erp/templates/fleet/trip_list.html`
7. `/var/www/tony_erp/templates/fleet/driver_list.html`
8. `/var/www/tony_erp/templates/fleet/vehicle_list.html`
9. `/var/www/tony_erp/templates/fleet/violation_list.html`
10. `/var/www/tony_erp/templates/production/reports_list.html`
11. `/var/www/tony_erp/templates/production/stages/list.html`
12. `/var/www/tony_erp/templates/production/work_centers_list.html`
13. `/var/www/tony_erp/templates/production/alerts_list.html`
14. `/var/www/tony_erp/templates/hr/job_vacancy_list.html`
15. `/var/www/tony_erp/templates/hr/department_list.html`
16. `/var/www/tony_erp/templates/hr/id_card_template_list.html`
17. `/var/www/tony_erp/templates/hr/job_application_list.html`
18. `/var/www/tony_erp/templates/sales/invoice_list.html`
19. `/var/www/tony_erp/templates/sales/discount/customer_discount_list.html`
20. `/var/www/tony_erp/templates/installments/overdue_list.html`
21. `/var/www/tony_erp/templates/projects/plans/list.html`
22. `/var/www/tony_erp/templates/projects/estimations/list.html`
23. `/var/www/tony_erp/templates/maintenance/machine_list.html`
24. `/var/www/tony_erp/templates/woocommerce_integration/config_list.html`
25. `/var/www/tony_erp/templates/purchases/quotation/list.html`
26. `/var/www/tony_erp/templates/purchases/shipment/list.html`
27. `/var/www/tony_erp/templates/purchases/receipt/list.html`
28. `/var/www/tony_erp/templates/purchases/pr/pr_list.html`
29. `/var/www/tony_erp/templates/purchases/rfq/list.html`
30. `/var/www/tony_erp/templates/purchases/po_list.html`
31. `/var/www/tony_erp/templates/accounting/journal_drafts_list.html`
32. `/var/www/tony_erp/templates/accounting/loan_list.html`
33. `/var/www/tony_erp/templates/accounting/costing/list.html`
34. `/var/www/tony_erp/templates/accounting/cheque_list.html`
35. `/var/www/tony_erp/templates/inventory/receiving_list.html`
36. `/var/www/tony_erp/templates/inventory/count_list.html`
37. `/var/www/tony_erp/templates/inventory/requisition_list.html`
38. `/var/www/tony_erp/templates/inventory/issue_list.html`
39. `/var/www/tony_erp/templates/inventory/catalog/catalog_list.html`
40. `/var/www/tony_erp/templates/fixed_assets/asset_list.html`
41. `/var/www/tony_erp/templates/fixed_assets/category_list.html`
42. `/var/www/tony_erp/templates/payments/loans_list.html`
43. `/var/www/tony_erp/templates/payments/payment_methods_list.html`
44. `/var/www/tony_erp/templates/crm/opportunity_list.html`
45. `/var/www/tony_erp/templates/crm/task_list.html`
46. `/var/www/tony_erp/templates/crm/activity_list.html`
47. `/var/www/tony_erp/templates/crm/contract_list.html`
48. `/var/www/tony_erp/templates/contracting/worker_list.html`
49. `/var/www/tony_erp/templates/contracting/receipt_list.html`
50. `/var/www/tony_erp/templates/contracting/expense_list.html`
51. `/var/www/tony_erp/templates/contracting/contract_list.html`
52. `/var/www/tony_erp/templates/approvals/list.html`
53. `/var/www/tony_erp/templates/showrooms/list.html`
54. `/var/www/tony_erp/templates/notifications/list.html`

---

## 📊 توصيات التحديث

### 1. الأولوية الأولى (عاجل):
- إضافة `table-responsive` لجميع الجداول غير المتجاوبة (~58 ملف)
- تحديث الصفحات المستخدمة بكثرة (sales, purchases, inventory)

### 2. الأولوية الثانية (مهم):
- توحيد التصميم باستخدام `ds-card` أو `hero-section` للصفحات الرئيسية
- تحديث الصفحات التي تستخدم `base.html` القديم إلى `base_v2.html`

### 3. الأولوية الثالثة (تحسين):
- توحيد استخدام `_list_professional.html` كقالب موحد لكل القوائم
- إضافة خصائص البحث والفلترة الموحدة

---

## ملاحظات:
- **hero-section**: تصميم حديث مع header ملون متدرج
- **ds-card**: تصميم بطاقات حديث مع ظلال
- **card-header**: تصميم بطاقات Bootstrap التقليدي
- **table-responsive**: يضمن التمرير الأفقي على الشاشات الصغيرة

---

*تم إنشاء هذا التقرير تلقائياً في 2 يناير 2026*
