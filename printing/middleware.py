"""
printing/middleware.py — Station Detection Middleware
=====================================================
يكتشف محطة الطباعة الخاصة بالمستخدم تلقائياً بناءً على IP أو الجلسة.

Auto-detects the user's PrintStation based on their IP address,
explicit session assignment, or user assignment.
Sets `request.print_station` for use by PrintService.
"""

import logging

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class StationDetectionMiddleware(MiddlewareMixin):
    """
    Detects the user's PrintStation based on their IP address or
    explicit session assignment.  Sets `request.print_station`.
    """

    def process_request(self, request):
        request.print_station = None

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return

        # 1. Check explicit session assignment (fastest)
        from printing.models import StationSession
        try:
            session = StationSession.objects.select_related('station').get(
                user=request.user,
            )
            if session.station.is_active:
                request.print_station = session.station
                return
        except StationSession.DoesNotExist:
            pass

        # 2. Detect by client IP
        client_ip = self._get_client_ip(request)
        if client_ip:
            from printing.models import PrintStation
            station = PrintStation.objects.filter(
                machine_ip=client_ip,
                is_active=True,
            ).first()

            if station:
                request.print_station = station
                # Auto-create session for faster subsequent lookups
                StationSession.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'station': station,
                        'client_ip': client_ip,
                        'session_key': request.session.session_key or '',
                    },
                )
                return

        # 3. Check if user is assigned to a station
        from printing.models import PrintStation
        station = PrintStation.objects.filter(
            assigned_users=request.user,
            is_active=True,
            is_online=True,
        ).first()

        if station:
            request.print_station = station

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
