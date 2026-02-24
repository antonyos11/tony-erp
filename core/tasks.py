"""
Tony ERP - Background Tasks
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name='core.backup_database')
def backup_database():
    """نسخ احتياطي للقاعدة"""
    import subprocess, os
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    result = subprocess.run(
        ['pg_dump', '-U', 'tony_erp_user', '-h', 'localhost', 'tony_erp_db',
         '-f', f'/backups/tony-erp/pg_dump_{timestamp}.sql'],
        capture_output=True, text=True,
        env={**os.environ, 'PGPASSWORD': 'T0nyERP_2026_Str0ng!'}
    )
    if result.returncode == 0:
        logger.info(f'Database backup completed: pg_dump_{timestamp}.sql')
        return f'Backup completed: {timestamp}'
    else:
        logger.error(f'Backup failed: {result.stderr}')
        return f'Backup failed: {result.stderr}'


@shared_task(name='core.cleanup_old_sessions')
def cleanup_old_sessions():
    """تنظيف الجلسات القديمة"""
    from django.contrib.sessions.models import Session
    expired = Session.objects.filter(expire_date__lt=timezone.now())
    count = expired.count()
    expired.delete()
    logger.info(f'Cleaned up {count} expired sessions')
    return f'Cleaned {count} sessions'


@shared_task(name='core.daily_report')
def generate_daily_report():
    """تقرير يومي"""
    from django.contrib.auth.models import User
    today = timezone.now().date()
    active_users = User.objects.filter(last_login__date=today).count()
    logger.info(f'Daily report: {active_users} active users today')
    return f'Daily report generated: {active_users} active users'
