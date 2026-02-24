"""
مهام Celery للوحة الأساسية
"""
from celery import shared_task
from typing import Optional
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import os
import shutil
import logging
from pathlib import Path
from django.conf import settings
from django.db import transaction
import json

from core.models import AuditLog

logger = logging.getLogger(__name__)


@shared_task
def create_daily_backup():
    """إنشاء نسخة احتياطية يومية تلقائية"""
    try:
        logger.info("بدء إنشاء النسخة الاحتياطية اليومية")
        
        # إنشاء اسم النسخة الاحتياطية
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"auto_backup_{timestamp}"
        
        # تشغيل أمر النسخ الاحتياطي
        call_command('backup_now', name=backup_name, include_media=True)
        
        logger.info(f"تم إنشاء النسخة الاحتياطية بنجاح: {backup_name}")
        return f"تم إنشاء النسخة الاحتياطية: {backup_name}"
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
        raise


@shared_task
def cleanup_old_logs():
    """تنظيف ملفات السجلات القديمة"""
    try:
        logger.info("بدء تنظيف السجلات القديمة")
        
        logs_dir = Path(settings.BASE_DIR) / 'logs'
        if not logs_dir.exists():
            return "مجلد السجلات غير موجود"
        
        # حذف السجلات الأقدم من 30 يوم
        cutoff_time = timezone.now() - timedelta(days=30)
        deleted_files = 0
        
        for log_file in logs_dir.glob('*.log.*'):  # ملفات السجلات المضغوطة
            try:
                file_time = timezone.datetime.fromtimestamp(
                    log_file.stat().st_mtime, 
                    tz=timezone.get_current_timezone()
                )
                if file_time < cutoff_time:
                    log_file.unlink()
                    deleted_files += 1
                    logger.info(f"تم حذف ملف السجل: {log_file.name}")
            except Exception as e:
                logger.warning(f"لا يمكن حذف ملف السجل {log_file.name}: {e}")
        
        logger.info(f"تم تنظيف السجلات، تم حذف {deleted_files} ملف")
        return f"تم حذف {deleted_files} ملف سجل قديم"
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف السجلات: {str(e)}")
        raise


@shared_task
def purge_old_audit_logs(days: Optional[int] = None, batch_size: int = 5000):
    """حذف سجلات التدقيق الأقدم من مدة الاحتفاظ المحددة لتقليل حجم القاعدة.
    days: إن لم تُحدد، تُستخدم القيمة من الإعداد BACKUP_RETENTION_DAYS أو 30.
    """
    try:
        keep_days = days
        if not keep_days:
            try:
                from core.models import AppSettings
                keep_days = AppSettings.get().audit_retention_days or 90
            except Exception:
                keep_days = getattr(settings, 'BACKUP_RETENTION_DAYS', 30)
        cutoff = timezone.now() - timedelta(days=keep_days)
        total_deleted = 0
        while True:
            ids = list(
                AuditLog.objects.filter(created_at__lt=cutoff).values_list('id', flat=True)[:batch_size]
            )
            if not ids:
                break
            with transaction.atomic():
                deleted, _ = AuditLog.objects.filter(id__in=ids).delete()
                total_deleted += deleted
        logger.info(f"تم حذف {total_deleted} سجل تدقيق أقدم من {keep_days} يوماً")
        return total_deleted
    except Exception as e:
        logger.error(f"خطأ في حذف سجلات التدقيق القديمة: {str(e)}")
        raise


@shared_task
def archive_old_audit_logs(days: Optional[int] = None, delete: bool = False, batch_size: int = 5000):
    """أرشفة سجلات التدقيق الأقدم من عدد الأيام المحدد إلى ملف JSONL في مجلد backups/audit_archives.
    أيام الأرشفة: إما معامل days أو AppSettings.audit_retention_days (افتراضي 90).
    delete: إذا True سيتم حذف السجلات بعد الأرشفة (يُنصح بالاستخدام في بيئات الإنتاج فقط بعد التحقق من النسخ الاحتياطي).
    ترجع عدد السجلات التي تمت أرشفتها.
    """
    try:
        try:
            from core.models import AppSettings
            retention = days or AppSettings.get().audit_retention_days or 90
        except Exception:
            retention = days or 90
        cutoff = timezone.now() - timedelta(days=retention)
        qs = AuditLog.objects.filter(created_at__lt=cutoff).order_by('id')
        if not qs.exists():
            logger.info("لا توجد سجلات لتتم أرشفتها")
            return 0
        archive_dir = Path(settings.BASE_DIR) / 'backups' / 'audit_archives'
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        out_file = archive_dir / f'audit_archive_{retention}d_{stamp}.jsonl'
        written = 0
        while True:
            ids = list(qs.values_list('id', flat=True)[:batch_size])
            if not ids:
                break
            rows = list(AuditLog.objects.filter(id__in=ids))
            with out_file.open('a', encoding='utf-8') as f:
                for log in rows:
                    f.write(json.dumps({
                        'id': log.id,
                        'user_id': log.user_id,
                        'action': log.action,
                        'app_label': log.app_label,
                        'model_name': log.model_name,
                        'object_id': log.object_id,
                        'object_repr': log.object_repr,
                        'changes': log.changes,
                        'ip_address': log.ip_address,
                        'user_agent': log.user_agent,
                        'created_at': log.created_at.isoformat(),
                    }, ensure_ascii=False) + '\n')
                    written += 1
            if delete:
                AuditLog.objects.filter(id__in=ids).delete()
        logger.info(f"تم أرشفة {written} سجل تدقيق إلى {out_file} (حذف بعد الأرشفة={delete})")
        return written
    except Exception as e:
        logger.error(f"خطأ في أرشفة سجلات التدقيق: {e}")
        raise


@shared_task
def system_health_check():
    """فحص دوري لصحة النظام"""
    try:
        logger.info("بدء فحص صحة النظام")
        
        # تشغيل فحص النظام
        call_command('system_self_check')
        
        logger.info("تم فحص النظام بنجاح")
        return "فحص النظام مكتمل"
        
    except Exception as e:
        logger.error(f"فشل فحص النظام: {str(e)}")
        # إرسال تنبيه للمديرين (يمكن إضافته لاحقاً)
        raise


@shared_task
def cleanup_temp_files():
    """تنظيف الملفات المؤقتة"""
    try:
        logger.info("بدء تنظيف الملفات المؤقتة")
        
        # تنظيف ملفات Python المؤقتة
        base_dir = Path(settings.BASE_DIR)
        deleted_files = 0
        
        # حذف ملفات __pycache__
        for pycache_dir in base_dir.rglob('__pycache__'):
            try:
                shutil.rmtree(pycache_dir)
                deleted_files += 1
            except Exception as e:
                logger.warning(f"لا يمكن حذف {pycache_dir}: {e}")
        
        # حذف ملفات .pyc
        for pyc_file in base_dir.rglob('*.pyc'):
            try:
                pyc_file.unlink()
                deleted_files += 1
            except Exception as e:
                logger.warning(f"لا يمكن حذف {pyc_file}: {e}")
        
        logger.info(f"تم تنظيف {deleted_files} ملف مؤقت")
        return f"تم تنظيف {deleted_files} ملف مؤقت"
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف الملفات المؤقتة: {str(e)}")
        raise


@shared_task
def generate_system_report():
    """إنشاء تقرير دوري عن حالة النظام"""
    try:
        logger.info("بدء إنشاء تقرير النظام")
        
        # جمع إحصائيات النظام
        from django.contrib.auth.models import User
        from django.contrib.sessions.models import Session
        
        stats = {
            'timestamp': timezone.now().isoformat(),
            'users_count': User.objects.count(),
            'active_users_count': User.objects.filter(is_active=True).count(),
        }
        
        # إحصائيات الجلسات النشطة (ORM بدلاً من SQL خام)
        stats['active_sessions'] = Session.objects.filter(
            expire_date__gte=timezone.now()
        ).count()
        
        # حفظ التقرير (يمكن إرساله بالبريد أو حفظه في ملف)
        logger.info(f"تقرير النظام: {stats}")
        
        return f"تم إنشاء تقرير النظام في {stats['timestamp']}"
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء تقرير النظام: {str(e)}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_system_notifications(self):
    """إرسال التنبيهات النظامية المعلقة"""
    try:
        logger.info("فحص التنبيهات المعلقة")

        sent_count = 0
        errors = 0

        # 1. تنبيهات انتهاء صلاحية اللوتات
        try:
            from inventory.models_advanced import LotTracking
            warning_date = timezone.now().date() + timedelta(days=7)
            expiring = LotTracking.objects.filter(
                expiry_date__lte=warning_date,
                expiry_date__gte=timezone.now().date(),
                current_quantity__gt=0,
                is_active=True,
            ).select_related('product')[:20]

            for lot in expiring:
                try:
                    from notifications.models import Notification
                    Notification.objects.get_or_create(
                        notification_type='system',
                        title=f'تنبيه صلاحية: لوت #{lot.lot_number}',
                        defaults={
                            'message': (
                                f'المنتج {lot.product} - اللوت #{lot.lot_number} '
                                f'ينتهي خلال {lot.days_until_expiry} يوم'
                            ),
                            'priority': 'high',
                        }
                    )
                    sent_count += 1
                except Exception as e:
                    logger.debug(f"تنبيه لوت: {e}")
        except ImportError:
            pass

        # 2. تنبيهات المخزون المنخفض
        try:
            from inventory.models import Product
            from django.db import models as db_models
            low_stock = Product.objects.filter(
                is_active=True,
            ).extra(
                where=['quantity <= minimum_stock']
            )[:20]

            for product in low_stock:
                try:
                    from notifications.models import Notification
                    Notification.objects.get_or_create(
                        notification_type='system',
                        title=f'مخزون منخفض: {product.name}',
                        defaults={
                            'message': f'الكمية الحالية: {product.quantity}',
                            'priority': 'medium',
                        }
                    )
                    sent_count += 1
                except Exception as e:
                    logger.debug(f"تنبيه مخزون: {e}")
        except (ImportError, Exception):
            pass

        # 3. فحص الموافقات المعلقة
        try:
            from approvals.models import ApprovalRequest
            pending = ApprovalRequest.objects.filter(
                status='pending',
                created_at__lte=timezone.now() - timedelta(days=3)
            ).count()
            if pending > 0:
                logger.info(f"يوجد {pending} طلب موافقة معلق منذ أكثر من 3 أيام")
        except (ImportError, Exception):
            pass

        logger.info(f"تم إرسال {sent_count} تنبيه ({errors} خطأ)")
        return f"تم إرسال {sent_count} تنبيه"

    except Exception as exc:
        logger.error(f"خطأ في إرسال التنبيهات: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task
def send_audit_alert(audit_id: int, rule_name: Optional[str] = None):
    """إرسال تنبيه عند توافق سجل تدقيق مع قواعد محددة في الإعدادات.
    يرسل بريدًا إلى ADMINS إن تم ضبطه، ويسجّل الحدث في السجل.
    """
    try:
        audit = AuditLog.objects.select_related('user').filter(id=audit_id).first()
        if not audit:
            return 'audit not found'
        subject = f"[AUDIT ALERT]{' ' + rule_name if rule_name else ''}: {audit.app_label}.{audit.model_name} {audit.action}"
        body = (
            f"التاريخ: {audit.created_at:%Y-%m-%d %H:%M:%S}\n"
            f"المستخدم: {getattr(audit.user, 'username', '-') }\n"
            f"الكائن: {audit.app_label}.{audit.model_name} (id={audit.object_id})\n"
            f"الوصف: {audit.object_repr}\n"
            f"IP: {audit.ip_address}\n"
            f"التغييرات: {audit.changes}\n"
        )
        logger.warning(subject + "\n" + body)
        # إرسال بريد إذا كانت الإعدادات متاحة
        try:
            from django.core.mail import mail_admins
            mail_admins(subject, body, fail_silently=True)
        except Exception:
            pass
        return 'ok'
    except Exception as e:
        logger.error(f"خطأ في إرسال تنبيه التدقيق: {str(e)}")
        raise


# ============================================================
# مهام النماذج المتقدمة - Advanced Model Tasks
# ============================================================

@shared_task
def check_stock_alerts():
    """
    فحص تنبيهات المخزون وتشغيلها
    يُفضل تشغيلها كل 30 دقيقة
    """
    try:
        from inventory.models_advanced import StockAlert
        alerts = StockAlert.objects.filter(is_active=True).select_related('product')
        triggered = 0
        for alert in alerts:
            if alert.check_and_trigger():
                triggered += 1
                logger.info(
                    f"تنبيه مخزون: {alert.get_alert_type_display()} "
                    f"- {alert.product}"
                )
        logger.info(f"فحص تنبيهات المخزون: {triggered} تنبيه نشط من {alerts.count()}")
        return triggered
    except Exception as e:
        logger.error(f"خطأ في فحص تنبيهات المخزون: {e}")
        return 0


@shared_task
def check_overdue_approvals():
    """
    فحص طلبات الموافقة المتأخرة وتصعيدها
    يُفضل تشغيلها كل ساعة
    """
    try:
        from accounts.services import ApprovalService
        escalated = ApprovalService.check_overdue_requests()
        logger.info(f"فحص الموافقات المتأخرة: {escalated} طلب تم تصعيده")
        return escalated
    except Exception as e:
        logger.error(f"خطأ في فحص الموافقات المتأخرة: {e}")
        return 0


@shared_task
def execute_followup_rules():
    """
    تنفيذ قواعد المتابعة التلقائية
    يُفضل تشغيلها كل يوم صباحاً
    """
    try:
        from crm.models_advanced import FollowUpRule, FollowUpLog
        from crm.models import Customer

        rules = FollowUpRule.objects.filter(is_active=True)
        executed = 0

        for rule in rules:
            try:
                if rule.trigger == 'no_activity_days':
                    threshold_date = timezone.now() - timedelta(days=rule.days_after)
                    inactive_customers = Customer.objects.filter(
                        last_contact_date__lt=threshold_date
                    ).exclude(
                        followup_logs__rule=rule,
                        followup_logs__executed_at__gt=threshold_date
                    )[:50]

                    for customer in inactive_customers:
                        FollowUpLog.objects.create(
                            rule=rule,
                            customer=customer,
                            result='success',
                            details=f'عدم نشاط منذ {customer.last_contact_date}'
                        )
                        executed += 1

                rule.execution_count += executed
                rule.last_executed = timezone.now()
                rule.save(update_fields=['execution_count', 'last_executed'])

            except Exception as e:
                logger.error(f"خطأ في تنفيذ قاعدة {rule.name}: {e}")
                FollowUpLog.objects.create(
                    rule=rule,
                    result='failed',
                    details=str(e)
                )

        logger.info(f"تنفيذ قواعد المتابعة: {executed} إجراء")
        return executed
    except Exception as e:
        logger.error(f"خطأ في تنفيذ قواعد المتابعة: {e}")
        return 0


@shared_task
def recalculate_lead_scores():
    """
    إعادة حساب تقييم العملاء
    يُفضل تشغيلها كل أسبوع
    """
    try:
        from crm.models_advanced import LeadScore
        scores = LeadScore.objects.all().select_related('customer')
        updated = 0
        for score in scores:
            old_grade = score.grade
            score.calculate_grade()
            score.save()
            if score.grade != old_grade:
                updated += 1
                logger.info(
                    f"تغيير تصنيف {score.customer}: "
                    f"{old_grade} → {score.grade}"
                )
        logger.info(f"إعادة حساب تقييم العملاء: {updated} تغيير من {scores.count()}")
        return updated
    except Exception as e:
        logger.error(f"خطأ في حساب تقييم العملاء: {e}")
        return 0


@shared_task
def check_expiring_lots():
    """
    فحص اللوتات قرب انتهاء الصلاحية
    يُفضل تشغيلها كل يوم
    """
    try:
        from inventory.models_advanced import LotTracking
        warning_date = timezone.now().date() + timedelta(days=30)

        expiring = LotTracking.objects.filter(
            expiry_date__lte=warning_date,
            expiry_date__gte=timezone.now().date(),
            current_quantity__gt=0,
            is_active=True
        ).select_related('product')

        for lot in expiring:
            logger.warning(
                f"لوت #{lot.lot_number} - {lot.product} "
                f"ينتهي في {lot.days_until_expiry} يوم"
            )

        logger.info(f"لوتات قرب انتهاء الصلاحية: {expiring.count()}")
        return expiring.count()
    except Exception as e:
        logger.error(f"خطأ في فحص اللوتات: {e}")
        return 0