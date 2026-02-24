"""
Analytics Integration for E-commerce
=====================================
Google Analytics 4, Facebook Pixel, and conversion tracking
Week 4 - Final Polish
"""

import json
from django.conf import settings
from django.utils.safestring import mark_safe


class AnalyticsService:
    """خدمة Analytics الموحدة"""
    
    def __init__(self):
        self.ga4_id = getattr(settings, 'GA4_MEASUREMENT_ID', None)
        self.fb_pixel_id = getattr(settings, 'FB_PIXEL_ID', None)
        self.gtm_id = getattr(settings, 'GTM_CONTAINER_ID', None)
    
    def get_gtag_config(self):
        """إعدادات Google Tag"""
        if not self.ga4_id:
            return ''
        
        return f'''
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={self.ga4_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{self.ga4_id}', {{
    'currency': 'EGP',
    'country': 'EG',
    'language': 'ar'
  }});
</script>
'''
    
    def get_fb_pixel(self):
        """Facebook Pixel script"""
        if not self.fb_pixel_id:
            return ''
        
        return f'''
<!-- Facebook Pixel Code -->
<script>
  !function(f,b,e,v,n,t,s)
  {{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}}(window, document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', '{self.fb_pixel_id}');
  fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
  src="https://www.facebook.com/tr?id={self.fb_pixel_id}&ev=PageView&noscript=1"
/></noscript>
<!-- End Facebook Pixel Code -->
'''
    
    def get_gtm_head(self):
        """Google Tag Manager - Head script"""
        if not self.gtm_id:
            return ''
        
        return f'''
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{self.gtm_id}');</script>
<!-- End Google Tag Manager -->
'''
    
    def get_gtm_body(self):
        """Google Tag Manager - Body noscript"""
        if not self.gtm_id:
            return ''
        
        return f'''
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={self.gtm_id}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
'''


def track_page_view(request, page_title=None, page_type='page'):
    """Track page view event"""
    return {
        'event': 'page_view',
        'page_title': page_title or '',
        'page_type': page_type,
        'page_location': request.build_absolute_uri(),
        'page_path': request.path,
    }


def track_product_view(product):
    """Track product view event (GA4 view_item)"""
    return {
        'event': 'view_item',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(product.price),
            'items': [{
                'item_id': str(product.id),
                'item_name': product.name,
                'item_category': product.category.name if product.category else '',
                'item_brand': product.brand.name if product.brand else '',
                'price': float(product.price),
                'quantity': 1
            }]
        }
    }


def track_add_to_cart(product, quantity=1):
    """Track add to cart event (GA4 add_to_cart)"""
    return {
        'event': 'add_to_cart',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(product.price * quantity),
            'items': [{
                'item_id': str(product.id),
                'item_name': product.name,
                'item_category': product.category.name if product.category else '',
                'item_brand': product.brand.name if product.brand else '',
                'price': float(product.price),
                'quantity': quantity
            }]
        }
    }


def track_remove_from_cart(product, quantity=1):
    """Track remove from cart event"""
    return {
        'event': 'remove_from_cart',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(product.price * quantity),
            'items': [{
                'item_id': str(product.id),
                'item_name': product.name,
                'price': float(product.price),
                'quantity': quantity
            }]
        }
    }


def track_view_cart(cart_items, cart_total):
    """Track view cart event"""
    items = []
    for item in cart_items:
        items.append({
            'item_id': str(item.product.id),
            'item_name': item.product.name,
            'item_category': item.product.category.name if item.product.category else '',
            'price': float(item.product.price),
            'quantity': item.quantity
        })
    
    return {
        'event': 'view_cart',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(cart_total),
            'items': items
        }
    }


def track_begin_checkout(cart_items, cart_total, coupon=None):
    """Track begin checkout event"""
    items = []
    for item in cart_items:
        items.append({
            'item_id': str(item.product.id),
            'item_name': item.product.name,
            'price': float(item.product.price),
            'quantity': item.quantity
        })
    
    data = {
        'event': 'begin_checkout',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(cart_total),
            'items': items
        }
    }
    
    if coupon:
        data['ecommerce']['coupon'] = coupon
    
    return data


def track_add_shipping_info(order, shipping_method):
    """Track shipping info step"""
    return {
        'event': 'add_shipping_info',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(order.total),
            'shipping_tier': shipping_method,
            'items': _get_order_items(order)
        }
    }


def track_add_payment_info(order, payment_method):
    """Track payment info step"""
    return {
        'event': 'add_payment_info',
        'ecommerce': {
            'currency': 'EGP',
            'value': float(order.total),
            'payment_type': payment_method,
            'items': _get_order_items(order)
        }
    }


def track_purchase(order):
    """Track purchase/conversion event (GA4 purchase)"""
    items = _get_order_items(order)
    
    return {
        'event': 'purchase',
        'ecommerce': {
            'transaction_id': order.order_number,
            'value': float(order.total),
            'tax': float(order.vat_amount) if hasattr(order, 'vat_amount') else 0,
            'shipping': float(order.shipping_cost) if hasattr(order, 'shipping_cost') else 0,
            'currency': 'EGP',
            'coupon': order.coupon.code if hasattr(order, 'coupon') and order.coupon else '',
            'items': items
        }
    }


def track_refund(order, partial=False, items=None):
    """Track refund event"""
    data = {
        'event': 'refund',
        'ecommerce': {
            'transaction_id': order.order_number,
            'currency': 'EGP'
        }
    }
    
    if partial and items:
        data['ecommerce']['value'] = sum(float(i['price'] * i['quantity']) for i in items)
        data['ecommerce']['items'] = items
    else:
        data['ecommerce']['value'] = float(order.total)
    
    return data


def track_search(search_term, results_count=0):
    """Track search event"""
    return {
        'event': 'search',
        'search_term': search_term,
        'results_count': results_count
    }


def track_login(method='email'):
    """Track login event"""
    return {
        'event': 'login',
        'method': method
    }


def track_sign_up(method='email'):
    """Track sign up event"""
    return {
        'event': 'sign_up',
        'method': method
    }


def _get_order_items(order):
    """Helper to format order items for analytics"""
    items = []
    for item in order.items.select_related('product', 'product__category'):
        items.append({
            'item_id': str(item.product.id),
            'item_name': item.product.name,
            'item_category': item.product.category.name if item.product.category else '',
            'price': float(item.price),
            'quantity': item.quantity
        })
    return items


# Template tag helpers
def render_analytics_event(event_data):
    """Render analytics event as JavaScript"""
    return mark_safe(f'''
<script>
  if (typeof gtag !== 'undefined') {{
    gtag('event', '{event_data["event"]}', {json.dumps(event_data.get('ecommerce', {}), ensure_ascii=False)});
  }}
  if (typeof fbq !== 'undefined') {{
    fbq('track', '{_ga_to_fb_event(event_data["event"])}', {json.dumps(_format_fb_params(event_data), ensure_ascii=False)});
  }}
</script>
''')


def _ga_to_fb_event(ga_event):
    """Map GA4 events to Facebook Pixel events"""
    mapping = {
        'view_item': 'ViewContent',
        'add_to_cart': 'AddToCart',
        'begin_checkout': 'InitiateCheckout',
        'add_payment_info': 'AddPaymentInfo',
        'purchase': 'Purchase',
        'search': 'Search',
        'sign_up': 'CompleteRegistration',
    }
    return mapping.get(ga_event, 'CustomEvent')


def _format_fb_params(event_data):
    """Format parameters for Facebook Pixel"""
    ecommerce = event_data.get('ecommerce', {})
    
    params = {
        'currency': ecommerce.get('currency', 'EGP'),
        'value': ecommerce.get('value', 0)
    }
    
    if 'items' in ecommerce and ecommerce['items']:
        params['content_ids'] = [item['item_id'] for item in ecommerce['items']]
        params['content_type'] = 'product'
        params['num_items'] = sum(item.get('quantity', 1) for item in ecommerce['items'])
    
    return params
