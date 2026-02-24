"""
Sidebar Menu Configuration - نموذج بيانات موحد للقائمة الجانبية
==================================================================
Updated: 2025-12-08 22:41 - Added advanced purchasing features (PR, RFQ, Quotations, Shipments, Receipts)

هذا الملف يحتوي على التكوين الكامل للقائمة الجانبية (Sidebar) مقسمة إلى:
- أقسام رئيسية (Main Sections)
- مجموعات فرعية داخل كل قسم (Categories):
  * daily: عمليات يومية
  * master: تعريفات وإعدادات
  * reports: تقارير واستعلامات
- عناصر القائمة (Menu Items)

الاستخدام:
---------
from core.sidebar_config import get_sidebar_config
sidebar_data = get_sidebar_config()
"""

from django.utils.translation import gettext_lazy as _


# ===============================================
# تعريف البنية: Category Types
# ===============================================
CATEGORY_DAILY = 'daily'        # عمليات يومية
CATEGORY_MASTER = 'master'      # تعريفات / إعدادات
CATEGORY_REPORTS = 'reports'    # تقارير / استعلامات


# ===============================================
# تعريف الأقسام الرئيسية والعناصر الفرعية
# ===============================================
SIDEBAR_CONFIG = {
    'dashboard': {
        'id': 'dashboard',
        'label': _('الرئيسية'),
        'icon': 'bi-speedometer2',
        'order': 1,
        'module': None,  # لا ترتبط بوحدة معينة
        'items': [
            {
                'id': 'dashboard_main',
                'label': _('لوحة التحكم'),
                'url': 'core:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': None,  # متاح للجميع
            },
            {
                'id': 'notifications',
                'label': _('الإشعارات'),
                'url': 'notifications:list',
                'icon': 'bi-bell',
                'category': CATEGORY_DAILY,
                'permission': None,
                'badge_key': 'unread_notifications_count',
            },
            {
                'id': 'approvals',
                'label': _('الموافقات'),
                'url': 'approvals:list',
                'icon': 'bi-check2-circle',
                'category': CATEGORY_DAILY,
                'permission': None,
            },
        ]
    },
    
    'sales': {
        'id': 'sales',
        'label': _('المبيعات'),
        'icon': 'bi-cart-check',
        'order': 2,
        'module': 'sales',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'sales_dashboard',
                'label': _('لوحة المبيعات'),
                'url': 'sales:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'sales_invoice_create',
                'label': _('فاتورة مبيعات جديدة'),
                'url': 'sales:invoice_create',
                'icon': 'bi-file-earmark-plus',
                'category': CATEGORY_DAILY,
                'permission': 'add',
                'resource': 'invoice_create',
            },
            {
                'id': 'sales_invoice_list',
                'label': _('قائمة الفواتير'),
                'url': 'sales:invoice_list',
                'icon': 'bi-card-list',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'sales_return_start',
                'label': _('مرتجع مبيعات'),
                'url': 'sales:sales_return_start',
                'icon': 'bi-arrow-return-left',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'sales_receipt_create',
                'label': _('سند قبض'),
                'url': 'sales:receipt_create',
                'icon': 'bi-cash-coin',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'customer_discount_create',
                'label': _('خصم مسموح به'),
                'url': 'sales:customer_discount_create',
                'icon': 'bi-percent',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            
            # === تعريفات ===
            {
                'id': 'customers_list',
                'label': _('العملاء'),
                'url': 'partners:customers_list',
                'icon': 'bi-people',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'customer_create',
                'label': _('عميل جديد'),
                'url': 'partners:customer_create',
                'icon': 'bi-person-plus',
                'category': CATEGORY_MASTER,
                'permission': 'add',
            },
            {
                'id': 'sales_pricing_offers',
                'label': _('التسعير والعروض'),
                'url': 'sales:pricing_offers',
                'icon': 'bi-tag',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            
            # === تقارير ===
            {
                'id': 'customer_discount_list',
                'label': _('سجل الخصومات المسموح بها'),
                'url': 'sales:customer_discount_list',
                'icon': 'bi-list-ul',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'sales_payments_overview',
                'label': _('مدفوعات العملاء'),
                'url': 'accounting:sales_payments_overview',
                'icon': 'bi-cash-stack',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'customer_statement',
                'label': _('كشف حساب عميل'),
                'url': 'accounting:sales_customer_statement_sample',
                'icon': 'bi-file-text',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'sales_report',
                'label': _('تقرير المبيعات'),
                'url': 'reports:sales_report',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'purchases': {
        'id': 'purchases',
        'label': _('المشتريات'),
        'icon': 'bi-bag-plus',
        'order': 3,
        'module': 'purchases',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            # طلبات الشراء (PR)
            {
                'id': 'pr_create',
                'label': _('طلب شراء جديد'),
                'url': 'purchases:pr_create',
                'icon': 'bi-clipboard-plus',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'pr_list',
                'label': _('طلبات الشراء'),
                'url': 'purchases:pr_list',
                'icon': 'bi-clipboard-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # طلبات عروض الأسعار (RFQ)
            {
                'id': 'rfq_create',
                'label': _('طلب عروض جديد'),
                'url': 'purchases:rfq_create',
                'icon': 'bi-envelope-plus',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'rfq_list',
                'label': _('طلبات عروض الأسعار'),
                'url': 'purchases:rfq_list',
                'icon': 'bi-envelopes',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # عروض الموردين
            {
                'id': 'quotation_list',
                'label': _('عروض الموردين'),
                'url': 'purchases:quotation_list',
                'icon': 'bi-receipt',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # طلبات شراء من المخازن
            {
                'id': 'warehouse_purchase_requests',
                'label': _('طلبات شراء من المخازن'),
                'url': 'purchases:warehouse_purchase_requests',
                'icon': 'bi-box-seam',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # أوامر الشراء
            {
                'id': 'po_create',
                'label': _('أمر شراء جديد'),
                'url': 'purchases:po_create',
                'icon': 'bi-file-earmark-text',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'po_list',
                'label': _('أوامر الشراء'),
                'url': 'purchases:po_list',
                'icon': 'bi-list-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'badge_key': 'pending_purchase_orders_count',
            },
            # الشحنات واستلام البضائع
            {
                'id': 'shipment_list',
                'label': _('الشحنات'),
                'url': 'purchases:shipment_list',
                'icon': 'bi-truck',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'receipt_list',
                'label': _('سندات الاستلام'),
                'url': 'purchases:receipt_list',
                'icon': 'bi-inbox',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # فواتير الشراء
            {
                'id': 'purchase_create',
                'label': _('مشتريات جديدة'),
                'url': 'purchases:purchase_create',
                'icon': 'bi-file-earmark-plus',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'purchase_list',
                'label': _('قائمة المشتريات'),
                'url': 'purchases:purchase_list',
                'icon': 'bi-card-list',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # خصم مكتسب (من الموردين)
            {
                'id': 'supplier_discount_create',
                'label': _('خصم مكتسب'),
                'url': 'purchases:supplier_discount_create',
                'icon': 'bi-percent',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            
            # === تعريفات ===
            {
                'id': 'suppliers_list',
                'label': _('الموردين'),
                'url': 'partners:suppliers_list',
                'icon': 'bi-people',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'supplier_create',
                'label': _('إضافة مورد جديد'),
                'url': 'partners:supplier_create',
                'icon': 'bi-person-plus-fill',
                'category': CATEGORY_MASTER,
                'permission': 'add',
            },
            
            # === تقارير ===
            {
                'id': 'supplier_material_prices',
                'label': _('أسعار المواد الخام لكل مورد'),
                'url': 'purchases:supplier_material_prices',
                'icon': 'bi-tags',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'price_comparison',
                'label': _('مقارنة الأسعار'),
                'url': 'purchases:price_comparison',
                'icon': 'bi-graph-down-arrow',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'supplier_performance',
                'label': _('أداء الموردين'),
                'url': 'purchases:supplier_performance',
                'icon': 'bi-star',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'purchasing_analytics',
                'label': _('تحليلات المشتريات'),
                'url': 'purchases:purchasing_analytics',
                'icon': 'bi-pie-chart',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'vendors_balances',
                'label': _('أرصدة الموردين'),
                'url': 'purchases:vendors_balances',
                'icon': 'bi-cash-stack',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'badge_key': 'suppliers_with_debt_nav',
            },
            {
                'id': 'supplier_discount_list',
                'label': _('سجل الخصومات المكتسبة'),
                'url': 'purchases:supplier_discount_list',
                'icon': 'bi-list-ul',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'inventory': {
        'id': 'inventory',
        'label': _('المخزون'),
        'icon': 'bi-boxes',
        'order': 4,
        'module': 'inventory',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === الدورة المستندية (الأهم) ===
            {
                'id': 'document_cycle',
                'label': _('📋 الدورة المستندية'),
                'url': 'inventory:document_cycle',
                'icon': 'bi-diagram-3',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'bom_list',
                'label': _('🔧 قوائم المكونات (BOM)'),
                'url': 'inventory:bom_list',
                'icon': 'bi-list-nested',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            # === عمليات يومية ===
            {
                'id': 'catalog_list',
                'label': _('📔 كتالوج المنتجات'),
                'url': 'inventory:catalog_list',
                'icon': 'bi-journal-richtext',
                'category': CATEGORY_DAILY,
                'permission': None,
            },
            {
                'id': 'inventory_stock_management',
                'label': _('إدارة المخزون'),
                'url': 'inventory:stock_management',
                'icon': 'bi-grid-3x3',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'resource': 'stock_management',
            },
            {
                'id': 'inventory_receiving_create',
                'label': _('استلام بضاعة'),
                'url': 'inventory:receiving_create',
                'icon': 'bi-box-arrow-in-down',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'inventory_issue_create',
                'label': _('صرف بضاعة'),
                'url': 'inventory:issue_create',
                'icon': 'bi-box-arrow-up',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'inventory_transfer_list',
                'label': _('تحويلات المخزون'),
                'url': 'inventory:transfer_list',
                'icon': 'bi-arrow-left-right',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'inventory_count_create',
                'label': _('جرد جديد'),
                'url': 'inventory:count_create',
                'icon': 'bi-clipboard-check',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'inventory_barcode_scanner',
                'label': _('مسح الباركود'),
                'url': 'inventory:barcode_scanner',
                'icon': 'bi-upc-scan',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            
            # === تعريفات ===
            {
                'id': 'product_list',
                'label': _('المنتجات'),
                'url': 'inventory:product_list',
                'icon': 'bi-box-seam',
                'category': CATEGORY_MASTER,
                'permission': 'view',
                'resource': 'product_list',
            },
            {
                'id': 'category_list',
                'label': _('فئات المنتجات'),
                'url': 'inventory:category_list',
                'icon': 'bi-folder2-open',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'product_add',
                'label': _('منتج جديد'),
                'url': 'inventory:product_add',
                'icon': 'bi-plus-square',
                'category': CATEGORY_MASTER,
                'permission': 'add',
            },
            {
                'id': 'location_list',
                'label': _('المواقع/المخازن'),
                'url': 'inventory:location_list',
                'icon': 'bi-building',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'inventory_barcode_management',
                'label': _('إدارة الباركود'),
                'url': 'inventory:barcode_management',
                'icon': 'bi-upc',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            
            # === تقارير ===
            {
                'id': 'warehouse_summary',
                'label': _('ملخص المخزون'),
                'url': 'inventory:warehouse_summary',
                'icon': 'bi-card-text',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'inventory_valuation_report',
                'label': _('تقرير تقييم المخزون'),
                'url': 'inventory:valuation_report',
                'icon': 'bi-currency-dollar',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'inventory_aging_report',
                'label': _('تقرير أقدمية المخزون'),
                'url': 'inventory:aging_report',
                'icon': 'bi-clock-history',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'inventory_report',
                'label': _('تقرير المخزون'),
                'url': 'reports:inventory_report',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'accounting': {
        'id': 'accounting',
        'label': _('المحاسبة'),
        'icon': 'bi-calculator',
        'order': 5,
        'module': 'accounting',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية - القيود والحركة ===
            {
                'id': 'accounting_dashboard',
                'label': _('لوحة المحاسبة'),
                'url': 'accounting:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'order': 1,
            },
            {
                'id': 'journal_entry_create',
                'label': _('قيد جديد'),
                'url': 'accounting:journal_entry_create',
                'icon': 'bi-plus-square',
                'category': CATEGORY_DAILY,
                'permission': 'add',
                'order': 2,
            },
            {
                'id': 'journal_entries_unposted',
                'label': _('قيود غير مُرحّلة'),
                'url': 'accounting:journal_entries_list',
                'icon': 'bi-exclamation-circle',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'badge_key': 'unposted_journal_entries_count',
                'order': 3,
            },
            {
                'id': 'journal_entries_list',
                'label': _('القيود المحاسبية'),
                'url': 'accounting:journal_entries_list',
                'icon': 'bi-journal-text',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'order': 4,
            },
            
            # === عمليات يومية - الخزينة والبنوك ===
            {
                'id': 'receipt_voucher_create',
                'label': _('سند قبض'),
                'url': 'accounting:cash_receipt_create',
                'icon': 'bi-arrow-down-circle',
                'category': CATEGORY_DAILY,
                'permission': 'add',
                'order': 5,
            },
            {
                'id': 'payment_voucher_create',
                'label': _('سند صرف'),
                'url': 'accounting:cash_payment_create',
                'icon': 'bi-arrow-up-circle',
                'category': CATEGORY_DAILY,
                'permission': 'add',
                'order': 6,
            },
            {
                'id': 'cash_transfer_form',
                'label': _('تحويل نقدي'),
                'url': 'accounting:cash_transfer_create',
                'icon': 'bi-arrow-left-right',
                'category': CATEGORY_DAILY,
                'permission': 'add',
                'order': 7,
            },
            {
                'id': 'bank_reconcile',
                'label': _('تسوية بنكية'),
                'url': 'accounting:bank_reconcile',
                'icon': 'bi-bank',
                'category': CATEGORY_DAILY,
                'permission': 'change',
                'order': 8,
            },
            {
                'id': 'cash_positions',
                'label': _('الأرصدة النقدية'),
                'url': 'accounting:cash_positions',
                'icon': 'bi-cash-stack',
                'category': CATEGORY_DAILY,
                'permission': 'view',
                'order': 9,
            },
            
            # === تعريفات - الحسابات الأساسية ===
            {
                'id': 'chart_of_accounts',
                'label': _('دليل الحسابات'),
                'url': 'accounting:chart_of_accounts',
                'icon': 'bi-diagram-3',
                'category': CATEGORY_MASTER,
                'permission': 'view',
                'order': 1,
            },
            {
                'id': 'account_create',
                'label': _('حساب جديد'),
                'url': 'accounting:account_create',
                'icon': 'bi-plus-circle',
                'category': CATEGORY_MASTER,
                'permission': 'add',
                'order': 2,
            },
            {
                'id': 'cost_centers_list',
                'label': _('مراكز التكلفة'),
                'url': 'accounting:cost_centers_list',
                'icon': 'bi-building',
                'category': CATEGORY_MASTER,
                'permission': 'view',
                'order': 3,
            },
            
            # === تعريفات - الإعدادات ===
            {
                'id': 'accounting_settings',
                'label': _('تكوين الحسابات'),
                'url': 'accounting:settings',
                'icon': 'bi-gear',
                'category': CATEGORY_MASTER,
                'permission': 'change',
                'order': 4,
            },
            {
                'id': 'accounting_tax_settings',
                'label': _('إعدادات الضرائب'),
                'url': 'accounting:tax_settings',
                'icon': 'bi-percent',
                'category': CATEGORY_MASTER,
                'permission': 'change',
                'order': 5,
            },
            {
                'id': 'fiscal_year_settings',
                'label': _('السنة المالية'),
                'url': 'accounting:fiscal_year_create',
                'icon': 'bi-calendar3',
                'category': CATEGORY_MASTER,
                'permission': 'change',
                'order': 6,
            },
            
            # === تقارير - القوائم المالية الأساسية ===
            {
                'id': 'trial_balance',
                'label': _('ميزان المراجعة'),
                'url': 'accounting:trial_balance',
                'icon': 'bi-diagram-3',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 1,
            },
            {
                'id': 'balance_sheet',
                'label': _('الميزانية العمومية'),
                'url': 'accounting:balance_sheet',
                'icon': 'bi-clipboard-data',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 2,
            },
            {
                'id': 'income_statement',
                'label': _('قائمة الدخل'),
                'url': 'accounting:income_statement',
                'icon': 'bi-graph-up-arrow',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 3,
            },
            {
                'id': 'cash_flow_statement',
                'label': _('قائمة التدفقات النقدية'),
                'url': 'accounting:cash_flow_statement',
                'icon': 'bi-water',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 4,
            },
            
            # === تقارير - التقارير التفصيلية ===
            {
                'id': 'general_ledger',
                'label': _('دفتر الأستاذ العام'),
                'url': 'accounting:general_ledger',
                'icon': 'bi-journal-check',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 5,
            },
            {
                'id': 'account_statement',
                'label': _('كشف حساب'),
                'url': 'accounting:account_statement',
                'icon': 'bi-file-text',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 6,
            },
            {
                'id': 'aging_receivables',
                'label': _('أعمار الذمم المدينة'),
                'url': 'accounting:aging_receivables_report',
                'icon': 'bi-hourglass-split',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 7,
            },
            {
                'id': 'aging_payables',
                'label': _('أعمار الذمم الدائنة'),
                'url': 'accounting:aging_payables_report',
                'icon': 'bi-hourglass',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 8,
            },
            {
                'id': 'cost_center_report',
                'label': _('تقرير مراكز التكلفة'),
                'url': 'accounting:cost_centers_list',
                'icon': 'bi-pie-chart',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'order': 9,
            },
        ]
    },
    
    'pos': {
        'id': 'pos',
        'label': _('نقطة البيع'),
        'icon': 'bi-receipt',
        'order': 6,
        'module': 'pos',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'pos_dashboard',
                'label': _('لوحة نقطة البيع'),
                'url': 'pos:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'pos_new_order',
                'label': _('طلب جديد'),
                'url': 'pos:new_order',
                'icon': 'bi-plus-circle',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
        ]
    },
    
    'hr': {
        'id': 'hr',
        'label': _('الموارد البشرية'),
        'icon': 'bi-people',
        'order': 7,
        'module': 'hr',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'hr_dashboard',
                'label': _('لوحة الموارد البشرية'),
                'url': 'hr:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'hr_attendance_dashboard',
                'label': _('الحضور والانصراف'),
                'url': 'hr:attendance_dashboard',
                'icon': 'bi-clock',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'hr_leave_dashboard',
                'label': _('إدارة الإجازات'),
                'url': 'hr:leave_dashboard',
                'icon': 'bi-calendar-x',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'hr_employee_portal',
                'label': _('بوابة الموظف'),
                'url': 'hr:employee_portal',
                'icon': 'bi-person-workspace',
                'category': CATEGORY_DAILY,
                'permission': None,  # متاح للموظفين
            },
            {
                'id': 'hr_leave_approval',
                'label': _('موافقة الإجازات'),
                'url': 'hr:leave_approval_dashboard',
                'icon': 'bi-check-circle',
                'category': CATEGORY_DAILY,
                'permission': 'change',  # للمدراء فقط
                'badge_key': 'pending_leave_requests_count',
            },
            {
                'id': 'hr_payroll_dashboard',
                'label': _('الرواتب'),
                'url': 'hr:payroll_dashboard',
                'icon': 'bi-cash',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'hr_employee_list',
                'label': _('الموظفون'),
                'url': 'hr:employee_list',
                'icon': 'bi-people',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'hr_department_list',
                'label': _('الأقسام'),
                'url': 'hr:department_list',
                'icon': 'bi-building',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'hr_position_list',
                'label': _('المناصب'),
                'url': 'hr:position_list',
                'icon': 'bi-briefcase',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'hr_job_vacancy_list',
                'label': _('الوظائف الشاغرة'),
                'url': 'hr:job_vacancy_list',
                'icon': 'bi-card-checklist',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'hr_id_cards',
                'label': _('كروت الموظفين'),
                'url': 'hr:employee_id_cards_list',
                'icon': 'bi-person-badge',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'hr_printer_config',
                'label': _('إعدادات الطابعات'),
                'url': 'admin:inventory_printerconfiguration_changelist',
                'icon': 'bi-printer',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            
            # === تقارير ===
            {
                'id': 'hr_reports_dashboard',
                'label': _('تقارير الموارد البشرية'),
                'url': 'hr:reports_dashboard',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'hr_performance_dashboard',
                'label': _('تقييم الأداء'),
                'url': 'hr:performance_dashboard',
                'icon': 'bi-star',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'crm': {
        'id': 'crm',
        'label': _('إدارة علاقات العملاء'),
        'icon': 'bi-person-hearts',
        'order': 8,
        'module': 'crm',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'crm_dashboard',
                'label': _('لوحة CRM'),
                'url': 'crm:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'crm_opportunity_create',
                'label': _('فرصة جديدة'),
                'url': 'crm:opportunity_create',
                'icon': 'bi-bullseye',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'crm_opportunity_list',
                'label': _('الفرص التجارية'),
                'url': 'crm:opportunity_list',
                'icon': 'bi-kanban',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'crm_quotation_create',
                'label': _('عرض سعر جديد'),
                'url': 'crm:quotation_create',
                'icon': 'bi-file-earmark-plus',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'crm_quotation_list',
                'label': _('عروض الأسعار'),
                'url': 'crm:quotation_list',
                'icon': 'bi-card-list',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'crm_customer_list',
                'label': _('عملاء CRM'),
                'url': 'crm:customer_list',
                'icon': 'bi-people',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'crm_customer_create',
                'label': _('عميل CRM جديد'),
                'url': 'crm:customer_create',
                'icon': 'bi-person-plus',
                'category': CATEGORY_MASTER,
                'permission': 'add',
            },
            
            # === تقارير ===
            {
                'id': 'crm_reports_dashboard',
                'label': _('لوحة التقارير'),
                'url': 'crm:reports_dashboard',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'crm_source_conversions_report',
                'label': _('تقرير التحويلات حسب المصدر'),
                'url': 'crm:source_conversions_report',
                'icon': 'bi-funnel',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'crm_commissions_report',
                'label': _('تقرير العمولات'),
                'url': 'crm:commissions_report',
                'icon': 'bi-currency-dollar',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            
            # === السوشيال ميديا و AI ===
            {
                'id': 'social_dashboard',
                'label': _('لوحة السوشيال ميديا'),
                'url': 'whatsapp_ai_web:dashboard',
                'icon': 'bi-robot',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'social_conversations',
                'label': _('المحادثات'),
                'url': 'whatsapp_ai_web:conversations_list',
                'icon': 'bi-chat-dots',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'social_customers',
                'label': _('عملاء السوشيال'),
                'url': 'whatsapp_ai_web:customers_list',
                'icon': 'bi-person-badge',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'social_opportunities',
                'label': _('فرص السوشيال'),
                'url': 'whatsapp_ai_web:opportunities_list',
                'icon': 'bi-graph-up-arrow',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'social_products',
                'label': _('قاعدة معرفة المنتجات'),
                'url': 'whatsapp_ai_web:products_knowledge',
                'icon': 'bi-box-seam',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'social_settings',
                'label': _('إعدادات المنصات'),
                'url': 'whatsapp_ai_web:platform_settings',
                'icon': 'bi-gear',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'social_analytics',
                'label': _('تحليلات السوشيال'),
                'url': 'whatsapp_ai_web:analytics',
                'icon': 'bi-bar-chart-line',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'production': {
        'id': 'production',
        'label': _('الإنتاج'),
        'icon': 'bi-gear-wide-connected',
        'order': 9,
        'module': 'production',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'production_dashboard',
                'label': _('لوحة الإنتاج'),
                'url': 'production:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'production_orders',
                'label': _('أوامر الإنتاج'),
                'url': 'production:orders_list',
                'icon': 'bi-list-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'production_work_centers',
                'label': _('مراكز العمل'),
                'url': 'production:work_centers_list',
                'icon': 'bi-building',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'production_quality',
                'label': _('إدارة الجودة'),
                'url': 'production:quality_dashboard',
                'icon': 'bi-patch-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'production_stages',
                'label': _('مراحل الإنتاج'),
                'url': 'production:stages_list',
                'icon': 'bi-layers',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'production_time_motion',
                'label': _('تحليل الوقت والحركة'),
                'url': 'production:time_motion',
                'icon': 'bi-stopwatch',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'production_safety',
                'label': _('دليل السلامة'),
                'url': 'production:safety',
                'icon': 'bi-shield-check',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            
            # === تقارير ===
            {
                'id': 'production_cost_analysis',
                'label': _('تحليل التكاليف'),
                'url': 'production:cost_analysis',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'production_product_costing',
                'label': _('تكلفة المنتج'),
                'url': 'production:product_costing',
                'icon': 'bi-calculator',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'maintenance': {
        'id': 'maintenance',
        'label': _('الصيانة'),
        'icon': 'bi-tools',
        'order': 10,
        'module': 'maintenance',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'maintenance_dashboard',
                'label': _('لوحة الصيانة'),
                'url': 'maintenance:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'maintenance_request_list',
                'label': _('طلبات الصيانة'),
                'url': 'maintenance:maintenance_request_list',
                'icon': 'bi-clipboard-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'maintenance_schedule_list',
                'label': _('جدولة الصيانة'),
                'url': 'maintenance:maintenance_schedule_list',
                'icon': 'bi-calendar-event',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'maintenance_record_list',
                'label': _('سجلات الصيانة'),
                'url': 'maintenance:maintenance_record_list',
                'icon': 'bi-journal-text',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'maintenance_machine_list',
                'label': _('الماكينات'),
                'url': 'maintenance:machine_list',
                'icon': 'bi-cpu',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'maintenance_spare_part_list',
                'label': _('قطع الغيار'),
                'url': 'maintenance:spare_part_list',
                'icon': 'bi-gear',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
        ]
    },
    
    'fleet': {
        'id': 'fleet',
        'label': _('الأسطول'),
        'icon': 'bi-truck',
        'order': 11,
        'module': 'fleet',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'fleet_dashboard',
                'label': _('لوحة الأسطول'),
                'url': 'fleet:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'fleet_trip_list',
                'label': _('الرحلات'),
                'url': 'fleet:trip_list',
                'icon': 'bi-signpost',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'fleet_maintenance_list',
                'label': _('صيانة المركبات'),
                'url': 'fleet:maintenance_list',
                'icon': 'bi-wrench',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'fleet_expense_list',
                'label': _('مصروفات المركبات'),
                'url': 'fleet:expense_list',
                'icon': 'bi-cash',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'fleet_vehicle_list',
                'label': _('المركبات'),
                'url': 'fleet:vehicle_list',
                'icon': 'bi-truck',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'fleet_driver_list',
                'label': _('السائقون'),
                'url': 'fleet:driver_list',
                'icon': 'bi-person',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'fleet_documents_upload',
                'label': _('مستندات المركبات'),
                'url': 'fleet:documents_upload',
                'icon': 'bi-file-earmark',
                'category': CATEGORY_MASTER,
                'permission': 'add',
            },
            
            # === تقارير ===
            {
                'id': 'fleet_driver_performance',
                'label': _('أداء السائقين'),
                'url': 'fleet:driver_performance',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'showrooms': {
        'id': 'showrooms',
        'label': _('المعارض'),
        'icon': 'bi-shop-window',
        'order': 12,
        'module': 'showrooms',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'showrooms_list',
                'label': _('المعارض'),
                'url': 'showrooms:list',
                'icon': 'bi-shop',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'showrooms_employees',
                'label': _('موظفو المعارض'),
                'url': 'showrooms:employees',
                'icon': 'bi-people',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تقارير ===
            {
                'id': 'showrooms_kpis',
                'label': _('مؤشرات الأداء'),
                'url': 'showrooms:kpis',
                'icon': 'bi-speedometer',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'showrooms_pnl',
                'label': _('الأرباح والخسائر'),
                'url': 'showrooms:pnl',
                'icon': 'bi-graph-up-arrow',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    # ===============================================
    # نظام الشحن (Shipping)
    # ===============================================
    'shipping': {
        'id': 'shipping',
        'label': _('الشحن'),
        'icon': 'bi-truck',
        'order': 13,
        'module': 'shipping',
        'permissions': ['view', 'add', 'change', 'delete'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'shipping_dashboard',
                'label': _('لوحة الشحن'),
                'url': 'shipping:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'shipping_shipments',
                'label': _('الشحنات'),
                'url': 'shipping:shipment_list',
                'icon': 'bi-box-seam',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'shipping_pickups',
                'label': _('طلبات الاستلام'),
                'url': 'shipping:pickup_list',
                'icon': 'bi-collection',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'shipping_track',
                'label': _('تتبع الشحنات'),
                'url': 'shipping:track_shipment',
                'icon': 'bi-geo-alt',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'shipping_invoices',
                'label': _('فواتير الشحن'),
                'url': 'shipping:invoice_list',
                'icon': 'bi-receipt',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'shipping_companies',
                'label': _('شركات الشحن'),
                'url': 'shipping:company_list',
                'icon': 'bi-building',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'shipping_zones',
                'label': _('مناطق الشحن'),
                'url': 'shipping:zone_list',
                'icon': 'bi-map',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'shipping_rates',
                'label': _('تعريفات الأسعار'),
                'url': 'shipping:rate_list',
                'icon': 'bi-currency-dollar',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            
            # === تقارير ===
            {
                'id': 'shipping_reports',
                'label': _('تقارير الشحن'),
                'url': 'shipping:reports_dashboard',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'shipping_cod_report',
                'label': _('تقرير الدفع عند الاستلام'),
                'url': 'shipping:cod_report',
                'icon': 'bi-cash-coin',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    # ===============================================
    # الخدمات الإلكترونية (E-Services)
    # ===============================================
    'eservices': {
        'id': 'eservices',
        'label': _('الخدمات الإلكترونية'),
        'icon': 'bi-globe',
        'order': 14,
        'module': 'eservices',
        'permissions': ['view', 'add', 'change', 'delete'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'eservices_dashboard',
                'label': _('لوحة الخدمات'),
                'url': 'eservices:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'eservices_recharge',
                'label': _('شحن الرصيد'),
                'url': 'eservices:recharge_dashboard',
                'icon': 'bi-phone',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'eservices_bills',
                'label': _('دفع الفواتير'),
                'url': 'eservices:bill_dashboard',
                'icon': 'bi-receipt-cutoff',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'eservices_transfer',
                'label': _('تحويل الأموال'),
                'url': 'eservices:transfer_dashboard',
                'icon': 'bi-arrow-left-right',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'eservices_transactions',
                'label': _('المعاملات'),
                'url': 'eservices:transaction_list',
                'icon': 'bi-list-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'eservices_categories',
                'label': _('الفئات'),
                'url': 'eservices:category_list',
                'icon': 'bi-collection',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'eservices_providers',
                'label': _('مزودي الخدمات'),
                'url': 'eservices:provider_list',
                'icon': 'bi-building',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'eservices_services',
                'label': _('الخدمات'),
                'url': 'eservices:service_list',
                'icon': 'bi-grid-3x3-gap',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'eservices_operators',
                'label': _('المشغلين'),
                'url': 'eservices:operator_list',
                'icon': 'bi-broadcast',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            
            # === تقارير ===
            {
                'id': 'eservices_reports',
                'label': _('تقارير الخدمات'),
                'url': 'eservices:reports_dashboard',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'eservices_revenue',
                'label': _('تقرير الإيرادات'),
                'url': 'eservices:revenue_report',
                'icon': 'bi-cash-stack',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'reports': {
        'id': 'reports',
        'label': _('التقارير'),
        'icon': 'bi-graph-up-arrow',
        'order': 15,
        'module': 'reports',
        'permissions': ['view'],
        'items': [
            # === لوحات عامة ===
            {
                'id': 'reports_dashboard',
                'label': _('لوحة التقارير'),
                'url': 'reports:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'reports_sales',
                'label': _('تقرير المبيعات'),
                'url': 'reports:sales_report',
                'icon': 'bi-cart-check',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'reports_purchases',
                'label': _('تقرير المشتريات'),
                'url': 'reports:purchases_report',
                'icon': 'bi-bag-plus',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'reports_inventory',
                'label': _('تقرير المخزون'),
                'url': 'reports:inventory_report',
                'icon': 'bi-boxes',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'users': {
        'id': 'users',
        'label': _('إدارة المستخدمين'),
        'icon': 'bi-shield-lock',
        'order': 16,
        'module': 'users',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'users_dashboard',
                'label': _('لوحة المستخدمين'),
                'url': 'users:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'users_list',
                'label': _('قائمة المستخدمين'),
                'url': 'users:list',
                'icon': 'bi-people',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'users_sessions',
                'label': _('جلسات المستخدمين'),
                'url': 'users:sessions',
                'icon': 'bi-person-circle',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات ===
            {
                'id': 'users_permissions_manager',
                'label': _('إدارة الصلاحيات'),
                'url': 'users:permissions_manager',
                'icon': 'bi-key',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            
            # === تقارير ===
            {
                'id': 'users_activity_log',
                'label': _('سجل الأنشطة'),
                'url': 'users:activity_log',
                'icon': 'bi-activity',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
            {
                'id': 'users_security_alerts',
                'label': _('التنبيهات الأمنية'),
                'url': 'users:security_alerts',
                'icon': 'bi-exclamation-triangle',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'online_store': {
        'id': 'online_store',
        'label': _('المتجر الإلكتروني'),
        'icon': 'bi-shop',
        'order': 17,
        'module': 'ecommerce',
        'permissions': ['view', 'add', 'change'],
        'items': [
            # === عمليات يومية ===
            {
                'id': 'store_dashboard',
                'label': _('لوحة تحكم المتجر'),
                'url': 'ecommerce:admin_dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_orders',
                'label': _('الطلبات'),
                'url': 'ecommerce:admin_orders',
                'icon': 'bi-cart-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_products',
                'label': _('المنتجات'),
                'url': 'ecommerce:admin_products',
                'icon': 'bi-box-seam',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_categories',
                'label': _('التصنيفات'),
                'url': 'ecommerce:admin_categories',
                'icon': 'bi-folder',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_brands',
                'label': _('العلامات التجارية'),
                'url': 'ecommerce:admin_brands',
                'icon': 'bi-award',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_reviews',
                'label': _('التقييمات'),
                'url': 'ecommerce:admin_reviews',
                'icon': 'bi-star',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'store_coupons',
                'label': _('الكوبونات'),
                'url': 'ecommerce:admin_coupons',
                'icon': 'bi-ticket-perforated',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            
            # === تعريفات وإعدادات ===
            {
                'id': 'store_settings',
                'label': _('إعدادات المتجر'),
                'url': 'ecommerce:admin_settings',
                'icon': 'bi-gear',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'store_payment_gateways',
                'label': _('بوابات الدفع'),
                'url': 'ecommerce:admin_payment_gateways',
                'icon': 'bi-credit-card',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'store_shipping_companies',
                'label': _('شركات الشحن'),
                'url': 'ecommerce:admin_shipping_companies',
                'icon': 'bi-truck',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'store_social_media',
                'label': _('التواصل الاجتماعي'),
                'url': 'ecommerce:admin_social_media',
                'icon': 'bi-share',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'store_banners',
                'label': _('البانرات والإعلانات'),
                'url': 'ecommerce:admin_banners',
                'icon': 'bi-images',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            {
                'id': 'store_page_content',
                'label': _('محتوى الصفحات'),
                'url': 'ecommerce:admin_page_content',
                'icon': 'bi-file-text',
                'category': CATEGORY_MASTER,
                'permission': 'change',
            },
            
            # === الروابط السريعة ===
            {
                'id': 'store_view',
                'label': _('عرض المتجر'),
                'url': 'ecommerce:store_home',
                'icon': 'bi-globe',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'external': True,
            },
        ]
    },
    

    'branches': {
        'id': 'branches',
        'label': _('إدارة الفروع'),
        'icon': 'bi-building',
        'order': 13,
        'module': 'branches',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'branches_dashboard',
                'label': _('لوحة تحكم الفروع'),
                'url': 'branches:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'branches_list',
                'label': _('قائمة الفروع'),
                'url': 'branches:branch_list',
                'icon': 'bi-building',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'branches_transfers',
                'label': _('تحويلات الفروع'),
                'url': 'branches:transfer_list',
                'icon': 'bi-arrow-left-right',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },
    
    'bank_reconciliation': {
        'id': 'bank_reconciliation',
        'label': _('مطابقة البنوك'),
        'icon': 'bi-bank',
        'order': 14,
        'module': 'bank_reconciliation',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'bank_rec_dashboard',
                'label': _('لوحة المطابقة'),
                'url': 'bank_reconciliation:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'bank_statements',
                'label': _('كشوف الحساب'),
                'url': 'bank_reconciliation:statement_list',
                'icon': 'bi-file-earmark-text',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },
    
    'budgeting': {
        'id': 'budgeting',
        'label': _('الميزانيات'),
        'icon': 'bi-pie-chart',
        'order': 15,
        'module': 'budgeting',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'budgeting_dashboard',
                'label': _('لوحة الميزانيات'),
                'url': 'budgeting:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'budgets_list',
                'label': _('قائمة الميزانيات'),
                'url': 'budgeting:budget_list',
                'icon': 'bi-list-ul',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'variance_report',
                'label': _('تقرير الانحرافات'),
                'url': 'budgeting:variance_report',
                'icon': 'bi-graph-up-arrow',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    'quality_control': {
        'id': 'quality_control',
        'label': _('إدارة الجودة'),
        'icon': 'bi-shield-check',
        'order': 16,
        'module': 'quality_control',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'qc_dashboard',
                'label': _('لوحة الجودة'),
                'url': 'quality_control:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'qc_inspections',
                'label': _('فحوصات الجودة'),
                'url': 'quality_control:inspection_list',
                'icon': 'bi-clipboard-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'qc_issues',
                'label': _('مشاكل الجودة'),
                'url': 'quality_control:issue_list',
                'icon': 'bi-exclamation-triangle',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },
    
    'loyalty': {
        'id': 'loyalty',
        'label': _('برنامج الولاء'),
        'icon': 'bi-gift',
        'order': 17,
        'module': 'loyalty',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'loyalty_dashboard',
                'label': _('لوحة الولاء'),
                'url': 'loyalty:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'loyalty_members',
                'label': _('الأعضاء'),
                'url': 'loyalty:member_list',
                'icon': 'bi-people',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'loyalty_rewards',
                'label': _('المكافآت'),
                'url': 'loyalty:reward_list',
                'icon': 'bi-gift',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
        ]
    },
    
    'helpdesk': {
        'id': 'helpdesk',
        'label': _('مركز الدعم'),
        'icon': 'bi-headset',
        'order': 18,
        'module': 'helpdesk',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'helpdesk_dashboard',
                'label': _('لوحة الدعم'),
                'url': 'helpdesk:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'helpdesk_tickets',
                'label': _('التذاكر'),
                'url': 'helpdesk:ticket_list',
                'icon': 'bi-ticket',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
            {
                'id': 'helpdesk_new_ticket',
                'label': _('تذكرة جديدة'),
                'url': 'helpdesk:ticket_create',
                'icon': 'bi-plus-circle',
                'category': CATEGORY_DAILY,
                'permission': 'add',
            },
            {
                'id': 'helpdesk_kb',
                'label': _('قاعدة المعرفة'),
                'url': 'helpdesk:knowledge_base',
                'icon': 'bi-book',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },
    
    # ===============================================
    # بناء المراتب (Mattress Builder)
    # ===============================================
    'mattress_builder': {
        'id': 'mattress_builder',
        'label': _('بناء المراتب'),
        'icon': 'bi-layers-half',
        'order': 20,
        'module': 'mattress_builder',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'mattress_home',
                'label': _('لوحة بناء المراتب'),
                'url': 'ecommerce:mattress_builder:home',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الأصول الثابتة (Fixed Assets)
    # ===============================================
    'fixed_assets': {
        'id': 'fixed_assets',
        'label': _('الأصول الثابتة'),
        'icon': 'bi-building',
        'order': 21,
        'module': 'fixed_assets',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'fixed_assets_list',
                'label': _('قائمة الأصول'),
                'url': 'fixed_assets:asset_list',
                'icon': 'bi-list-ul',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة الخزينة (Treasury Management)
    # ===============================================
    'treasury_management': {
        'id': 'treasury_management',
        'label': _('إدارة الخزينة'),
        'icon': 'bi-safe2',
        'order': 22,
        'module': 'treasury_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'treasury_dashboard',
                'label': _('لوحة الخزينة'),
                'url': 'treasury_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المشاريع (Projects)
    # ===============================================
    'projects': {
        'id': 'projects',
        'label': _('المشاريع'),
        'icon': 'bi-kanban',
        'order': 23,
        'module': 'projects',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'projects_dashboard',
                'label': _('لوحة المشاريع'),
                'url': 'projects:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المهام (Tasks)
    # ===============================================
    'tasks': {
        'id': 'tasks',
        'label': _('المهام'),
        'icon': 'bi-check2-square',
        'order': 24,
        'module': 'tasks',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'tasks_dashboard',
                'label': _('لوحة المهام'),
                'url': 'tasks:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الضرائب (Taxes)
    # ===============================================
    'taxes': {
        'id': 'taxes',
        'label': _('الضرائب'),
        'icon': 'bi-percent',
        'order': 25,
        'module': 'taxes',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'taxes_dashboard',
                'label': _('لوحة الضرائب'),
                'url': 'taxes:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # نظام زاتكا (ZATCA)
    # ===============================================
    'zatca': {
        'id': 'zatca',
        'label': _('نظام زاتكا'),
        'icon': 'bi-qr-code',
        'order': 26,
        'module': 'zatca',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'zatca_dashboard',
                'label': _('لوحة زاتكا'),
                'url': 'zatca:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الأقساط (Installments)
    # ===============================================
    'installments': {
        'id': 'installments',
        'label': _('الأقساط'),
        'icon': 'bi-calendar-check',
        'order': 27,
        'module': 'installments',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'installments_dashboard',
                'label': _('لوحة الأقساط'),
                'url': 'installments:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة العقود (Contract Management)
    # ===============================================
    'contract_management': {
        'id': 'contract_management',
        'label': _('إدارة العقود'),
        'icon': 'bi-file-earmark-text',
        'order': 28,
        'module': 'contract_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'contract_dashboard',
                'label': _('لوحة العقود'),
                'url': 'contract_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المناقصات (Tender Bidding)
    # ===============================================
    'tender_bidding': {
        'id': 'tender_bidding',
        'label': _('المناقصات'),
        'icon': 'bi-hammer',
        'order': 29,
        'module': 'tender_bidding',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'tender_dashboard',
                'label': _('لوحة المناقصات'),
                'url': 'tender_bidding:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الحملات التسويقية (Marketing Campaigns)
    # ===============================================
    'marketing_campaigns': {
        'id': 'marketing_campaigns',
        'label': _('الحملات التسويقية'),
        'icon': 'bi-megaphone',
        'order': 30,
        'module': 'marketing_campaigns',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'marketing_dashboard',
                'label': _('لوحة التسويق'),
                'url': 'marketing_campaigns:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الطباعة (Printing)
    # ===============================================
    'printing': {
        'id': 'printing',
        'label': _('الطباعة'),
        'icon': 'bi-printer',
        'order': 31,
        'module': 'printing',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'printing_dashboard',
                'label': _('لوحة الطباعة'),
                'url': 'printing:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # ذكاء الأعمال (Business Intelligence)
    # ===============================================
    'business_intelligence': {
        'id': 'business_intelligence',
        'label': _('ذكاء الأعمال'),
        'icon': 'bi-bar-chart-line',
        'order': 32,
        'module': 'business_intelligence',
        'permissions': ['view'],
        'items': [
            {
                'id': 'bi_home',
                'label': _('لوحة ذكاء الأعمال'),
                'url': 'business_intelligence:home',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # تحليلات الذكاء الاصطناعي (AI Analytics)
    # ===============================================
    'ai_analytics': {
        'id': 'ai_analytics',
        'label': _('تحليلات الذكاء الاصطناعي'),
        'icon': 'bi-robot',
        'order': 33,
        'module': 'ai_analytics',
        'permissions': ['view'],
        'items': [
            {
                'id': 'ai_analytics_dashboard',
                'label': _('لوحة تحليلات الذكاء'),
                'url': 'ai_analytics:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المساعد الذكي (AI Assistant)
    # ===============================================
    'ai_assistant': {
        'id': 'ai_assistant',
        'label': _('المساعد الذكي'),
        'icon': 'bi-chat-dots',
        'order': 34,
        'module': 'ai_assistant',
        'permissions': ['view'],
        'items': [
            {
                'id': 'ai_assistant_dashboard',
                'label': _('المساعد الذكي'),
                'url': 'ai_assistant:admin_dashboard',
                'icon': 'bi-robot',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # CRM المتقدم (Advanced CRM)
    # ===============================================
    'advanced_crm': {
        'id': 'advanced_crm',
        'label': _('CRM المتقدم'),
        'icon': 'bi-people-fill',
        'order': 35,
        'module': 'advanced_crm',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'advanced_crm_dashboard',
                'label': _('لوحة CRM المتقدم'),
                'url': 'advanced_crm:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # منشئ التقارير (Report Builder)
    # ===============================================
    'report_builder': {
        'id': 'report_builder',
        'label': _('منشئ التقارير'),
        'icon': 'bi-wrench-adjustable',
        'order': 36,
        'module': 'report_builder',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'report_builder_dashboard',
                'label': _('منشئ التقارير'),
                'url': 'report_builder:dashboard',
                'icon': 'bi-bar-chart-steps',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة المخاطر (Risk Management)
    # ===============================================
    'risk_management': {
        'id': 'risk_management',
        'label': _('إدارة المخاطر'),
        'icon': 'bi-exclamation-diamond',
        'order': 37,
        'module': 'risk_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'risk_dashboard',
                'label': _('لوحة المخاطر'),
                'url': 'risk_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة الضمانات (Warranty Management)
    # ===============================================
    'warranty_management': {
        'id': 'warranty_management',
        'label': _('إدارة الضمانات'),
        'icon': 'bi-shield-check',
        'order': 38,
        'module': 'warranty_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'warranty_dashboard',
                'label': _('لوحة الضمانات'),
                'url': 'warranty_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة الشكاوى (Complaint Management)
    # ===============================================
    'complaint_management': {
        'id': 'complaint_management',
        'label': _('إدارة الشكاوى'),
        'icon': 'bi-chat-square-text',
        'order': 39,
        'module': 'complaint_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'complaint_dashboard',
                'label': _('لوحة الشكاوى'),
                'url': 'complaint_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الاشتراكات (Subscriptions)
    # ===============================================
    'subscriptions': {
        'id': 'subscriptions',
        'label': _('الاشتراكات'),
        'icon': 'bi-credit-card-2-front',
        'order': 40,
        'module': 'subscriptions',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'subscriptions_plans',
                'label': _('خطط الاشتراك'),
                'url': 'subscriptions:plans_list',
                'icon': 'bi-list-stars',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الدردشة الداخلية (Internal Chat)
    # ===============================================
    'internal_chat': {
        'id': 'internal_chat',
        'label': _('الدردشة الداخلية'),
        'icon': 'bi-chat-left-dots',
        'order': 41,
        'module': 'internal_chat',
        'permissions': ['view'],
        'items': [
            {
                'id': 'internal_chat_home',
                'label': _('الدردشة الداخلية'),
                'url': 'internal_chat:home',
                'icon': 'bi-chat-dots',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # تكامل واتساب (WhatsApp Integration)
    # ===============================================
    'whatsapp_integration': {
        'id': 'whatsapp_integration',
        'label': _('تكامل واتساب'),
        'icon': 'bi-whatsapp',
        'order': 42,
        'module': 'whatsapp_integration',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'whatsapp_dashboard',
                'label': _('لوحة واتساب'),
                'url': 'whatsapp_integration:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # تكامل WooCommerce
    # ===============================================
    'woocommerce_integration': {
        'id': 'woocommerce_integration',
        'label': _('تكامل WooCommerce'),
        'icon': 'bi-bag-heart',
        'order': 43,
        'module': 'woocommerce_integration',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'woocommerce_dashboard',
                'label': _('لوحة WooCommerce'),
                'url': 'woocommerce_integration:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # التوقيعات الرقمية (Digital Signatures)
    # ===============================================
    'digital_signatures': {
        'id': 'digital_signatures',
        'label': _('التوقيعات الرقمية'),
        'icon': 'bi-pen',
        'order': 44,
        'module': 'digital_signatures',
        'permissions': ['view', 'add'],
        'items': [
            {
                'id': 'digital_signatures_my',
                'label': _('توقيعاتي'),
                'url': 'digital_signatures:my_signature',
                'icon': 'bi-vector-pen',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # التسعير الذكي (Smart Pricing)
    # ===============================================
    'smart_pricing': {
        'id': 'smart_pricing',
        'label': _('التسعير الذكي'),
        'icon': 'bi-tags',
        'order': 45,
        'module': 'smart_pricing',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'smart_pricing_dashboard',
                'label': _('لوحة التسعير الذكي'),
                'url': 'smart_pricing:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # التنبؤ بالمبيعات (Sales Forecasting)
    # ===============================================
    'sales_forecasting': {
        'id': 'sales_forecasting',
        'label': _('التنبؤ بالمبيعات'),
        'icon': 'bi-graph-up-arrow',
        'order': 46,
        'module': 'sales_forecasting',
        'permissions': ['view'],
        'items': [
            {
                'id': 'sales_forecasting_dashboard',
                'label': _('لوحة التنبؤ'),
                'url': 'sales_forecasting:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة الامتثال (Compliance Management)
    # ===============================================
    'compliance_management': {
        'id': 'compliance_management',
        'label': _('إدارة الامتثال'),
        'icon': 'bi-clipboard2-check',
        'order': 47,
        'module': 'compliance_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'compliance_dashboard',
                'label': _('لوحة الامتثال'),
                'url': 'compliance_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الصادرات والتصدير (Exports)
    # ===============================================
    'exports': {
        'id': 'exports',
        'label': _('تصدير البيانات'),
        'icon': 'bi-file-earmark-arrow-down',
        'order': 48,
        'module': 'exports',
        'permissions': ['view'],
        'items': [
            {
                'id': 'exports_list',
                'label': _('قائمة الصادرات'),
                'url': 'exports:export_list',
                'icon': 'bi-download',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المدفوعات (Payments)
    # ===============================================
    'payments': {
        'id': 'payments',
        'label': _('المدفوعات'),
        'icon': 'bi-cash-coin',
        'order': 49,
        'module': 'payments',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'payments_dashboard',
                'label': _('لوحة المدفوعات'),
                'url': 'payments:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الحضور والانصراف المستقل (Attendance)
    # ===============================================
    'attendance': {
        'id': 'attendance',
        'label': _('الحضور والانصراف'),
        'icon': 'bi-fingerprint',
        'order': 50,
        'module': 'attendance',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'attendance_dashboard',
                'label': _('لوحة الحضور'),
                'url': 'attendance:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # التكامل البنكي (Bank Integration)
    # ===============================================
    'bank_integration': {
        'id': 'bank_integration',
        'label': _('التكامل البنكي'),
        'icon': 'bi-bank2',
        'order': 51,
        'module': 'bank_integration',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'bank_integration_dashboard',
                'label': _('لوحة التكامل البنكي'),
                'url': 'bank_integration:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # النسخ الاحتياطي السحابي (Cloud Backup)
    # ===============================================
    'cloud_backup': {
        'id': 'cloud_backup',
        'label': _('النسخ الاحتياطي السحابي'),
        'icon': 'bi-cloud-arrow-up',
        'order': 52,
        'module': 'cloud_backup',
        'permissions': ['view', 'add'],
        'items': [
            {
                'id': 'cloud_backup_dashboard',
                'label': _('لوحة النسخ الاحتياطي'),
                'url': 'cloud_backup:dashboard',
                'icon': 'bi-cloud-check',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # نظام المحتوى (CMS)
    # ===============================================
    'cms': {
        'id': 'cms',
        'label': _('إدارة المحتوى'),
        'icon': 'bi-file-richtext',
        'order': 53,
        'module': 'cms',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'cms_dashboard',
                'label': _('لوحة المحتوى'),
                'url': 'cms:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المستندات التشاركية (Collaborative Docs)
    # ===============================================
    'collaborative_docs': {
        'id': 'collaborative_docs',
        'label': _('المستندات التشاركية'),
        'icon': 'bi-file-earmark-text',
        'order': 54,
        'module': 'collaborative_docs',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'collaborative_docs_dashboard',
                'label': _('لوحة المستندات'),
                'url': 'collaborative_docs:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # تحليل المنافسين (Competitive Intelligence)
    # ===============================================
    'competitive_intelligence': {
        'id': 'competitive_intelligence',
        'label': _('تحليل المنافسين'),
        'icon': 'bi-binoculars',
        'order': 55,
        'module': 'competitive_intelligence',
        'permissions': ['view'],
        'items': [
            {
                'id': 'competitive_intel_dashboard',
                'label': _('لوحة تحليل المنافسين'),
                'url': 'competitive_intelligence:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المقاولات (Contracting)
    # ===============================================
    'contracting': {
        'id': 'contracting',
        'label': _('المقاولات'),
        'icon': 'bi-building-gear',
        'order': 56,
        'module': 'contracting',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'contracting_index',
                'label': _('لوحة المقاولات'),
                'url': 'contracting:index',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة المراسلات (Correspondence Management)
    # ===============================================
    'correspondence_management': {
        'id': 'correspondence_management',
        'label': _('إدارة المراسلات'),
        'icon': 'bi-envelope-open',
        'order': 57,
        'module': 'correspondence_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'correspondence_dashboard',
                'label': _('لوحة المراسلات'),
                'url': 'correspondence_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # لوحات التحكم المخصصة (Custom Dashboard)
    # ===============================================
    'custom_dashboard': {
        'id': 'custom_dashboard',
        'label': _('لوحات مخصصة'),
        'icon': 'bi-layout-wtf',
        'order': 58,
        'module': 'custom_dashboard',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'custom_dashboard_main',
                'label': _('لوحات التحكم المخصصة'),
                'url': 'custom_dashboard:dashboard',
                'icon': 'bi-grid-1x2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # ربحية العملاء (Customer Profitability)
    # ===============================================
    'customer_profitability': {
        'id': 'customer_profitability',
        'label': _('ربحية العملاء'),
        'icon': 'bi-person-check',
        'order': 59,
        'module': 'customer_profitability',
        'permissions': ['view'],
        'items': [
            {
                'id': 'customer_profitability_dashboard',
                'label': _('لوحة ربحية العملاء'),
                'url': 'customer_profitability:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة الطاقة (Energy Management)
    # ===============================================
    'energy_management': {
        'id': 'energy_management',
        'label': _('إدارة الطاقة'),
        'icon': 'bi-lightning-charge',
        'order': 60,
        'module': 'energy_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'energy_dashboard',
                'label': _('لوحة إدارة الطاقة'),
                'url': 'energy_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الملكية الفكرية (Intellectual Property)
    # ===============================================
    'intellectual_property': {
        'id': 'intellectual_property',
        'label': _('الملكية الفكرية'),
        'icon': 'bi-lightbulb',
        'order': 61,
        'module': 'intellectual_property',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'intellectual_property_dashboard',
                'label': _('لوحة الملكية الفكرية'),
                'url': 'intellectual_property:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # إدارة التراخيص (License Management)
    # ===============================================
    'license_management': {
        'id': 'license_management',
        'label': _('إدارة التراخيص'),
        'icon': 'bi-award',
        'order': 62,
        'module': 'license_management',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'license_management_dashboard',
                'label': _('لوحة التراخيص'),
                'url': 'license_management:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # مراقبة النظام (Monitoring)
    # ===============================================
    'monitoring': {
        'id': 'monitoring',
        'label': _('مراقبة النظام'),
        'icon': 'bi-activity',
        'order': 63,
        'module': 'monitoring',
        'permissions': ['view'],
        'items': [
            {
                'id': 'monitoring_anomaly_dashboard',
                'label': _('لوحة المراقبة'),
                'url': 'monitoring:anomaly_dashboard',
                'icon': 'bi-graph-up',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الساعة الذكية (Smartwatch)
    # ===============================================
    'smartwatch': {
        'id': 'smartwatch',
        'label': _('الساعة الذكية'),
        'icon': 'bi-smartwatch',
        'order': 64,
        'module': 'smartwatch',
        'permissions': ['view'],
        'items': [
            {
                'id': 'smartwatch_dashboard',
                'label': _('لوحة الساعة الذكية'),
                'url': 'smartwatch:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # مكالمات الفيديو (Video Calls)
    # ===============================================
    'video_calls': {
        'id': 'video_calls',
        'label': _('مكالمات الفيديو'),
        'icon': 'bi-camera-video',
        'order': 65,
        'module': 'video_calls',
        'permissions': ['view'],
        'items': [
            {
                'id': 'video_calls_dashboard',
                'label': _('لوحة مكالمات الفيديو'),
                'url': 'video_calls:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # المساعد الصوتي (Voice Assistant)
    # ===============================================
    'voice_assistant': {
        'id': 'voice_assistant',
        'label': _('المساعد الصوتي'),
        'icon': 'bi-mic',
        'order': 66,
        'module': 'voice_assistant',
        'permissions': ['view'],
        'items': [
            {
                'id': 'voice_assistant_dashboard',
                'label': _('المساعد الصوتي'),
                'url': 'voice_assistant:dashboard',
                'icon': 'bi-mic-fill',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # واتساب AI (WhatsApp AI)
    # ===============================================
    'whatsapp_ai': {
        'id': 'whatsapp_ai',
        'label': _('واتساب AI'),
        'icon': 'bi-robot',
        'order': 67,
        'module': 'whatsapp_ai',
        'permissions': ['view', 'add', 'change'],
        'items': [
            {
                'id': 'whatsapp_ai_dashboard',
                'label': _('لوحة واتساب AI'),
                'url': 'whatsapp_ai_dashboard:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الإشعارات المتقدمة (Advanced Notifications)
    # ===============================================
    'advanced_notifications': {
        'id': 'advanced_notifications',
        'label': _('الإشعارات المتقدمة'),
        'icon': 'bi-bell-fill',
        'order': 68,
        'module': 'advanced_notifications',
        'permissions': ['view', 'change'],
        'items': [
            {
                'id': 'advanced_notifications_dashboard',
                'label': _('لوحة الإشعارات المتقدمة'),
                'url': 'advanced_notifications:dashboard',
                'icon': 'bi-speedometer2',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    # ===============================================
    # الوصول السريع (Quick Access)
    # ===============================================
    'quick_access': {
        'id': 'quick_access',
        'label': _('الوصول السريع'),
        'icon': 'bi-lightning',
        'order': 69,
        'module': 'quick_access',
        'permissions': ['view'],
        'items': [
            {
                'id': 'quick_access_dashboard',
                'label': _('لوحة الوصول السريع'),
                'url': 'quick_access:dashboard',
                'icon': 'bi-grid-3x3',
                'category': CATEGORY_DAILY,
                'permission': 'view',
            },
        ]
    },

    'settings': {
        'id': 'settings',
        'label': _('الإعدادات'),
        'icon': 'bi-gear',
        'order': 99,
        'module': None,
        'items': [
            {
                'id': 'company_settings',
                'label': _('إعدادات النظام'),
                'url': 'core:company_settings',
                'icon': 'bi-gear',
                'category': CATEGORY_MASTER,
                'permission': 'view',
                'module_permission': ('core', 'view'),
            },
            {
                'id': 'data_import',
                'label': _('استيراد البيانات'),
                'url': 'data_import:dashboard',
                'icon': 'bi-file-earmark-excel',
                'category': CATEGORY_MASTER,
                'permission': 'view',
            },
            {
                'id': 'audit_logs',
                'label': _('سجلات التدقيق'),
                'url': 'core:audit_logs',
                'icon': 'bi-clipboard-data',
                'category': CATEGORY_REPORTS,
                'permission': 'view',
                'module_permission': ('core', 'view_auditlog'),
            },
        ]
    },
}


# ===============================================
# Helper Functions
# ===============================================

def get_sidebar_config():
    """
    Returns the complete sidebar configuration
    """
    return SIDEBAR_CONFIG


def get_category_label(category):
    """
    Returns the Arabic label for a category
    """
    labels = {
        CATEGORY_DAILY: _('عمليات يومية'),
        CATEGORY_MASTER: _('تعريفات وإعدادات'),
        CATEGORY_REPORTS: _('تقارير واستعلامات'),
    }
    return labels.get(category, category)


def get_sections_sorted():
    """
    Returns sections sorted by order
    """
    sections = list(SIDEBAR_CONFIG.values())
    sections.sort(key=lambda x: x.get('order', 999))
    return sections


def group_items_by_category(items):
    """
    Groups menu items by their category (daily, master, reports)
    Returns a dict: {category: [items]}
    Items are sorted by 'order' within each category.
    """
    grouped = {
        CATEGORY_DAILY: [],
        CATEGORY_MASTER: [],
        CATEGORY_REPORTS: [],
    }
    
    for item in items:
        category = item.get('category', CATEGORY_DAILY)
        if category in grouped:
            grouped[category].append(item)
    
    # Sort items within each category by order
    for category in grouped:
        grouped[category].sort(key=lambda x: x.get('order', 999))
    
    return grouped

