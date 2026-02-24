from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.apps import apps as django_apps
from django.db import connection
import os
import threading
import datetime
from decimal import Decimal

from .models import AuditLog
from .middleware import get_current_user, get_current_request


def _get_cache():
    if not hasattr(_local, 'pre_save_snapshots'):
        _local.pre_save_snapshots = {}
    return _local.pre_save_snapshots


def _jsonable(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float, str, bool)):
            return val
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
            return val.isoformat()
        return str(val)
    except Exception:
        return None


from django.conf import settings

# Thread-local cache for pre-save snapshots
_local = threading.local()


# Base sensitive keys; dynamic additions loaded lazily to avoid DB access at import
BASE_SENSITIVE_KEYS = {"password", "pwd", "secret", "token", "api_key", "apikey", "access_token", "refresh_token", "private_key", "key"}


def _audit_disabled() -> bool:
    """Disable auditing in test runs or when explicitly requested."""
    try:
        if getattr(settings, 'TESTING', False):
            return True
    except Exception:
        pass
    if os.getenv('SKIP_AUDIT') == '1':
        return True
    return False


def _auditing_available() -> bool:
    """Return True if the DB and required tables exist and the app registry is ready."""
    if _audit_disabled():
        return False
    try:
        if not django_apps.ready:
            return False
        tables = set(connection.introspection.table_names())
        # Content types and our audit table must exist before we log anything
        return 'django_content_type' in tables and 'core_auditlog' in tables
    except Exception:
        return False


def _get_sensitive_keys():
    keys = set(BASE_SENSITIVE_KEYS)
    extra = getattr(settings, 'AUDITLOG_SENSITIVE_FIELDS', None)
    if extra:
        try:
            keys.update({str(s).lower() for s in extra})
        except Exception:
            pass
    # Pull from AppSettings only when auditing is actually available
    # Skip during migrations or when AppSettings table doesn't exist
    if _auditing_available():
        try:
            tables = set(connection.introspection.table_names())
            if 'core_appsettings' not in tables:
                return keys
            from .models import AppSettings as _AS
            # Check if we have any AppSettings record
            if _AS.objects.exists():
                _cfg = _AS.objects.first()
                if _cfg and _cfg.audit_sensitive_fields:
                    keys.update({str(s).lower() for s in _cfg.audit_sensitive_fields})
        except Exception:
            pass
    return keys


# Configurable app/model ignore lists (settings-based at import; AppSettings checked lazily in _is_ignored)
DEFAULT_IGNORE_APPS = {"sessions", "admin", "contenttypes", "auth", "migrations"}
IGNORE_APPS = set(DEFAULT_IGNORE_APPS)
IGNORE_APPS = set(getattr(settings, 'AUDITLOG_IGNORE_APPS', IGNORE_APPS))
IGNORE_MODELS = set(m.lower() for m in getattr(settings, 'AUDITLOG_IGNORE_MODELS', []))


def _is_ignored(sender):
    """Decide if a model should be ignored from auditing without hitting the DB."""
    try:
        app_label = getattr(getattr(sender, '_meta', None), 'app_label', None)
        if not app_label:
            return True
        if app_label in IGNORE_APPS:
            return True
        full = f"{app_label}.{sender.__name__}".lower()
        if full in IGNORE_MODELS:
            return True
        # Prevent recursion: don't check settings if we're saving AppSettings itself
        if sender.__name__ == 'AppSettings':
            return True
        # Dynamic ignores from AppSettings (safe only when auditing available)
        if _auditing_available():
            try:
                tables = set(connection.introspection.table_names())
                if 'core_appsettings' not in tables:
                    return False
                from .models import AppSettings as _AS
                if _AS.objects.exists():
                    _cfg = _AS.objects.first()
                    if _cfg:
                        if _cfg.audit_ignore_apps and app_label in set(_cfg.audit_ignore_apps):
                            return True
                        if _cfg.audit_ignore_models and full in set(m.lower() for m in _cfg.audit_ignore_models):
                            return True
            except Exception:
                pass
        return False
    except Exception:
        return True


def _snapshot_fields(instance, mask_sensitive=False):
    data = {}
    sensitive = _get_sensitive_keys() if mask_sensitive else set()
    for field in instance._meta.fields:
        attname = getattr(field, 'attname', field.name)
        try:
            val = _jsonable(getattr(instance, attname))
            # Mask sensitive fields
            if field.name.lower() in sensitive:
                data[field.name] = "***"
            else:
                data[field.name] = val
        except Exception:
            continue
    return data


def _mask_changes(changes: dict):
    """Mask sensitive keys in a {field: {old,new}} mapping."""
    try:
        sensitive = _get_sensitive_keys()
        for k, v in list(changes.items()):
            if k.lower() in sensitive and isinstance(v, dict):
                if 'old' in v:
                    v['old'] = '***'
                if 'new' in v:
                    v['new'] = '***'
    except Exception:
        pass
    return changes


def diff_instance(instance, created):
    try:
        if created:
            new_data = _snapshot_fields(instance, mask_sensitive=True)
            return {k: {'new': v} for k, v in new_data.items() if isinstance(v, (int, float, str, bool)) or v is None}
        cache = _get_cache()
        key = f"{instance._meta.label}:{getattr(instance, 'pk', None)}"
        old_data = cache.pop(key, {})
        new_data = _snapshot_fields(instance, mask_sensitive=False)
        changes = {}
        for k, old_val in old_data.items():
            new_val = new_data.get(k)
            if old_val != new_val:
                changes[k] = {'old': old_val, 'new': new_val}
        if not old_data and not changes:
            changes['updated'] = True
        return _mask_changes(changes)
    except Exception:
        return {'updated': True}


def _maybe_alert(audit: AuditLog):
    if not _auditing_available():
        return
    # Load rules from AppSettings if present, else from settings
    rules = []
    try:
        from .models import AppSettings as _AS
        _cfg = _AS.get()
        if _cfg.audit_alert_rules:
            rules = list(_cfg.audit_alert_rules)
    except Exception:
        rules = []
    if not rules:
        rules = getattr(settings, 'AUDIT_ALERT_RULES', []) or []
    if not rules:
        return
    try:
        app = (audit.app_label or '').lower()
        model = (audit.model_name or '').lower()
        action = audit.action
        fields_changed = set((audit.changes or {}).keys())
        for rule in rules:
            # Basic filters
            r_action = rule.get('action')
            if r_action and r_action != action:
                continue
            r_app = (rule.get('app_label') or '').lower()
            if r_app and r_app != app:
                continue
            r_model = (rule.get('model_name') or '').lower()
            if r_model and r_model != model:
                continue
            # Fields conditions
            any_fields = set((rule.get('fields_any') or [])).intersection(fields_changed)
            all_fields = set(rule.get('fields_all') or [])
            if rule.get('fields_any') and not any_fields:
                continue
            if all_fields and not all_fields.issubset(fields_changed):
                continue
            # Contains check on new values
            contains = rule.get('contains') or {}
            matched = True
            for k, v in contains.items():
                ch = (audit.changes or {}).get(k)
                newv = ch.get('new') if isinstance(ch, dict) else None
                if str(newv) != str(v):
                    matched = False
                    break
            if not matched:
                continue
            # User filter
            users = set(rule.get('user_in') or [])
            if users and (not audit.user or audit.user.username not in users):
                continue
            # If reached here, rule matches -> queue alert task
            try:
                from .tasks import send_audit_alert
                send_audit_alert.delay(audit.id, rule.get('name'))
            except Exception:
                pass
    except Exception:
        return


def create_audit(instance, action, created=False, changes=None):
    if _audit_disabled() or not _auditing_available():
        return
    user = get_current_user()
    request = get_current_request()
    meta = AuditLog.build_object_meta(instance)
    ip = None
    ua = ''
    if request:
        ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')[:255]
    audit = AuditLog.objects.create(
        user=user,
        action=action,
        content_type_id=meta['content_type_id'],
        object_id=meta['object_id'],
        model_name=meta['model_name'],
        app_label=meta['app_label'],
        object_repr=meta['object_repr'],
        changes=changes if changes is not None else diff_instance(instance, created),
        ip_address=ip,
        user_agent=ua,
    )
    _maybe_alert(audit)


@receiver(pre_save, dispatch_uid="core_audit_pre_save")
def audit_pre_save(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    if sender is AuditLog or _audit_disabled() or _is_ignored(sender) or not _auditing_available():
        return
    if getattr(instance, 'pk', None):
        try:
            current = sender.objects.filter(pk=instance.pk).first()
            if current is not None:
                cache = _get_cache()
                key = f"{instance._meta.label}:{instance.pk}"
                cache[key] = _snapshot_fields(current, mask_sensitive=False)
        except Exception:
            pass


@receiver(post_save, dispatch_uid="core_audit_post_save")
def audit_post_save(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    if sender is AuditLog or _audit_disabled() or _is_ignored(sender) or not _auditing_available():
        return
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    changes = diff_instance(instance, created)
    create_audit(instance, action, created, changes=changes)


@receiver(post_delete, dispatch_uid="core_audit_post_delete")
def audit_post_delete(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    if sender is AuditLog or _audit_disabled() or _is_ignored(sender) or not _auditing_available():
        return
    create_audit(instance, AuditLog.ACTION_DELETE)


@receiver(user_logged_in, dispatch_uid="core_audit_user_login")
def audit_user_login(sender, request, user, **kwargs):
    if _audit_disabled() or not _auditing_available():
        return
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_LOGIN,
        model_name='User',
        app_label='auth',
        object_id=str(getattr(user, 'pk', '')),
        object_repr=str(user)[:255],
        changes={},
        ip_address=ip,
        user_agent=ua,
    )


@receiver(user_logged_out, dispatch_uid="core_audit_user_logout")
def audit_user_logout(sender, request, user, **kwargs):
    if _audit_disabled() or not _auditing_available():
        return
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_LOGOUT,
        model_name='User',
        app_label='auth',
        object_id=str(getattr(user, 'pk', '')),
        object_repr=str(user)[:255],
        changes={},
        ip_address=ip,
        user_agent=ua,
    )


# ==================== Dashboard Cache Invalidation ====================
@receiver([post_save, post_delete])
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """حذف cache الداشبورد عند حدوث تحديثات في البيانات الرئيسية"""
    from django.core.cache import cache
    
    # القوائم المؤثرة على الداشبورد
    dashboard_models = [
        'Invoice', 'InvoiceItem', 'PurchaseBill', 'PurchaseItem',
        'Revenue', 'Expense', 'Product', 'Stock',
        'Customer', 'Supplier', 'Account'
    ]
    
    model_name = sender.__name__
    if model_name in dashboard_models:
        # حذف جميع cache keys للداشبورد
        # Check if cache supports delete_pattern (redis) or fall back to regular delete
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('dashboard:v2:*')
        else:
            # Fallback for DummyCache or other cache backends without delete_pattern
            try:
                cache.delete('dashboard:v2:overview')
            except Exception:
                pass

