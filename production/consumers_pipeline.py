"""
WebSocket consumers for the Global Production Pipeline dashboard.
Handles real-time sync between departments and print agent communication.
"""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class PipelineDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for the production pipeline Kanban board."""

    PIPELINE_GROUP = 'production_pipeline'

    async def connect(self):
        await self.channel_layer.group_add(
            self.PIPELINE_GROUP,
            self.channel_name,
        )
        await self.accept()

        # Send full snapshot on connect
        snapshot = await self.get_pipeline_snapshot()
        await self.send(text_data=json.dumps({
            'type': 'full_snapshot',
            'data': snapshot,
            'timestamp': timezone.now().isoformat(),
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.PIPELINE_GROUP,
            self.channel_name,
        )

    async def receive(self, text_data):
        """Handle client messages: actions from supervisors."""
        try:
            message = json.loads(text_data)
            action = message.get('action')

            if action == 'refresh':
                snapshot = await self.get_pipeline_snapshot()
                await self.send(text_data=json.dumps({
                    'type': 'full_snapshot',
                    'data': snapshot,
                    'timestamp': timezone.now().isoformat(),
                }))

            elif action == 'start_stage':
                result = await self.handle_start_stage(message)
                await self.send(text_data=json.dumps(result))

            elif action == 'complete_stage':
                result = await self.handle_complete_stage(message)
                await self.send(text_data=json.dumps(result))

            elif action == 'fail_stage':
                result = await self.handle_fail_stage(message)
                await self.send(text_data=json.dumps(result))

            elif action == 'reprint':
                result = await self.handle_reprint(message)
                await self.send(text_data=json.dumps(result))

            elif action == 'report_issue':
                result = await self.handle_report_issue(message)
                await self.send(text_data=json.dumps(result))

                # Broadcast issue to all connected dashboards
                if result.get('success'):
                    await self.channel_layer.group_send(
                        self.PIPELINE_GROUP,
                        {
                            'type': 'pipeline.stage.update',
                            'data': {
                                'event': 'issue_reported',
                                'stage_id': message.get('stage_id'),
                                'issue': result.get('issue_data'),
                                'timestamp': timezone.now().isoformat(),
                            },
                        },
                    )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Invalid pipeline WS message: {e}")

    # ── Group message handlers ──

    async def pipeline_stage_update(self, event):
        """Relay pipeline stage update to all connected clients."""
        await self.send(text_data=json.dumps({
            'type': 'stage_update',
            'data': event['data'],
        }))

    # ── Action handlers ──

    @database_sync_to_async
    def handle_start_stage(self, message):
        from production.models_pipeline import PipelineStageEntry
        from production.services.pipeline_service import PipelineService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        stage_id = message.get('stage_id')
        user_id = message.get('user_id')

        try:
            stage = PipelineStageEntry.objects.select_related(
                'board__production_order__product', 'work_center'
            ).get(id=stage_id)
            user = User.objects.get(id=user_id)

            success, msg = PipelineService.start_stage(stage, user)
            return {'type': 'action_result', 'success': success, 'message': msg}
        except Exception as e:
            return {'type': 'action_result', 'success': False, 'message': str(e)}

    @database_sync_to_async
    def handle_complete_stage(self, message):
        from production.models_pipeline import PipelineStageEntry
        from production.services.pipeline_service import PipelineService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        stage_id = message.get('stage_id')
        user_id = message.get('user_id')

        try:
            stage = PipelineStageEntry.objects.select_related(
                'board__production_order__product', 'work_center'
            ).get(id=stage_id)
            user = User.objects.get(id=user_id)

            success, msg, details = PipelineService.complete_stage(stage, user)
            return {
                'type': 'action_result',
                'success': success,
                'message': msg,
                'details': details,
            }
        except Exception as e:
            return {'type': 'action_result', 'success': False, 'message': str(e)}

    @database_sync_to_async
    def handle_fail_stage(self, message):
        from production.models_pipeline import PipelineStageEntry
        from production.services.pipeline_service import PipelineService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        stage_id = message.get('stage_id')
        user_id = message.get('user_id')
        reason = message.get('reason', '')
        category = message.get('category', 'other')

        try:
            stage = PipelineStageEntry.objects.select_related(
                'board__production_order__product', 'work_center'
            ).get(id=stage_id)
            user = User.objects.get(id=user_id)

            success, msg = PipelineService.fail_stage(stage, user, reason, category)
            return {'type': 'action_result', 'success': success, 'message': msg}
        except Exception as e:
            return {'type': 'action_result', 'success': False, 'message': str(e)}

    @database_sync_to_async
    def handle_reprint(self, message):
        from production.models_pipeline import PipelineStageEntry
        from production.services.pipeline_service import PipelineService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        stage_id = message.get('stage_id')
        user_id = message.get('user_id')

        try:
            stage = PipelineStageEntry.objects.select_related(
                'board__production_order__product', 'work_center'
            ).get(id=stage_id)
            user = User.objects.get(id=user_id)

            success, msg, job = PipelineService.reprint_barcodes(stage, user)
            return {
                'type': 'action_result',
                'success': success,
                'message': msg,
                'print_job_id': str(job.id) if job else None,
            }
        except Exception as e:
            return {'type': 'action_result', 'success': False, 'message': str(e)}

    @database_sync_to_async
    def handle_report_issue(self, message):
        """Handle issue reporting from kiosk interface."""
        from production.models_pipeline import PipelineStageEntry, ProductionIssue
        from django.contrib.auth import get_user_model

        User = get_user_model()
        stage_id = message.get('stage_id')
        user_id = message.get('user_id')

        try:
            stage = PipelineStageEntry.objects.select_related(
                'board__production_order', 'work_center',
            ).get(id=stage_id)
            user = User.objects.get(id=user_id)

            issue = ProductionIssue.objects.create(
                production_order=stage.board.production_order,
                stage_entry=stage,
                work_center=stage.work_center,
                category=message.get('category', 'other'),
                severity=message.get('severity', 'medium'),
                title=message.get('title', f'مشكلة في {stage.work_center.name}'),
                description=message.get('description', ''),
                units_affected=int(message.get('units_affected', 0)),
                reported_by=user,
            )

            # Update stage status to failed if severity is critical
            if issue.severity == 'critical':
                stage.status = 'failed'
                stage.failure_reason = issue.title
                stage.failure_category = issue.category
                stage.save(update_fields=['status', 'failure_reason', 'failure_category'])

            return {
                'type': 'action_result',
                'success': True,
                'message': f'تم تسجيل المشكلة: {issue.title}',
                'issue_data': {
                    'id': issue.id,
                    'title': issue.title,
                    'category': issue.category,
                    'severity': issue.severity,
                    'work_center': stage.work_center.name,
                    'order_number': stage.board.production_order.number,
                },
            }
        except Exception as e:
            return {'type': 'action_result', 'success': False, 'message': str(e)}

    @database_sync_to_async
    def get_pipeline_snapshot(self):
        from production.services.pipeline_service import PipelineService
        return PipelineService.get_pipeline_dashboard_data()


class PrintAgentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the thermal printer agent.
    The agent runs on the machine connected to the Zebra/thermal printer.
    """

    PRINT_GROUP = 'print_agent'

    async def connect(self):
        await self.channel_layer.group_add(
            self.PRINT_GROUP,
            self.channel_name,
        )
        await self.accept()
        logger.info("Print agent connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.PRINT_GROUP,
            self.channel_name,
        )
        logger.info("Print agent disconnected")

    async def receive(self, text_data):
        """Receive print confirmations from the agent."""
        try:
            message = json.loads(text_data)

            if message.get('type') == 'print_result':
                job_id = message.get('job_id')
                success = message.get('success', False)
                error = message.get('error', '')

                if success:
                    await self.confirm_print(job_id)
                else:
                    await self.mark_print_failed(job_id, error)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Invalid print agent message: {e}")

    async def print_command(self, event):
        """Send print command to the agent."""
        await self.send(text_data=json.dumps({
            'type': 'print',
            'data': event['data'],
        }))

    @database_sync_to_async
    def confirm_print(self, job_id):
        from production.services.pipeline_service import PipelineService
        return PipelineService.confirm_print_completed(job_id)

    @database_sync_to_async
    def mark_print_failed(self, job_id, error):
        from production.models_pipeline import PipelinePrintJob
        try:
            job = PipelinePrintJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = error
            job.save(update_fields=['status', 'error_message'])

            stage = job.stage_entry
            stage.print_status = 'print_error'
            stage.save(update_fields=['print_status'])
        except PipelinePrintJob.DoesNotExist:
            pass
