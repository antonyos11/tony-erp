"""
إشارات تلقائية لإنشاء لوحات الأنابيب عند إنشاء أوامر الإنتاج
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from production.models import ProductionOrder

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ProductionOrder)
def auto_create_pipeline_board(sender, instance, created, **kwargs):
    """إنشاء لوحة أنابيب تلقائياً عند إنشاء أمر إنتاج جديد"""
    if created:
        try:
            from production.services.pipeline_service import PipelineService
            success, msg, board = PipelineService.create_board_for_order(instance)
            if success:
                logger.info(f"Auto-created pipeline board for order {instance.number}")
            else:
                logger.warning(f"Could not create pipeline board: {msg}")
        except Exception as e:
            logger.error(f"Error creating pipeline board: {e}")
