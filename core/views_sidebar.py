"""
Sidebar Badge API — Returns live counts for sidebar notification badges.
Called via AJAX from sidebar_v3.js every 60 seconds.
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@login_required
@require_GET
def sidebar_badges_api(request):
    """Return live badge counts for sidebar items."""
    sources_param = request.GET.get('sources', '')
    if not sources_param:
        return JsonResponse({})

    sources = [s.strip() for s in sources_param.split(',') if s.strip()]
    result = {}

    for source in sources:
        try:
            result[source] = _get_badge_count(source, request.user)
        except Exception as exc:
            logger.debug("Badge source %s error: %s", source, exc)
            result[source] = 0

    return JsonResponse(result)


def _get_badge_count(source, user):
    """
    Get count for a specific badge source.
    Each source is wrapped in its own try/except so missing models
    or apps never break the whole response.
    """

    if source == 'pending_qc_count':
        try:
            from production.models import ProductionOrder
            return ProductionOrder.objects.filter(status='pending_qc').count()
        except Exception:
            return 0

    elif source == 'low_stock_alerts':
        try:
            from inventory.models import Product
            from django.db.models import F
            return Product.objects.filter(
                quantity__lte=F('minimum_stock')
            ).count()
        except Exception:
            return 0

    elif source == 'offline_printers_count':
        return 0  # Print agent is external - count from cache/signal

    elif source == 'pending_online_orders':
        try:
            from ecommerce.models import Order
            return Order.objects.filter(status='pending').count()
        except Exception:
            return 0

    elif source == 'open_maintenance_tickets':
        return 0  # Maintenance module planned

    elif source == 'active_production_count':
        try:
            from production.models import ProductionOrder
            return ProductionOrder.objects.filter(
                status__in=['in_progress', 'started']
            ).count()
        except Exception:
            return 0

    return 0
