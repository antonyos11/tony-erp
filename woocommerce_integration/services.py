"""
Synchronization Services for WooCommerce Integration
Handles bi-directional sync between ERP and WooCommerce
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    WooCommerceConfig,
    ProductMapping,
    OrderMapping,
    CustomerMapping,
    SyncLog
)
from .woocommerce_client import WooCommerceClient, WooCommerceAPIError

from inventory.models import Product, Stock, Location
from sales.models import Invoice, InvoiceItem
from crm.models import Customer, CustomerType
from partners.models import Partner

User = get_user_model()
logger = logging.getLogger(__name__)


class SyncService:
    """Base sync service"""
    
    def __init__(self, config: WooCommerceConfig):
        self.config = config
        self.client = WooCommerceClient(
            store_url=config.store_url,
            consumer_key=config.consumer_key,
            consumer_secret=config.consumer_secret
        )
    
    def create_sync_log(self, sync_type: str) -> SyncLog:
        """Create sync log entry"""
        return SyncLog.objects.create(
            config=self.config,
            sync_type=sync_type,
            status='success',  # Will be updated
            started_at=timezone.now()
        )
    
    def complete_sync_log(self, log: SyncLog, status: str, message: str = '', error_details: str = ''):
        """Complete sync log with results"""
        log.status = status
        log.message = message
        log.error_details = error_details
        log.completed_at = timezone.now()
        log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
        log.save()


class ProductSyncService(SyncService):
    """Product synchronization service"""
    
    def push_product_to_woocommerce(self, product: Product) -> Tuple[bool, str]:
        """Push ERP product to WooCommerce"""
        try:
            # Check if already mapped
            mapping = ProductMapping.objects.filter(
                config=self.config,
                erp_product=product
            ).first()
            
            # Prepare product data
            woo_data = {
                'name': product.name,
                'sku': product.sku,
                'regular_price': str(product.price),
                'description': product.description or '',
                'manage_stock': True,
                'stock_quantity': self._get_product_stock(product),
                'status': 'publish' if product.is_active else 'draft',
            }
            
            if mapping:
                # Update existing
                result = self.client.update_product(mapping.woo_product_id, woo_data)
                mapping.last_synced = timezone.now()
                mapping.save()
            else:
                # Create new
                result = self.client.create_product(woo_data)
                ProductMapping.objects.create(
                    config=self.config,
                    erp_product=product,
                    woo_product_id=result['id'],
                    woo_sku=result.get('sku', ''),
                    last_synced=timezone.now()
                )
            
            return True, f"Product synced: {product.name}"
        
        except WooCommerceAPIError as e:
            logger.error(f"Failed to push product {product.id}: {str(e)}")
            return False, str(e)
    
    def pull_products_from_woocommerce(self) -> Tuple[int, int, str]:
        """Pull products from WooCommerce to ERP"""
        log = self.create_sync_log('product_pull')
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            page = 1
            while True:
                products = self.client.get_products(per_page=100, page=page)
                if not products:
                    break
                
                for woo_product in products:
                    try:
                        self._import_woo_product(woo_product)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        errors.append(f"Product {woo_product.get('id')}: {str(e)}")
                        logger.error(f"Failed to import product: {str(e)}")
                
                page += 1
            
            log.records_processed = success_count + fail_count
            log.records_success = success_count
            log.records_failed = fail_count
            self.complete_sync_log(
                log,
                'success' if fail_count == 0 else 'partial',
                f"Imported {success_count} products",
                '\n'.join(errors)
            )
            
            self.config.last_product_sync = timezone.now()
            self.config.save()
            
            return success_count, fail_count, '\n'.join(errors)
        
        except Exception as e:
            self.complete_sync_log(log, 'failed', error_details=str(e))
            raise
    
    def _import_woo_product(self, woo_product: Dict):
        """Import single WooCommerce product"""
        sku = woo_product.get('sku')
        if not sku:
            raise ValueError("Product has no SKU")
        
        # Find or create ERP product
        product, created = Product.objects.get_or_create(
            sku=sku,
            defaults={
                'name': woo_product['name'],
                'description': woo_product.get('description', ''),
                'price': Decimal(woo_product.get('regular_price', '0') or '0'),
                'is_active': woo_product.get('status') == 'publish',
            }
        )
        
        if not created:
            # Update existing
            product.name = woo_product['name']
            product.price = Decimal(woo_product.get('regular_price', '0') or '0')
            product.save()
        
        # Create or update mapping
        ProductMapping.objects.update_or_create(
            config=self.config,
            erp_product=product,
            defaults={
                'woo_product_id': woo_product['id'],
                'woo_sku': sku,
                'last_synced': timezone.now()
            }
        )
    
    def _get_product_stock(self, product: Product) -> int:
        """Get total stock for product"""
        if self.config.default_location:
            stock = Stock.objects.filter(
                product=product,
                location=self.config.default_location
            ).first()
            return int(stock.quantity) if stock else 0
        else:
            total = Stock.objects.filter(product=product).aggregate(
                total=models.Sum('quantity')
            )['total']
            return int(total) if total else 0
    
    def sync_inventory_to_woocommerce(self) -> Tuple[int, int]:
        """Sync inventory levels to WooCommerce"""
        log = self.create_sync_log('inventory_push')
        success_count = 0
        fail_count = 0
        
        try:
            mappings = ProductMapping.objects.filter(
                config=self.config,
                sync_enabled=True,
                sync_stock=True
            ).select_related('erp_product')
            
            for mapping in mappings:
                try:
                    stock_qty = self._get_product_stock(mapping.erp_product)
                    self.client.update_product_stock(mapping.woo_product_id, stock_qty)
                    mapping.last_synced = timezone.now()
                    mapping.save()
                    success_count += 1
                except WooCommerceAPIError as e:
                    fail_count += 1
                    logger.error(f"Failed to sync stock for {mapping.erp_product}: {str(e)}")
            
            log.records_processed = success_count + fail_count
            log.records_success = success_count
            log.records_failed = fail_count
            self.complete_sync_log(log, 'success' if fail_count == 0 else 'partial')
            
            self.config.last_inventory_sync = timezone.now()
            self.config.save()
            
            return success_count, fail_count
        
        except Exception as e:
            self.complete_sync_log(log, 'failed', error_details=str(e))
            raise


class OrderSyncService(SyncService):
    """Order synchronization service"""
    
    def pull_orders_from_woocommerce(self, since: Optional[datetime] = None) -> Tuple[int, int, str]:
        """Pull new orders from WooCommerce"""
        log = self.create_sync_log('order_pull')
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            # Get orders since last sync or specified date
            if since is None and self.config.last_order_sync:
                since = self.config.last_order_sync - timedelta(hours=1)  # 1 hour overlap
            
            filters = {}
            if since:
                filters['after'] = since.isoformat()
            
            page = 1
            while True:
                orders = self.client.get_orders(per_page=100, page=page, **filters)
                if not orders:
                    break
                
                for woo_order in orders:
                    try:
                        self._import_woo_order(woo_order)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        errors.append(f"Order {woo_order.get('number')}: {str(e)}")
                        logger.error(f"Failed to import order: {str(e)}")
                
                page += 1
            
            log.records_processed = success_count + fail_count
            log.records_success = success_count
            log.records_failed = fail_count
            self.complete_sync_log(
                log,
                'success' if fail_count == 0 else 'partial',
                f"Imported {success_count} orders",
                '\n'.join(errors)
            )
            
            self.config.last_order_sync = timezone.now()
            self.config.save()
            
            return success_count, fail_count, '\n'.join(errors)
        
        except Exception as e:
            self.complete_sync_log(log, 'failed', error_details=str(e))
            raise
    
    @transaction.atomic
    def _import_woo_order(self, woo_order: Dict):
        """Import single WooCommerce order"""
        woo_order_id = woo_order['id']
        
        # Check if already imported
        if OrderMapping.objects.filter(config=self.config, woo_order_id=woo_order_id).exists():
            logger.info(f"Order {woo_order_id} already imported, skipping")
            return
        
        # Get or create customer
        customer = self._get_or_create_customer(woo_order)
        
        # Create sales invoice
        invoice = self._create_sales_invoice(woo_order, customer)
        
        # Create order mapping
        OrderMapping.objects.create(
            config=self.config,
            woo_order_id=woo_order_id,
            woo_order_number=woo_order['number'],
            erp_invoice=invoice,
            erp_customer=customer,
            status=self._map_order_status(woo_order['status']),
            woo_data=woo_order,
            woo_created_at=datetime.fromisoformat(woo_order['date_created'].replace('Z', '+00:00'))
        )
    
    def _get_or_create_customer(self, woo_order: Dict) -> Customer:
        """Get or create customer from WooCommerce order"""
        woo_customer_id = woo_order.get('customer_id', 0)
        
        # Check mapping first
        if woo_customer_id > 0:
            mapping = CustomerMapping.objects.filter(
                config=self.config,
                woo_customer_id=woo_customer_id
            ).first()
            if mapping:
                return mapping.erp_customer
        
        # Extract customer data
        billing = woo_order.get('billing', {})
        email = billing.get('email', '')
        name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        phone = billing.get('phone', '')
        
        # Find existing customer by email or phone
        customer = None
        if email:
            partner = Partner.objects.filter(email=email).first()
            if partner and hasattr(partner, 'customer_profile'):
                customer = partner.customer_profile
        
        if not customer and phone:
            partner = Partner.objects.filter(phone=phone).first()
            if partner and hasattr(partner, 'customer_profile'):
                customer = partner.customer_profile
        
        # Create new customer if not found
        if not customer:
            partner = Partner.objects.create(
                name=name or 'WooCommerce Customer',
                email=email,
                phone=phone,
                address=billing.get('address_1', ''),
                city=billing.get('city', ''),
                country=billing.get('country', ''),
            )
            
            customer = Customer.objects.create(
                partner=partner,
                name=name or 'WooCommerce Customer',
                email=email,
                phone=phone,
                address=billing.get('address_1', ''),
                city=billing.get('city', ''),
                customer_type=self.config.default_customer_type,
                source='woocommerce'
            )
        
        # Create mapping if has customer ID
        if woo_customer_id > 0:
            CustomerMapping.objects.get_or_create(
                config=self.config,
                woo_customer_id=woo_customer_id,
                defaults={
                    'erp_customer': customer,
                    'woo_email': email,
                    'last_synced': timezone.now()
                }
            )
        
        return customer
    
    def _create_sales_invoice(self, woo_order: Dict, customer: Customer) -> Invoice:
        """Create sales invoice from WooCommerce order"""
        # Get system user for automated invoices
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.first()
        
        # Create invoice
        invoice = Invoice.objects.create(
            customer=customer.partner,
            date=timezone.now().date(),
            payment_method='online',
            notes=f"WooCommerce Order #{woo_order['number']}",
            created_by=system_user
        )
        
        # Add line items
        for item in woo_order.get('line_items', []):
            product = self._find_product_by_sku(item.get('sku', ''))
            if product:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=Decimal(item['quantity']),
                    price=Decimal(item['price']),
                    total=Decimal(item['total'])
                )
        
        return invoice
    
    def _find_product_by_sku(self, sku: str) -> Optional[Product]:
        """Find product by SKU"""
        if not sku:
            return None
        return Product.objects.filter(sku=sku).first()
    
    def _map_order_status(self, woo_status: str) -> str:
        """Map WooCommerce order status to ERP status"""
        status_map = {
            'pending': 'pending',
            'processing': 'processing',
            'on-hold': 'pending',
            'completed': 'completed',
            'cancelled': 'failed',
            'refunded': 'failed',
            'failed': 'failed',
        }
        return status_map.get(woo_status, 'pending')


class CustomerSyncService(SyncService):
    """Customer synchronization service"""
    
    def pull_customers_from_woocommerce(self) -> Tuple[int, int, str]:
        """Pull customers from WooCommerce"""
        log = self.create_sync_log('customer_pull')
        success_count = 0
        fail_count = 0
        errors = []
        
        try:
            page = 1
            while True:
                customers = self.client.get_customers(per_page=100, page=page)
                if not customers:
                    break
                
                for woo_customer in customers:
                    try:
                        self._import_woo_customer(woo_customer)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        errors.append(f"Customer {woo_customer.get('id')}: {str(e)}")
                        logger.error(f"Failed to import customer: {str(e)}")
                
                page += 1
            
            log.records_processed = success_count + fail_count
            log.records_success = success_count
            log.records_failed = fail_count
            self.complete_sync_log(
                log,
                'success' if fail_count == 0 else 'partial',
                f"Imported {success_count} customers",
                '\n'.join(errors)
            )
            
            return success_count, fail_count, '\n'.join(errors)
        
        except Exception as e:
            self.complete_sync_log(log, 'failed', error_details=str(e))
            raise
    
    def _import_woo_customer(self, woo_customer: Dict):
        """Import single WooCommerce customer"""
        # Implementation similar to _get_or_create_customer
        pass
