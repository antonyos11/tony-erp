"""
Comprehensive Audit Trail System for Accounting Operations
Tracks all changes, user actions, and system events
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AuditTrail(models.Model):
    """
    Main audit trail model to track all accounting operations
    """
    
    ACTION_CHOICES = [
        ('create', 'إنشاء'),
        ('update', 'تعديل'),
        ('delete', 'حذف'),
        ('view', 'عرض'),
        ('post', 'ترحيل'),
        ('reverse', 'عكس'),
        ('approve', 'اعتماد'),
        ('reject', 'رفض'),
        ('export', 'تصدير'),
        ('import', 'استيراد'),
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
    ]
    
    CATEGORY_CHOICES = [
        ('journal_entry', 'قيد محاسبي'),
        ('account', 'حساب'),
        ('cost_center', 'مركز تكلفة'),
        ('customer', 'عميل'),
        ('supplier', 'مورد'),
        ('invoice', 'فاتورة'),
        ('payment', 'دفعة'),
        ('report', 'تقرير'),
        ('system', 'نظام'),
        ('security', 'أمان'),
    ]
    
    # Basic Information
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, db_index=True)
    
    # Object being audited (generic foreign key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Details
    description = models.TextField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    # Technical Information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    request_id = models.CharField(max_length=50, blank=True)
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'accounting_audit_trail'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'user']),
            models.Index(fields=['category', 'action']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.get_category_display()} - {self.timestamp}"


class AuditManager:
    """
    Manager class for creating and managing audit entries
    """
    
    @staticmethod
    def log_journal_entry_creation(user, journal_entry, request=None):
        """Log journal entry creation"""
        try:
            metadata = {
                'entry_number': journal_entry.number,
                'entry_date': journal_entry.date.isoformat() if journal_entry.date else None,
                'total_debit': float(journal_entry.total_debit or 0),
                'total_credit': float(journal_entry.total_credit or 0),
                'items_count': journal_entry.items.count() if hasattr(journal_entry, 'items') else 0,
            }
            
            AuditTrail.objects.create(
                user=user,
                action='create',
                category='journal_entry',
                content_object=journal_entry,
                description=f"تم إنشاء قيد محاسبي رقم {journal_entry.number}",
                new_values=AuditManager._serialize_journal_entry(journal_entry),
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging journal entry creation: {str(e)}")
    
    @staticmethod
    def log_journal_entry_update(user, journal_entry, old_data, request=None):
        """Log journal entry update"""
        try:
            metadata = {
                'entry_number': journal_entry.number,
                'changes_made': AuditManager._identify_changes(old_data, AuditManager._serialize_journal_entry(journal_entry))
            }
            
            AuditTrail.objects.create(
                user=user,
                action='update',
                category='journal_entry',
                content_object=journal_entry,
                description=f"تم تعديل قيد محاسبي رقم {journal_entry.number}",
                old_values=old_data,
                new_values=AuditManager._serialize_journal_entry(journal_entry),
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging journal entry update: {str(e)}")
    
    @staticmethod
    def log_journal_entry_posting(user, journal_entry, request=None):
        """Log journal entry posting"""
        try:
            metadata = {
                'entry_number': journal_entry.number,
                'posted_date': timezone.now().isoformat(),
                'fiscal_year': getattr(journal_entry, 'fiscal_year', None),
            }
            
            AuditTrail.objects.create(
                user=user,
                action='post',
                category='journal_entry',
                content_object=journal_entry,
                description=f"تم ترحيل قيد محاسبي رقم {journal_entry.number}",
                new_values={'is_posted': True, 'posted_date': timezone.now().isoformat()},
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging journal entry posting: {str(e)}")
    
    @staticmethod
    def log_account_creation(user, account, request=None):
        """Log account creation"""
        try:
            metadata = {
                'account_code': account.code,
                'account_type': account.type,
                'parent_account': account.parent.code if account.parent else None,
            }
            
            AuditTrail.objects.create(
                user=user,
                action='create',
                category='account',
                content_object=account,
                description=f"تم إنشاء حساب {account.code} - {account.name}",
                new_values=AuditManager._serialize_account(account),
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging account creation: {str(e)}")
    
    @staticmethod
    def log_security_event(user, event_type, description, request=None, severity='info'):
        """Log security events"""
        try:
            metadata = {
                'event_type': event_type,
                'severity': severity,
                'user_id': user.id if user else None,
                'username': str(user) if user else 'anonymous',
            }
            
            AuditTrail.objects.create(
                user=user,
                action='security',
                category='security',
                description=description,
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
    
    @staticmethod
    def log_system_event(event_type, description, metadata=None):
        """Log system events"""
        try:
            AuditTrail.objects.create(
                action='system',
                category='system',
                description=description,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Error logging system event: {str(e)}")
    
    @staticmethod
    def log_report_access(user, report_type, parameters, request=None):
        """Log report access"""
        try:
            metadata = {
                'report_type': report_type,
                'parameters': parameters,
                'generated_at': timezone.now().isoformat(),
            }
            
            AuditTrail.objects.create(
                user=user,
                action='view',
                category='report',
                description=f"تم الوصول إلى تقرير {report_type}",
                new_values=parameters,
                ip_address=AuditManager._get_ip_from_request(request),
                user_agent=AuditManager._get_user_agent_from_request(request),
                session_key=request.session.session_key if request and hasattr(request, 'session') else '',
                request_id=getattr(request, '_request_id', ''),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error logging report access: {str(e)}")
    
    @staticmethod
    def _serialize_journal_entry(journal_entry):
        """Serialize journal entry for audit trail"""
        try:
            data = {
                'id': journal_entry.id,
                'number': journal_entry.number,
                'date': journal_entry.date.isoformat() if journal_entry.date else None,
                'description': journal_entry.description,
                'total_debit': float(journal_entry.total_debit or 0),
                'total_credit': float(journal_entry.total_credit or 0),
                'is_posted': getattr(journal_entry, 'is_posted', False),
                'entry_type': getattr(journal_entry, 'entry_type', 'manual'),
            }
            
            # Add items if available
            if hasattr(journal_entry, 'items'):
                data['items'] = [
                    {
                        'account_id': item.account.id if item.account else None,
                        'account_code': item.account.code if item.account else None,
                        'account_name': item.account.name if item.account else None,
                        'debit': float(item.debit or 0),
                        'credit': float(item.credit or 0),
                        'description': item.description or '',
                    }
                    for item in journal_entry.items.all()
                ]
            
            return data
            
        except Exception as e:
            logger.error(f"Error serializing journal entry: {str(e)}")
            return {}
    
    @staticmethod
    def _serialize_account(account):
        """Serialize account for audit trail"""
        try:
            return {
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'type': account.type,
                'parent_id': account.parent.id if account.parent else None,
                'parent_code': account.parent.code if account.parent else None,
                'is_active': getattr(account, 'is_active', True),
                'balance': float(getattr(account, 'balance', 0)),
            }
            
        except Exception as e:
            logger.error(f"Error serializing account: {str(e)}")
            return {}
    
    @staticmethod
    def _identify_changes(old_data, new_data):
        """Identify what changed between old and new data"""
        try:
            changes = []
            
            if not old_data or not new_data:
                return changes
            
            for key, new_value in new_data.items():
                old_value = old_data.get(key)
                if old_value != new_value:
                    changes.append({
                        'field': key,
                        'old_value': old_value,
                        'new_value': new_value
                    })
            
            return changes
            
        except Exception as e:
            logger.error(f"Error identifying changes: {str(e)}")
            return []
    
    @staticmethod
    def _get_ip_from_request(request):
        """Get IP address from request"""
        if not request:
            return None
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _get_user_agent_from_request(request):
        """Get user agent from request"""
        if not request:
            return ''
        
        return request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length


class AuditQueryManager:
    """
    Manager for querying audit trail data
    """
    
    @staticmethod
    def get_user_activity(user, days=30):
        """Get user activity for specified days"""
        try:
            since_date = timezone.now() - timezone.timedelta(days=days)
            
            return AuditTrail.objects.filter(
                user=user,
                timestamp__gte=since_date
            ).order_by('-timestamp')
            
        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return AuditTrail.objects.none()
    
    @staticmethod
    def get_object_history(content_object):
        """Get audit history for a specific object"""
        try:
            content_type = ContentType.objects.get_for_model(content_object)
            
            return AuditTrail.objects.filter(
                content_type=content_type,
                object_id=content_object.id
            ).order_by('-timestamp')
            
        except Exception as e:
            logger.error(f"Error getting object history: {str(e)}")
            return AuditTrail.objects.none()
    
    @staticmethod
    def get_security_events(days=7):
        """Get security events for specified days"""
        try:
            since_date = timezone.now() - timezone.timedelta(days=days)
            
            return AuditTrail.objects.filter(
                category='security',
                timestamp__gte=since_date
            ).order_by('-timestamp')
            
        except Exception as e:
            logger.error(f"Error getting security events: {str(e)}")
            return AuditTrail.objects.none()
    
    @staticmethod
    def get_activity_summary(days=30):
        """Get activity summary for dashboard"""
        try:
            since_date = timezone.now() - timezone.timedelta(days=days)
            
            # Get total activities
            total_activities = AuditTrail.objects.filter(
                timestamp__gte=since_date
            ).count()
            
            # Get activities by category
            activities_by_category = {}
            for category, label in AuditTrail.CATEGORY_CHOICES:
                count = AuditTrail.objects.filter(
                    category=category,
                    timestamp__gte=since_date
                ).count()
                if count > 0:
                    activities_by_category[label] = count
            
            # Get activities by action
            activities_by_action = {}
            for action, label in AuditTrail.ACTION_CHOICES:
                count = AuditTrail.objects.filter(
                    action=action,
                    timestamp__gte=since_date
                ).count()
                if count > 0:
                    activities_by_action[label] = count
            
            # Get top users
            top_users = AuditTrail.objects.filter(
                timestamp__gte=since_date,
                user__isnull=False
            ).values('user__username').annotate(
                activity_count=models.Count('id')
            ).order_by('-activity_count')[:10]
            
            return {
                'total_activities': total_activities,
                'activities_by_category': activities_by_category,
                'activities_by_action': activities_by_action,
                'top_users': list(top_users),
            }
            
        except Exception as e:
            logger.error(f"Error getting activity summary: {str(e)}")
            return {
                'total_activities': 0,
                'activities_by_category': {},
                'activities_by_action': {},
                'top_users': [],
            }


# Audit Trail Decorators
def audit_journal_entry_action(action):
    """Decorator to automatically audit journal entry actions"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            try:
                result = func(request, *args, **kwargs)
                
                # Log the action after successful execution
                if hasattr(request, 'journal_entry_for_audit'):
                    journal_entry = request.journal_entry_for_audit
                    
                    if action == 'create':
                        AuditManager.log_journal_entry_creation(request.user, journal_entry, request)
                    elif action == 'post':
                        AuditManager.log_journal_entry_posting(request.user, journal_entry, request)
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditManager.log_security_event(
                    request.user,
                    'action_failed',
                    f"فشل في تنفيذ {action} للقيد المحاسبي: {str(e)}",
                    request,
                    'error'
                )
                raise
        
        return wrapper
    return decorator