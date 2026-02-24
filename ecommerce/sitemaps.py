"""
Django Sitemaps for E-commerce
==============================
Dynamic sitemap generation for products and categories
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from ecommerce.models import OnlineProduct, ProductCategory

# Aliases for compatibility
Product = OnlineProduct
Category = ProductCategory


class StaticViewSitemap(Sitemap):
    """Sitemap للصفحات الثابتة"""
    
    priority = 0.5
    changefreq = 'monthly'
    protocol = 'https'
    
    def items(self):
        return [
            'store:home',
            'store:products',
            'store:about',
            'store:contact',
            'store:privacy',
            'store:terms',
        ]
    
    def location(self, obj):
        return reverse(obj)


class ProductSitemap(Sitemap):
    """Sitemap للمنتجات"""
    
    changefreq = 'weekly'
    protocol = 'https'
    limit = 1000  # Max URLs per sitemap file
    
    def items(self):
        return Product.objects.filter(
            is_active=True
        ).select_related('category').order_by('-updated_at')
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return f'/products/{obj.slug}/'
    
    def priority(self, obj):
        # Higher priority for featured/popular products
        if hasattr(obj, 'is_featured') and obj.is_featured:
            return 0.9
        return 0.7


class CategorySitemap(Sitemap):
    """Sitemap للفئات"""
    
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'
    
    def items(self):
        return Category.objects.filter(
            is_active=True
        ).order_by('name')
    
    def lastmod(self, obj):
        # Get latest product update in category
        latest_product = obj.products.order_by('-updated_at').first()
        if latest_product:
            return latest_product.updated_at
        return obj.updated_at if hasattr(obj, 'updated_at') else None
    
    def location(self, obj):
        return f'/categories/{obj.slug}/'


class BrandSitemap(Sitemap):
    """Sitemap للعلامات التجارية"""
    
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'
    
    def items(self):
        from ecommerce.models import Brand
        return Brand.objects.filter(
            is_active=True
        ).order_by('name')
    
    def location(self, obj):
        return f'/brands/{obj.slug}/'


# Dictionary for URL configuration
sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'brands': BrandSitemap,
}
