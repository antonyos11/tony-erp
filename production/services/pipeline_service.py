"""
خدمة خط أنابيب الإنتاج العالمي
Global Production Pipeline Service

المسؤوليات:
- إنشاء لوحات الأنابيب تلقائياً
- إدارة انتقال المراحل
- إطلاق أحداث WebSocket
- تكامل الطباعة عند المرحلة الأخيرة
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from production.models import (
    ProductionOrder, ProductionWorkCenter, ProductionOrderStage,
    BillOfMaterials, FinishedGoodUnit,
)
from production.models_pipeline import (
    PipelineBoard, PipelineStageEntry, PipelinePrintJob,
    PipelineStageStatus,
)

logger = logging.getLogger(__name__)


class PipelineService:
    """خدمة إدارة خط أنابيب الإنتاج"""

    # ──────────────────────────────────────────────
    # Board Creation
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_board_for_order(
        production_order: ProductionOrder,
    ) -> Tuple[bool, str, Optional[PipelineBoard]]:
        """
        إنشاء لوحة أنابيب لأمر إنتاج.
        يتم إنشاء مرحلة لكل مركز عمل مرتبط بالأمر عبر BOM stages.
        """
        if hasattr(production_order, 'pipeline_board'):
            try:
                board = production_order.pipeline_board
                return True, "اللوحة موجودة مسبقاً", board
            except PipelineBoard.DoesNotExist:
                pass

        board = PipelineBoard.objects.create(
            production_order=production_order
        )

        # Collect work centers from BOM stages or order stages
        work_centers = PipelineService._resolve_work_centers(production_order)

        if not work_centers:
            # Fallback: use all active work centers in sequence
            work_centers = list(
                ProductionWorkCenter.objects.filter(
                    is_active=True
                ).order_by('id')
            )

        for seq, wc in enumerate(work_centers, start=1):
            status = PipelineStageStatus.WAITING
            if seq == 1:
                # First stage is immediately "ready"
                status = PipelineStageStatus.READY

            PipelineStageEntry.objects.create(
                board=board,
                work_center=wc,
                sequence=seq,
                status=status,
            )

        logger.info(
            f"Created pipeline board for order {production_order.number} "
            f"with {len(work_centers)} stages"
        )
        return True, "تم إنشاء لوحة الأنابيب بنجاح", board

    @staticmethod
    def _resolve_work_centers(
        production_order: ProductionOrder,
    ) -> List[ProductionWorkCenter]:
        """
        استخراج مراكز العمل من مراحل أمر الإنتاج أو BOM
        """
        centers = []
        seen_ids = set()

        # Try from ProductionOrderStage
        order_stages = ProductionOrderStage.objects.filter(
            production_order=production_order
        ).select_related('stage__work_center').order_by('stage__sequence')

        for os in order_stages:
            wc = getattr(os.stage, 'work_center', None)
            if wc and wc.id not in seen_ids:
                centers.append(wc)
                seen_ids.add(wc.id)

        if centers:
            return centers

        # Fallback: BOM stages
        if production_order.bom:
            try:
                for bom_stage in production_order.bom.stages.all().order_by('sequence'):
                    wc = getattr(bom_stage.stage, 'work_center', None) if hasattr(bom_stage, 'stage') else None
                    if wc and wc.id not in seen_ids:
                        centers.append(wc)
                        seen_ids.add(wc.id)
            except Exception:
                pass

        return centers

    # ──────────────────────────────────────────────
    # Stage Transitions
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def start_stage(
        stage_entry: PipelineStageEntry,
        user: User,
    ) -> Tuple[bool, str]:
        """بدء العمل في مرحلة"""
        if stage_entry.status not in (
            PipelineStageStatus.READY,
            PipelineStageStatus.FAILED,  # allow restart after failure
        ):
            return False, f"لا يمكن بدء المرحلة، الحالة الحالية: {stage_entry.get_status_display()}"

        # Check previous stage is completed
        prev = PipelineStageEntry.objects.filter(
            board=stage_entry.board,
            sequence__lt=stage_entry.sequence,
        ).order_by('-sequence').first()

        if prev and prev.status != PipelineStageStatus.COMPLETED:
            return False, "المرحلة السابقة لم تكتمل بعد"

        stage_entry.status = PipelineStageStatus.IN_PROGRESS
        stage_entry.started_at = timezone.now()
        stage_entry.started_by = user
        stage_entry.failure_reason = ''
        stage_entry.failure_category = ''
        stage_entry.save()

        # Send real-time update
        PipelineService._broadcast_stage_update(stage_entry, 'stage_started')

        logger.info(
            f"Stage {stage_entry.work_center.name} started for "
            f"order {stage_entry.board.production_order.number} by {user.username}"
        )
        return True, "تم بدء المرحلة بنجاح"

    @staticmethod
    @transaction.atomic
    def complete_stage(
        stage_entry: PipelineStageEntry,
        user: User,
    ) -> Tuple[bool, str, Dict]:
        """
        إكمال مرحلة — ينشط المرحلة التالية تلقائياً.
        إذا كانت المرحلة الأخيرة → يُطلق توليد الباركود والطباعة.
        """
        if stage_entry.status != PipelineStageStatus.IN_PROGRESS:
            return (
                False,
                f"لا يمكن إكمال المرحلة، الحالة: {stage_entry.get_status_display()}",
                {},
            )

        stage_entry.status = PipelineStageStatus.COMPLETED
        stage_entry.completed_at = timezone.now()
        stage_entry.completed_by = user
        stage_entry.save()

        result: Dict = {
            'stage_completed': stage_entry.work_center.name,
            'is_final': False,
            'print_job_id': None,
        }

        # Activate next stage
        next_stage = PipelineStageEntry.objects.filter(
            board=stage_entry.board,
            sequence__gt=stage_entry.sequence,
        ).order_by('sequence').first()

        if next_stage:
            next_stage.status = PipelineStageStatus.READY
            next_stage.save()
            PipelineService._broadcast_stage_update(next_stage, 'stage_ready')
            result['next_stage'] = next_stage.work_center.name
        else:
            # This was the FINAL stage → trigger barcode + print
            result['is_final'] = True
            stage_entry.print_status = 'pending'
            stage_entry.save(update_fields=['print_status'])

            print_job = PipelineService._trigger_final_stage_actions(
                stage_entry, user
            )
            if print_job:
                result['print_job_id'] = str(print_job.id)

        # Recalculate board progress
        stage_entry.board.recalculate_progress()

        # Broadcast
        PipelineService._broadcast_stage_update(stage_entry, 'stage_completed')

        logger.info(
            f"Stage {stage_entry.work_center.name} completed for "
            f"order {stage_entry.board.production_order.number}"
        )
        return True, "تم إكمال المرحلة بنجاح", result

    @staticmethod
    @transaction.atomic
    def fail_stage(
        stage_entry: PipelineStageEntry,
        user: User,
        reason: str,
        category: str = 'other',
    ) -> Tuple[bool, str]:
        """تسجيل توقف/عطل في مرحلة"""
        if stage_entry.status != PipelineStageStatus.IN_PROGRESS:
            return False, "المرحلة ليست قيد التنفيذ"

        stage_entry.status = PipelineStageStatus.FAILED
        stage_entry.failure_reason = reason
        stage_entry.failure_category = category
        stage_entry.save()

        # Broadcast failure to ALL columns
        PipelineService._broadcast_stage_update(stage_entry, 'stage_failed')

        logger.warning(
            f"Stage {stage_entry.work_center.name} FAILED for "
            f"order {stage_entry.board.production_order.number}: {reason}"
        )
        return True, "تم تسجيل العطل"

    # ──────────────────────────────────────────────
    # Final Stage: Barcode Generation + Printing
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def _trigger_final_stage_actions(
        stage_entry: PipelineStageEntry,
        user: User,
    ) -> Optional[PipelinePrintJob]:
        """
        عند إكمال المرحلة الأخيرة (التغليف):
        1. توليد باركود فريد لكل وحدة
        2. إنشاء/تحديث سجلات الضمان
        3. إرسال أمر الطباعة
        4. تحديث المخزون → المنتجات التامة
        """
        from production.services.inventory_integration import ProductionInventoryService

        order = stage_entry.board.production_order
        product = order.product

        # 1. Generate barcodes for finished units
        quantity = int(order.produced_quantity or order.planned_quantity)
        sku = getattr(product, 'sku', '') or getattr(product, 'code', '') or str(product.id)
        production_date = timezone.now().strftime('%Y%m%d')

        units = FinishedGoodUnit.objects.filter(production_order=order)
        if not units.exists():
            # Generate units if not already created
            try:
                success, msg, generated_units = (
                    ProductionInventoryService.generate_barcodes_for_finished_goods(
                        order, quantity
                    )
                )
                if success:
                    units = FinishedGoodUnit.objects.filter(production_order=order)
                else:
                    logger.error(f"Failed to generate barcodes: {msg}")
                    stage_entry.print_status = 'print_error'
                    stage_entry.save(update_fields=['print_status'])
                    return None
            except Exception as e:
                logger.error(f"Error generating barcodes: {e}")
                stage_entry.print_status = 'print_error'
                stage_entry.save(update_fields=['print_status'])
                return None

        # 2. Build ZPL commands for all units
        zpl_commands = []
        barcode_data_list = []

        for unit in units:
            barcode_content = f"{sku}-{production_date}-{order.id}-{unit.unit_serial}"
            barcode_data_list.append(barcode_content)

            zpl = PipelineService._generate_zpl_label(
                barcode_content=barcode_content,
                product_name=product.name,
                sku=sku,
                serial=unit.unit_serial,
                production_date=production_date,
                order_number=order.number,
            )
            zpl_commands.append(zpl)

        combined_zpl = '\n'.join(zpl_commands)
        combined_barcode_data = '\n'.join(barcode_data_list)

        # 3. Create print job
        print_job = PipelinePrintJob.objects.create(
            stage_entry=stage_entry,
            production_order=order,
            barcode_data=combined_barcode_data,
            zpl_command=combined_zpl,
            copies=1,
            status='queued',
            requested_by=user,
        )

        # 4. Update stage print status
        stage_entry.print_status = 'printing'
        stage_entry.save(update_fields=['print_status'])

        # 5. Link warranty if ProductWarranty policy exists
        PipelineService._ensure_warranty_records(order, units)

        # 6. Send print command via WebSocket to print agent
        PipelineService._send_print_to_agent(print_job)

        # 7. Broadcast print status
        PipelineService._broadcast_stage_update(stage_entry, 'printing_started')

        return print_job

    @staticmethod
    def _generate_zpl_label(
        barcode_content: str,
        product_name: str,
        sku: str,
        serial: str,
        production_date: str,
        order_number: str,
    ) -> str:
        """
        توليد أمر ZPL لطابعة Zebra الحرارية
        Uses PrintTemplate if a default template exists, otherwise falls back to hardcoded ZPL.
        """
        # Try to use a configured template first
        try:
            from printing.models import PrintTemplate
            template = PrintTemplate.objects.filter(
                template_type='production_label',
                is_default=True,
                is_active=True,
            ).first()

            if template and template.zpl_template:
                return template.render_zpl({
                    'barcode_content': barcode_content,
                    'product_name': product_name[:30],
                    'sku': sku,
                    'serial': serial,
                    'production_date': production_date,
                    'order_number': order_number,
                })
        except Exception:
            pass  # Fall back to hardcoded ZPL

        # Truncate product name for label
        display_name = product_name[:30] if len(product_name) > 30 else product_name

        zpl = (
            "^XA\n"
            "^CF0,30\n"
            f"^FO50,30^FD{display_name}^FS\n"
            "^CF0,22\n"
            f"^FO50,70^FDSKU: {sku}^FS\n"
            f"^FO50,100^FDS/N: {serial}^FS\n"
            f"^FO50,130^FDOrder: {order_number}^FS\n"
            f"^FO50,160^FDDate: {production_date}^FS\n"
            "^BY3,2,100\n"
            f"^FO50,200^BC^FD{barcode_content}^FS\n"
            f"^FO50,330^BQ,2,5^FDQA,{barcode_content}^FS\n"
            "^XZ"
        )
        return zpl

    @staticmethod
    def _ensure_warranty_records(order, units):
        """ربط/إنشاء سجلات الضمان للوحدات"""
        try:
            from ecommerce.models import ProductWarranty

            # Find applicable warranty policy
            product = order.product
            warranty_policy = ProductWarranty.objects.filter(
                product__product=product,
                is_active=True,
            ).first()

            if not warranty_policy:
                # Try any active policy
                warranty_policy = ProductWarranty.objects.filter(
                    is_active=True
                ).first()

            if not warranty_policy:
                logger.info(f"No warranty policy found for order {order.number}")
                return

            for unit in units:
                # Skip if warranty already set on unit
                if unit.warranty_policy_id:
                    continue
                unit.warranty_policy = warranty_policy
                unit.save(update_fields=['warranty_policy'])

        except Exception as e:
            logger.warning(f"Could not link warranty for order {order.number}: {e}")

    @staticmethod
    def reprint_barcodes(
        stage_entry: PipelineStageEntry,
        user: User,
    ) -> Tuple[bool, str, Optional[PipelinePrintJob]]:
        """
        إعادة طباعة الباركود (في حالة انحشار الورق أو خطأ الطابعة)
        """
        last_job = PipelinePrintJob.objects.filter(
            stage_entry=stage_entry
        ).order_by('-created_at').first()

        if not last_job:
            return False, "لا توجد مهمة طباعة سابقة", None

        # Create new print job with same data
        new_job = PipelinePrintJob.objects.create(
            stage_entry=stage_entry,
            production_order=last_job.production_order,
            barcode_data=last_job.barcode_data,
            zpl_command=last_job.zpl_command,
            copies=1,
            status='queued',
            requested_by=user,
        )

        stage_entry.print_status = 'printing'
        stage_entry.save(update_fields=['print_status'])

        PipelineService._send_print_to_agent(new_job)
        PipelineService._broadcast_stage_update(stage_entry, 'reprinting')

        return True, "تم إرسال أمر إعادة الطباعة", new_job

    # ──────────────────────────────────────────────
    # Print Agent Communication
    # ──────────────────────────────────────────────

    @staticmethod
    def _send_print_to_agent(print_job: PipelinePrintJob):
        """إرسال أمر الطباعة عبر WebSocket إلى وكيل الطباعة"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer is None:
                logger.warning("No channel layer configured; print job queued only.")
                return

            async_to_sync(channel_layer.group_send)(
                'print_agent',
                {
                    'type': 'print.command',
                    'data': {
                        'job_id': str(print_job.id),
                        'zpl': print_job.zpl_command,
                        'copies': print_job.copies,
                        'order_number': print_job.production_order.number,
                    },
                },
            )

            print_job.status = 'sent'
            print_job.save(update_fields=['status'])

        except Exception as e:
            logger.error(f"Failed to send print command: {e}")
            print_job.status = 'failed'
            print_job.error_message = str(e)
            print_job.save(update_fields=['status', 'error_message'])

    @staticmethod
    def confirm_print_completed(job_id: str) -> Tuple[bool, str]:
        """
        تأكيد اكتمال الطباعة (يُستدعى من وكيل الطباعة عبر WebSocket)
        """
        try:
            job = PipelinePrintJob.objects.select_related(
                'stage_entry__board__production_order'
            ).get(id=job_id)
        except PipelinePrintJob.DoesNotExist:
            return False, "مهمة الطباعة غير موجودة"

        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at'])

        # Update stage print status
        stage = job.stage_entry
        stage.print_status = 'printed'
        stage.save(update_fields=['print_status'])

        # Move inventory to finished goods location
        order = stage.board.production_order
        PipelineService._move_to_finished_goods(order)

        # Broadcast final update
        PipelineService._broadcast_stage_update(stage, 'print_completed')

        return True, "تم تأكيد الطباعة بنجاح"

    @staticmethod
    def _move_to_finished_goods(production_order: ProductionOrder):
        """نقل المنتج إلى مخزن المنتجات التامة (type='finished')"""
        from inventory.models import Location, Stock

        try:
            finished_location = Location.objects.filter(
                type='finished'
            ).first()

            if not finished_location:
                finished_location = Location.objects.filter(
                    name__icontains='تام'
                ).first()

            if not finished_location:
                logger.warning("No finished goods location found")
                return

            # Ensure stock record exists
            Stock.objects.get_or_create(
                product=production_order.product,
                location=finished_location,
                defaults={'quantity': Decimal('0')},
            )

            logger.info(
                f"Order {production_order.number} inventory confirmed at "
                f"finished location: {finished_location.name}"
            )

        except Exception as e:
            logger.error(f"Error moving to finished goods: {e}")

    # ──────────────────────────────────────────────
    # WebSocket Broadcasting
    # ──────────────────────────────────────────────

    @staticmethod
    def _broadcast_stage_update(
        stage_entry: PipelineStageEntry,
        event_type: str,
    ):
        """بث تحديث المرحلة عبر WebSocket إلى جميع المتصلين"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer is None:
                return

            board = stage_entry.board
            order = board.production_order

            payload = {
                'type': 'pipeline.stage.update',
                'data': {
                    'event': event_type,
                    'order_id': order.id,
                    'order_number': order.number,
                    'product_name': order.product.name,
                    'stage_id': stage_entry.id,
                    'work_center_id': stage_entry.work_center_id,
                    'work_center_name': stage_entry.work_center.name,
                    'status': stage_entry.status,
                    'sequence': stage_entry.sequence,
                    'failure_reason': stage_entry.failure_reason,
                    'failure_category': stage_entry.failure_category,
                    'print_status': stage_entry.print_status,
                    'overall_progress': float(board.overall_progress),
                    'timestamp': timezone.now().isoformat(),
                },
            }

            async_to_sync(channel_layer.group_send)(
                'production_pipeline',
                payload,
            )

        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

    # ──────────────────────────────────────────────
    # Dashboard Data
    # ──────────────────────────────────────────────

    @staticmethod
    def get_pipeline_dashboard_data() -> Dict:
        """
        بيانات لوحة خط الأنابيب الكاملة
        """
        active_boards = PipelineBoard.objects.filter(
            is_active=True,
        ).select_related(
            'production_order__product',
        ).prefetch_related(
            'stage_entries__work_center',
            'stage_entries__started_by',
            'stage_entries__completed_by',
        ).order_by('-created_at')

        # All active work centers as columns
        work_centers = ProductionWorkCenter.objects.filter(
            is_active=True
        ).order_by('id')

        columns = []
        for wc in work_centers:
            columns.append({
                'id': wc.id,
                'name': wc.name,
                'type': wc.work_center_type,
                'code': wc.code,
            })

        boards_data = []
        for board in active_boards:
            order = board.production_order
            sku = (
                getattr(order.product, 'sku', '')
                or getattr(order.product, 'code', '')
                or str(order.product.id)
            )

            stages_data = []
            for entry in board.stage_entries.all():
                stages_data.append({
                    'id': entry.id,
                    'work_center_id': entry.work_center_id,
                    'work_center_name': entry.work_center.name,
                    'sequence': entry.sequence,
                    'status': entry.status,
                    'status_display': entry.get_status_display(),
                    'started_at': entry.started_at.isoformat() if entry.started_at else None,
                    'completed_at': entry.completed_at.isoformat() if entry.completed_at else None,
                    'started_by': entry.started_by.get_full_name() if entry.started_by else None,
                    'completed_by': entry.completed_by.get_full_name() if entry.completed_by else None,
                    'failure_reason': entry.failure_reason,
                    'failure_category': entry.failure_category,
                    'print_status': entry.print_status,
                    'is_final': entry.is_final_stage,
                    'duration_minutes': entry.duration_minutes,
                })

            boards_data.append({
                'id': board.id,
                'order_id': order.id,
                'order_number': order.number,
                'product_name': order.product.name,
                'product_sku': sku,
                'planned_quantity': float(order.planned_quantity),
                'produced_quantity': float(order.produced_quantity),
                'overall_progress': float(board.overall_progress),
                'stages': stages_data,
            })

        return {
            'columns': columns,
            'boards': boards_data,
            'timestamp': timezone.now().isoformat(),
        }
