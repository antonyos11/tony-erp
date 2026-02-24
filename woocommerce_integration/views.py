from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    WooCommerceConfig,
    ProductMapping,
    OrderMapping,
    CustomerMapping,
    SyncLog
)
from .services import ProductSyncService, OrderSyncService, CustomerSyncService
from .woocommerce_client import WooCommerceAPIError


@login_required
def dashboard(request):
    """WooCommerce Integration Dashboard"""
    configs = WooCommerceConfig.objects.filter(is_active=True)
    
    # Stats
    stats = {
        'total_configs': configs.count(),
        'product_mappings': ProductMapping.objects.filter(sync_enabled=True).count(),
        'order_mappings': OrderMapping.objects.count(),
        'customer_mappings': CustomerMapping.objects.count(),
    }
    
    # Recent logs
    recent_logs = SyncLog.objects.all()[:20]
    
    context = {
        'configs': configs,
        'stats': stats,
        'recent_logs': recent_logs,
    }
    return render(request, 'woocommerce_integration/dashboard.html', context)


@login_required
def config_list(request):
    """List all WooCommerce configurations"""
    configs = WooCommerceConfig.objects.all()
    return render(request, 'woocommerce_integration/config_list.html', {'configs': configs})


@login_required
def config_create(request):
    """Create new WooCommerce configuration"""
    if request.method == 'POST':
        # Simple form handling - in production, use Django forms
        try:
            config = WooCommerceConfig.objects.create(
                name=request.POST['name'],
                store_url=request.POST['store_url'],
                consumer_key=request.POST['consumer_key'],
                consumer_secret=request.POST['consumer_secret'],
                is_active=request.POST.get('is_active') == 'on',
                is_default=request.POST.get('is_default') == 'on',
            )
            messages.success(request, _('تم إنشاء الإعداد بنجاح'))
            return redirect('woocommerce_integration:config_list')
        except Exception as e:
            messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return render(request, 'woocommerce_integration/config_form.html')


@login_required
def config_edit(request, pk):
    """Edit WooCommerce configuration"""
    config = get_object_or_404(WooCommerceConfig, pk=pk)
    
    if request.method == 'POST':
        try:
            config.name = request.POST['name']
            config.store_url = request.POST['store_url']
            config.consumer_key = request.POST['consumer_key']
            config.consumer_secret = request.POST['consumer_secret']
            config.is_active = request.POST.get('is_active') == 'on'
            config.is_default = request.POST.get('is_default') == 'on'
            config.save()
            messages.success(request, _('تم تحديث الإعداد بنجاح'))
            return redirect('woocommerce_integration:config_list')
        except Exception as e:
            messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return render(request, 'woocommerce_integration/config_form.html', {'config': config})


@login_required
def test_connection(request, pk):
    """Test WooCommerce connection"""
    config = get_object_or_404(WooCommerceConfig, pk=pk)
    
    try:
        service = ProductSyncService(config)
        if service.client.test_connection():
            messages.success(request, _('الاتصال بـ WooCommerce ناجح!'))
        else:
            messages.error(request, _('فشل الاتصال بـ WooCommerce'))
    except WooCommerceAPIError as e:
        messages.error(request, f'{_("خطأ في الاتصال")}: {str(e)}')
    
    return redirect('woocommerce_integration:config_list')


@login_required
def sync_products_push(request):
    """Push products to WooCommerce"""
    config = WooCommerceConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        messages.error(request, _('لا يوجد إعداد WooCommerce نشط'))
        return redirect('woocommerce_integration:dashboard')
    
    try:
        service = ProductSyncService(config)
        # Push all active products
        from inventory.models import Product
        products = Product.objects.filter(is_active=True)
        
        success = 0
        failed = 0
        for product in products:
            ok, msg = service.push_product_to_woocommerce(product)
            if ok:
                success += 1
            else:
                failed += 1
        
        messages.success(request, f'{_("تم دفع")} {success} {_("منتج بنجاح")}. {_("فشل")}: {failed}')
    except Exception as e:
        messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return redirect('woocommerce_integration:dashboard')


@login_required
def sync_products_pull(request):
    """Pull products from WooCommerce"""
    config = WooCommerceConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        messages.error(request, _('لا يوجد إعداد WooCommerce نشط'))
        return redirect('woocommerce_integration:dashboard')
    
    try:
        service = ProductSyncService(config)
        success, failed, errors = service.pull_products_from_woocommerce()
        messages.success(request, f'{_("تم سحب")} {success} {_("منتج بنجاح")}. {_("فشل")}: {failed}')
        if errors:
            messages.warning(request, f'{_("أخطاء")}: {errors[:500]}...')
    except Exception as e:
        messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return redirect('woocommerce_integration:dashboard')


@login_required
def sync_inventory(request):
    """Sync inventory to WooCommerce"""
    config = WooCommerceConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        messages.error(request, _('لا يوجد إعداد WooCommerce نشط'))
        return redirect('woocommerce_integration:dashboard')
    
    try:
        service = ProductSyncService(config)
        success, failed = service.sync_inventory_to_woocommerce()
        messages.success(request, f'{_("تم مزامنة المخزون لـ")} {success} {_("منتج")}. {_("فشل")}: {failed}')
    except Exception as e:
        messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return redirect('woocommerce_integration:dashboard')


@login_required
def sync_orders(request):
    """Pull orders from WooCommerce"""
    config = WooCommerceConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        messages.error(request, _('لا يوجد إعداد WooCommerce نشط'))
        return redirect('woocommerce_integration:dashboard')
    
    try:
        service = OrderSyncService(config)
        success, failed, errors = service.pull_orders_from_woocommerce()
        messages.success(request, f'{_("تم سحب")} {success} {_("طلب بنجاح")}. {_("فشل")}: {failed}')
        if errors:
            messages.warning(request, f'{_("أخطاء")}: {errors[:500]}...')
    except Exception as e:
        messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return redirect('woocommerce_integration:dashboard')


@login_required
def sync_customers(request):
    """Pull customers from WooCommerce"""
    config = WooCommerceConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        messages.error(request, _('لا يوجد إعداد WooCommerce نشط'))
        return redirect('woocommerce_integration:dashboard')
    
    try:
        service = CustomerSyncService(config)
        success, failed, errors = service.pull_customers_from_woocommerce()
        messages.success(request, f'{_("تم سحب")} {success} {_("عميل بنجاح")}. {_("فشل")}: {failed}')
        if errors:
            messages.warning(request, f'{_("أخطاء")}: {errors[:500]}...')
    except Exception as e:
        messages.error(request, f'{_("خطأ")}: {str(e)}')
    
    return redirect('woocommerce_integration:dashboard')


@login_required
def product_mappings(request):
    """List product mappings"""
    mappings = ProductMapping.objects.select_related('config', 'erp_product').all()
    return render(request, 'woocommerce_integration/product_mappings.html', {'mappings': mappings})


@login_required
def order_mappings(request):
    """List order mappings"""
    mappings = OrderMapping.objects.select_related('config', 'erp_invoice', 'erp_customer').all()
    return render(request, 'woocommerce_integration/order_mappings.html', {'mappings': mappings})


@login_required
def customer_mappings(request):
    """List customer mappings"""
    mappings = CustomerMapping.objects.select_related('config', 'erp_customer').all()
    return render(request, 'woocommerce_integration/customer_mappings.html', {'mappings': mappings})


@login_required
def sync_logs(request):
    """List sync logs"""
    logs = SyncLog.objects.select_related('config').all()[:100]
    return render(request, 'woocommerce_integration/sync_logs.html', {'logs': logs})
