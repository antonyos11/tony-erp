"""
SEO Middleware and Utilities for E-commerce
============================================
Week 4 - Final Polish
"""

from django.conf import settings
from django.utils.html import escape
from django.db import models
import json


class SEOMiddleware:
    """Middleware لإضافة SEO headers"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


def get_product_structured_data(product):
    """
    Generate JSON-LD structured data for a product
    https://schema.org/Product
    """
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.description[:500] if product.description else "",
        "sku": product.sku if hasattr(product, 'sku') else str(product.id),
        "brand": {
            "@type": "Brand",
            "name": product.brand.name if product.brand else "متجر Tony"
        },
        "offers": {
            "@type": "Offer",
            "url": f"{settings.SITE_URL}/products/{product.slug}/",
            "priceCurrency": "EGP",
            "price": str(product.price),
            "availability": "https://schema.org/InStock" if product.stock > 0 else "https://schema.org/OutOfStock",
            "seller": {
                "@type": "Organization",
                "name": "متجر Tony"
            }
        }
    }
    
    # Add compare price if available
    if product.compare_price and product.compare_price > product.price:
        data["offers"]["priceValidUntil"] = "2026-12-31"
    
    # Add images
    if hasattr(product, 'images') and product.images.exists():
        primary_image = product.images.filter(is_primary=True).first()
        if primary_image:
            data["image"] = primary_image.image.url
    
    # Add reviews if available
    if hasattr(product, 'reviews'):
        reviews = product.reviews.filter(is_approved=True)
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg']
            data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": str(round(avg_rating, 1)),
                "reviewCount": str(reviews.count())
            }
    
    return json.dumps(data, ensure_ascii=False)


def get_category_structured_data(category, products):
    """
    Generate JSON-LD for category/collection page
    https://schema.org/CollectionPage
    """
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": category.name,
        "description": category.description or f"تسوق منتجات {category.name}",
        "url": f"{settings.SITE_URL}/categories/{category.slug}/",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": products.count(),
            "itemListElement": []
        }
    }
    
    # Add first 10 products
    for i, product in enumerate(products[:10], 1):
        data["mainEntity"]["itemListElement"].append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "name": product.name,
                "url": f"{settings.SITE_URL}/products/{product.slug}/"
            }
        })
    
    return json.dumps(data, ensure_ascii=False)


def get_organization_structured_data():
    """
    Generate JSON-LD for organization
    https://schema.org/Organization
    """
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "متجر Tony",
        "url": settings.SITE_URL,
        "logo": f"{settings.SITE_URL}/static/images/logo.png",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+20-123-456-7890",
            "contactType": "customer service",
            "areaServed": "EG",
            "availableLanguage": ["Arabic", "English"]
        },
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "EG",
            "addressLocality": "القاهرة"
        },
        "sameAs": [
            "https://facebook.com/tonystore",
            "https://instagram.com/tonystore",
            "https://twitter.com/tonystore"
        ]
    }
    
    return json.dumps(data, ensure_ascii=False)


def get_breadcrumb_structured_data(breadcrumbs):
    """
    Generate JSON-LD for breadcrumbs
    https://schema.org/BreadcrumbList
    """
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": []
    }
    
    for i, crumb in enumerate(breadcrumbs, 1):
        data["itemListElement"].append({
            "@type": "ListItem",
            "position": i,
            "name": crumb['name'],
            "item": crumb['url']
        })
    
    return json.dumps(data, ensure_ascii=False)


def get_search_action_structured_data():
    """
    Generate JSON-LD for search action
    https://schema.org/SearchAction
    """
    data = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "url": settings.SITE_URL,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{settings.SITE_URL}/search/?q={{search_term_string}}"
            },
            "query-input": "required name=search_term_string"
        }
    }
    
    return json.dumps(data, ensure_ascii=False)


def generate_meta_tags(title, description, image=None, url=None, product=None):
    """
    Generate meta tags for SEO and social sharing
    """
    site_name = "متجر Tony"
    
    tags = {
        'title': f"{title} | {site_name}",
        'description': description[:160] if description else "",
        'og:title': title,
        'og:description': description[:200] if description else "",
        'og:site_name': site_name,
        'og:type': 'product' if product else 'website',
        'og:locale': 'ar_EG',
        'twitter:card': 'summary_large_image',
        'twitter:title': title,
        'twitter:description': description[:200] if description else "",
    }
    
    if url:
        tags['og:url'] = url
        tags['twitter:url'] = url
    
    if image:
        tags['og:image'] = image
        tags['twitter:image'] = image
    
    if product:
        tags['og:type'] = 'og:product'
        tags['product:price:amount'] = str(product.price)
        tags['product:price:currency'] = 'EGP'
        if product.stock > 0:
            tags['product:availability'] = 'in stock'
        else:
            tags['product:availability'] = 'out of stock'
    
    return tags


class SEOMixin:
    """Mixin للـ Views لإضافة SEO context"""
    
    seo_title = ""
    seo_description = ""
    seo_image = None
    
    def get_seo_title(self):
        return self.seo_title
    
    def get_seo_description(self):
        return self.seo_description
    
    def get_seo_image(self):
        return self.seo_image
    
    def get_context_data(self, **kwargs):
        # Call parent's get_context_data if available
        if hasattr(super(), 'get_context_data'):
            context = super().get_context_data(**kwargs)  # type: ignore
        else:
            context = kwargs
        
        context['seo'] = {
            'title': self.get_seo_title(),
            'description': self.get_seo_description(),
            'image': self.get_seo_image(),
        }
        
        return context
