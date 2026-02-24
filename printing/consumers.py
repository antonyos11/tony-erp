"""
Unified Print Agent WebSocket Consumer.
وكيل الطباعة الموحد عبر WebSocket.
يستبدل PrintAgentConsumer في production/consumers_pipeline.py
بمستهلك واحد يتعامل مع جميع أنواع مهام الطباعة.

v2.0 — Station-aware: supports dynamic device registration,
       station-specific groups, heartbeat, and queued job replay.
"""
import json
import logging
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class UnifiedPrintAgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the print agent.
    The agent (Windows/Linux) connects here, registers its station,
    and receives print commands targeted to its station group.
    """
    PRINT_GROUP = 'print_agent'  # Global broadcast group (legacy compat)

    async def connect(self):
        self.station_name = None
        self.station_group = None

        # Join the global group (backward compat)
        await self.channel_layer.group_add(self.PRINT_GROUP, self.channel_name)
        await self.accept()

        logger.info(f"Print agent connected: {self.channel_name}")

        # Re-queue stale 'sent' jobs that were never confirmed (agent crashed)
        await self._requeue_stale_sent_jobs()

        # Send queued jobs (legacy — before registration)
        queued_jobs = await self._get_queued_jobs_legacy()
        for job_data in queued_jobs:
            await self.send(text_data=json.dumps(job_data))

    async def disconnect(self, close_code):
        # Leave global group
        await self.channel_layer.group_discard(self.PRINT_GROUP, self.channel_name)

        # Leave station-specific group
        if self.station_group:
            await self.channel_layer.group_discard(self.station_group, self.channel_name)

        # Mark station offline
        if self.station_name:
            await self._mark_station_offline(self.station_name)

        logger.info(f"Print agent disconnected: {self.station_name or self.channel_name} (code={close_code})")

    async def receive(self, text_data):
        """Receive messages from the agent."""
        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from print agent")
            return

        msg_type = message.get('type', message.get('action', ''))

        # ── Agent Registration (new protocol) ──
        if msg_type == 'register':
            machine_name = message.get('machine_name', '')
            machine_ip = message.get('machine_ip', '')
            printers = message.get('printers', [])
            agent_version = message.get('agent_version', '')
            os_platform = message.get('os_platform', '')
            agent_port = message.get('agent_port', 9876)

            if machine_name:
                self.station_name = machine_name
                self.station_group = f"print_station_{machine_name}"

                # Join station-specific group
                await self.channel_layer.group_add(
                    self.station_group, self.channel_name
                )

                # Register / update in DB
                await self._register_station(
                    machine_name=machine_name,
                    machine_ip=machine_ip,
                    printers=printers,
                    agent_version=agent_version,
                    os_platform=os_platform,
                    agent_port=agent_port,
                )

                logger.info(
                    f"Station registered: {machine_name} "
                    f"({len(printers)} printers) → group {self.station_group}"
                )

                # Acknowledge registration
                await self.send(text_data=json.dumps({
                    'type': 'register_ack',
                    'station': machine_name,
                    'status': 'ok',
                }))

                # Send back queued jobs for this station
                queued = await self._get_queued_jobs_for_station(machine_name)
                for job_data in queued:
                    await self.send(text_data=json.dumps(job_data))

        # ── Print result (success) ──
        elif msg_type == 'print_result':
            job_id = message.get('job_id')
            success = message.get('success', False)
            error = message.get('error', '')

            if not job_id or job_id == 'None':
                logger.debug(f"Ignoring print_result with no job_id (success={success})")
                return

            if success:
                await self._confirm_print(job_id)
            else:
                await self._mark_failed(job_id, error)

            # Broadcast status update to dashboard consumers
            await self.channel_layer.group_send(
                'print_status',
                {
                    'type': 'print.status.update',
                    'data': {
                        'job_id': job_id,
                        'success': success,
                        'error': error,
                        'station': self.station_name or '',
                    },
                },
            )

        elif msg_type in ('print_done', 'print_success'):
            job_id = message.get('job_id')
            if job_id and str(job_id) != 'None':
                await self._confirm_print(job_id)

        elif msg_type in ('print_failed', 'print_error'):
            job_id = message.get('job_id')
            error = message.get('error', 'Unknown error')
            if job_id and str(job_id) != 'None':
                await self._mark_failed(job_id, error)

        # ── Agent status (legacy) ──
        elif msg_type == 'agent_status':
            logger.info(f"Agent status: {message.get('printers', [])}")

        # ── Heartbeat ──
        elif msg_type == 'heartbeat':
            if self.station_name:
                await self._touch_station(self.station_name)
            await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))

    async def print_command(self, event):
        """
        Called by PrintDispatcher/PrintService via channel_layer.group_send().
        Forwards the print command to the connected agent.
        """
        await self.send(text_data=json.dumps(event['data']))

    # ──────────────────────────────────────────
    # Database helpers
    # ──────────────────────────────────────────

    @database_sync_to_async
    def _register_station(self, machine_name, machine_ip, printers,
                          agent_version, os_platform, agent_port):
        from printing.models import PrintStation
        station, created = PrintStation.objects.update_or_create(
            machine_name=machine_name,
            defaults={
                'machine_ip': machine_ip or None,
                'agent_port': agent_port,
                'is_online': True,
            },
        )
        station.update_discovered_printers(
            printers, agent_version=agent_version, os_platform=os_platform,
        )
        if created:
            logger.info(f"New station created: {machine_name}")

    @database_sync_to_async
    def _mark_station_offline(self, machine_name):
        from printing.models import PrintStation
        PrintStation.objects.filter(machine_name=machine_name).update(is_online=False)

    @database_sync_to_async
    def _touch_station(self, machine_name):
        from printing.models import PrintStation
        from django.utils import timezone
        PrintStation.objects.filter(machine_name=machine_name).update(
            last_seen=timezone.now(), is_online=True,
        )

    @database_sync_to_async
    def _confirm_print(self, job_id):
        from printing.dispatch import PrintDispatcher
        PrintDispatcher.confirm_completed(job_id)
        logger.info(f"Print job confirmed: {job_id}")

    @database_sync_to_async
    def _mark_failed(self, job_id, error):
        from printing.dispatch import PrintDispatcher
        PrintDispatcher.mark_failed(job_id, error)
        logger.warning(f"Print job failed: {job_id} — {error}")

    @database_sync_to_async
    def _requeue_stale_sent_jobs(self):
        """
        Re-queue 'sent' jobs older than 2 minutes that were never confirmed.
        This recovers from agent crashes / disconnections.
        """
        from printing.models import UnifiedPrintJob
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(minutes=2)
        stale_count = UnifiedPrintJob.objects.filter(
            status='sent',
            sent_at__lt=cutoff,
        ).update(status='queued', error_message='أُعيد للطابور — الوكيل لم يؤكد الاستلام')

        if stale_count:
            logger.info(f"Re-queued {stale_count} stale 'sent' jobs → 'queued'")

    @database_sync_to_async
    def _get_queued_jobs_legacy(self):
        """Get jobs that were queued while agent was offline (legacy — no station)."""
        from printing.models import UnifiedPrintJob

        jobs = UnifiedPrintJob.objects.filter(
            status='queued'
        ).select_related('printer').order_by('created_at')[:50]

        results = []
        for job in jobs:
            payload = {
                'job_id': str(job.id),
                'document_type': job.document_type,
                'copies': job.copies,
                'title': job.title,
            }

            if job.zpl_command:
                payload['action'] = 'print_zebra_zpl'
                payload['zpl'] = job.zpl_command
            elif job.pdf_base64:
                payload['action'] = 'print_a4'
                payload['pdf_base64'] = job.pdf_base64
            elif job.html_content:
                payload['action'] = 'print_a4'
                payload['html'] = job.html_content
            elif job.escpos_data:
                payload['action'] = 'print_thermal_receipt'
                payload['raw_base64'] = base64.b64encode(bytes(job.escpos_data)).decode('ascii')

            if job.printer:
                payload['printer_name'] = job.printer.cups_printer_name or job.printer.name
                if job.printer.ip_address:
                    payload['ip'] = str(job.printer.ip_address)
                    payload['port'] = job.printer.port

            results.append(payload)

            # Mark as sent
            job.status = 'sent'
            job.save(update_fields=['status'])

        return results

    @database_sync_to_async
    def _get_queued_jobs_for_station(self, machine_name):
        """Get jobs queued while agent was offline, targeted to this station."""
        from printing.models import UnifiedPrintJob, PrintStation

        try:
            station = PrintStation.objects.get(machine_name=machine_name)
        except PrintStation.DoesNotExist:
            return []

        # Find jobs for printers mapped to this station
        mapped_printer_ids = list(
            station.printer_mappings.filter(
                is_enabled=True,
                printer_config__isnull=False,
            ).values_list('printer_config_id', flat=True)
        )

        if not mapped_printer_ids:
            return []

        jobs = UnifiedPrintJob.objects.filter(
            status='queued',
            printer_id__in=mapped_printer_ids,
        ).select_related('printer').order_by('created_at')[:20]

        # Build a lookup: printer_config_id → local_printer_name from mappings
        # This ensures the EXACT copy name is sent, not a generic name
        printer_to_local = {}
        for mapping in station.printer_mappings.filter(is_enabled=True, printer_config__isnull=False):
            if mapping.local_printer_name:
                printer_to_local[mapping.printer_config_id] = mapping.local_printer_name

        result = []
        for job in jobs:
            payload = {
                'job_id': str(job.id),
                'document_type': job.document_type,
                'copies': job.copies,
                'title': job.title,
                'target_station': machine_name,
            }
            if job.zpl_command:
                payload['action'] = 'print_zebra_zpl'
                payload['zpl'] = job.zpl_command
            elif job.pdf_base64:
                payload['action'] = 'print_a4'
                payload['pdf_base64'] = job.pdf_base64
            elif job.html_content:
                payload['action'] = 'print_a4'
                payload['html'] = job.html_content
            elif job.escpos_data:
                payload['action'] = 'print_thermal_receipt'
                payload['raw_base64'] = base64.b64encode(
                    bytes(job.escpos_data)
                ).decode('ascii')
            else:
                continue

            # CRITICAL: Use the EXACT local printer name from mapping
            if job.printer_id and job.printer_id in printer_to_local:
                payload['printer_name'] = printer_to_local[job.printer_id]
            elif job.printer:
                payload['printer_name'] = (
                    job.printer.cups_printer_name
                    or job.printer.shared_printer_name
                    or job.printer.name
                )
                if job.printer.ip_address:
                    payload['ip'] = str(job.printer.ip_address)
                    payload['port'] = job.printer.port

            result.append(payload)
            job.status = 'sent'
            job.save(update_fields=['status'])

        return result


class PrintStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for browser clients that want real-time print status.
    Used by the Print Status icon in the header.
    """

    async def connect(self):
        await self.channel_layer.group_add('print_status', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('print_status', self.channel_name)

    async def print_status_update(self, event):
        """Forward print status to browser."""
        await self.send(text_data=json.dumps(event['data']))
