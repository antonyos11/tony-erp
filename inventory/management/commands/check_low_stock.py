"""
Management command to check and alert for low stock items
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from inventory.models import Product
from inventory.signals import send_low_stock_alert
from notifications.signals import notify
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'فحص المنتجات منخفضة المخزون وإرسال إشعارات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=getattr(settings, 'LOW_STOCK_THRESHOLD_DEFAULT', 10),
            help='حد المخزون المنخفض (افتراضي: 10)'
        )
        parser.add_argument(
            '--notify-all',
            action='store_true',
            help='إرسال إشعارات لجميع المشرفين'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        notify_all = options['notify_all']
        self.stdout.write(self.style.SUCCESS(f'بدء فحص المنتجات منخفضة المخزون (الحد: {threshold})...'))

        low_stock_products = []
        for product in Product.objects.all():
            if product.current_stock <= threshold:
                low_stock_products.append(product)

        if not low_stock_products:
            self.stdout.write(self.style.SUCCESS('لا توجد منتجات منخفضة المخزون'))
            return

        self.stdout.write(self.style.WARNING(f'تم العثور على {len(low_stock_products)} منتج منخفض المخزون:'))

        for product in low_stock_products:
            current_stock = product.current_stock
            min_stock = product.min_stock or threshold
            self.stdout.write(f'   - {product.name} - المخزون الحالي: {current_stock}, الحد الأدنى: {min_stock}')
            try:
                send_low_stock_alert(product)
                if notify_all:
                    admin_users = User.objects.filter(is_staff=True, is_active=True)
                    for user in admin_users:
                        notify.send(
                            sender=product,
                            recipient=user,
                            verb='فحص مخزون',
                            description=f'المنتج {product.name} منخفض المخزون ({current_stock} متبقي)',
                            data={'product_id': product.id, 'current_stock': current_stock, 'type': 'low_stock_check'}
                        )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'خطأ في إرسال إشعار للمنتج {product.name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'تم إرسال إشعارات لـ {len(low_stock_products)} منتج منخفض المخزون'))