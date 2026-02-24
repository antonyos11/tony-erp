"""
أمر إدارة لإضافة صفحات المتجر الإلكتروني إلى نظام إدارة الصفحات
"""
from django.core.management.base import BaseCommand
from core.models import Page


class Command(BaseCommand):
    help = 'إضافة صفحات المتجر الإلكتروني إلى نظام إدارة الصفحات'

    def handle(self, *args, **options):
        self.stdout.write("إضافة صفحات المتجر الإلكتروني...")
        
        # إنشاء الصفحة الرئيسية للمتجر
        parent_page, created = Page.objects.get_or_create(
            code='ecommerce',
            defaults={
                'name': 'المتجر الإلكتروني',
                'url': '',
                'module': 'ecommerce',
                'icon': 'bi-shop',
                'order': 0,
                'is_menu_item': True,
            }
        )
        self.stdout.write(f"{'✓ جديد' if created else '↺ موجود'}: {parent_page.name}")
        
        # الصفحات الفرعية
        sub_pages = [
            {'name': 'لوحة تحكم المتجر', 'code': 'ecommerce_dashboard', 'url': 'ecommerce:admin_dashboard', 'icon': 'bi-speedometer2', 'order': 1},
            {'name': 'الطلبات', 'code': 'ecommerce_orders', 'url': 'ecommerce:admin_orders', 'icon': 'bi-cart-check', 'order': 2},
            {'name': 'المنتجات', 'code': 'ecommerce_products', 'url': 'ecommerce:admin_products', 'icon': 'bi-box-seam', 'order': 3},
            {'name': 'التصنيفات', 'code': 'ecommerce_categories', 'url': 'ecommerce:admin_categories', 'icon': 'bi-folder', 'order': 4},
            {'name': 'التقييمات', 'code': 'ecommerce_reviews', 'url': 'ecommerce:admin_reviews', 'icon': 'bi-star', 'order': 5},
            {'name': 'الكوبونات', 'code': 'ecommerce_coupons', 'url': 'ecommerce:admin_coupons', 'icon': 'bi-ticket-perforated', 'order': 6},
            {'name': 'إعدادات المتجر', 'code': 'ecommerce_settings', 'url': 'ecommerce:admin_settings', 'icon': 'bi-gear', 'order': 7},
            {'name': 'بوابات الدفع', 'code': 'ecommerce_payment_gateways', 'url': 'ecommerce:admin_payment_gateways', 'icon': 'bi-credit-card', 'order': 8},
            {'name': 'شركات الشحن', 'code': 'ecommerce_shipping_companies', 'url': 'ecommerce:admin_shipping_companies', 'icon': 'bi-truck', 'order': 9},
            {'name': 'التواصل الاجتماعي', 'code': 'ecommerce_social_media', 'url': 'ecommerce:admin_social_media', 'icon': 'bi-share', 'order': 10},
            {'name': 'البانرات', 'code': 'ecommerce_banners', 'url': 'ecommerce:admin_banners', 'icon': 'bi-images', 'order': 11},
            {'name': 'محتوى الصفحات', 'code': 'ecommerce_page_content', 'url': 'ecommerce:admin_page_content', 'icon': 'bi-file-text', 'order': 12},
            {'name': 'عرض المتجر', 'code': 'ecommerce_store_view', 'url': 'ecommerce:store_home', 'icon': 'bi-shop-window', 'order': 13},
        ]
        
        for page_data in sub_pages:
            page, created = Page.objects.get_or_create(
                code=page_data['code'],
                defaults={
                    'name': page_data['name'],
                    'url': page_data['url'],
                    'module': 'ecommerce',
                    'icon': page_data['icon'],
                    'order': page_data['order'],
                    'parent': parent_page,
                    'is_menu_item': True,
                }
            )
            if not created and page.parent != parent_page:
                page.parent = parent_page
                page.save()
            self.stdout.write(f"  {'✓ جديد' if created else '↺ موجود'}: {page.name}")
        
        self.stdout.write(self.style.SUCCESS("\n✅ تم إضافة جميع صفحات المتجر الإلكتروني!"))
