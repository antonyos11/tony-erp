"""
Accounting Performance Monitoring Middleware
Advanced middleware for tracking performance, errors, and user activity
"""

import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AccountingPerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to monitor performance of accounting operations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.accounting_urls = [
            'accounting:journal_entry_create',
            'accounting:journal_entries_list',
            'accounting:account_search_api',
            'accounting:journal_entry_validate_api',
            'accounting:journal_entry_draft_save_api',
        ]
    
    def process_request(self, request):
        """Start timing the request"""
        request._start_time = time.time()
        request._request_id = str(uuid.uuid4())[:8]
        
        # Add request ID to session for tracking
        if hasattr(request, 'session'):
            request.session['current_request_id'] = request._request_id
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view information"""
        try:
            resolved = resolve(request.path_info)
            request._view_name = resolved.view_name
            request._is_accounting = any(url in resolved.view_name for url in self.accounting_urls)
            
            # Log accounting operations
            if request._is_accounting:
                self._log_accounting_operation(request, 'start')
                
        except Exception as e:
            logger.error(f"Error in process_view: {str(e)}")
    
    def process_response(self, request, response):
        """Process response and log performance"""
        if not hasattr(request, '_start_time'):
            return response
        
        duration = time.time() - request._start_time
        
        # Log performance data
        if hasattr(request, '_is_accounting') and request._is_accounting:
            self._log_performance_data(request, response, duration)
        
        # Add performance headers for debugging
        if settings.DEBUG:
            response['X-Request-Duration'] = f"{duration:.3f}s"
            response['X-Request-ID'] = getattr(request, '_request_id', 'unknown')
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions in accounting operations"""
        if hasattr(request, '_is_accounting') and request._is_accounting:
            self._log_accounting_error(request, exception)
        
        return None
    
    def _log_accounting_operation(self, request, operation_type):
        """Log accounting operation details"""
        try:
            log_data = {
                'request_id': getattr(request, '_request_id', 'unknown'),
                'operation': operation_type,
                'view_name': getattr(request, '_view_name', 'unknown'),
                'method': request.method,
                'path': request.path_info,
                'user': str(request.user) if request.user.is_authenticated else 'anonymous',
                'user_id': request.user.id if request.user.is_authenticated else None,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                'timestamp': datetime.now().isoformat(),
            }
            
            # Add POST data for certain operations (excluding sensitive data)
            if request.method == 'POST' and operation_type == 'start':
                log_data['has_post_data'] = True
                log_data['content_length'] = request.META.get('CONTENT_LENGTH', 0)
            
            logger.info(f"Accounting Operation: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Error logging accounting operation: {str(e)}")
    
    def _log_performance_data(self, request, response, duration):
        """Log detailed performance data"""
        try:
            perf_data = {
                'request_id': getattr(request, '_request_id', 'unknown'),
                'view_name': getattr(request, '_view_name', 'unknown'),
                'method': request.method,
                'duration_seconds': round(duration, 3),
                'status_code': response.status_code,
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'timestamp': datetime.now().isoformat(),
            }
            
            # Categorize performance
            if duration > 5.0:
                perf_data['performance_category'] = 'very_slow'
                logger.warning(f"Very slow accounting operation: {json.dumps(perf_data)}")
            elif duration > 2.0:
                perf_data['performance_category'] = 'slow'
                logger.warning(f"Slow accounting operation: {json.dumps(perf_data)}")
            elif duration > 1.0:
                perf_data['performance_category'] = 'moderate'
                logger.info(f"Moderate accounting operation: {json.dumps(perf_data)}")
            else:
                perf_data['performance_category'] = 'fast'
                logger.debug(f"Fast accounting operation: {json.dumps(perf_data)}")
            
            # Store performance metrics in cache for dashboard
            self._store_performance_metrics(perf_data)
            
        except Exception as e:
            logger.error(f"Error logging performance data: {str(e)}")
    
    def _log_accounting_error(self, request, exception):
        """Log errors in accounting operations"""
        try:
            error_data = {
                'request_id': getattr(request, '_request_id', 'unknown'),
                'view_name': getattr(request, '_view_name', 'unknown'),
                'method': request.method,
                'path': request.path_info,
                'error_type': type(exception).__name__,
                'error_message': str(exception),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'timestamp': datetime.now().isoformat(),
            }
            
            logger.error(f"Accounting Operation Error: {json.dumps(error_data)}")
            
            # Store error for admin dashboard
            self._store_error_data(error_data)
            
        except Exception as e:
            logger.error(f"Error logging accounting error: {str(e)}")
    
    def _store_performance_metrics(self, perf_data):
        """Store performance metrics in cache for dashboard"""
        try:
            cache_key = f"accounting_perf_{datetime.now().strftime('%Y%m%d_%H')}"
            metrics = cache.get(cache_key, [])
            metrics.append(perf_data)
            
            # Keep only last 100 entries per hour
            if len(metrics) > 100:
                metrics = metrics[-100:]
            
            cache.set(cache_key, metrics, 3600)  # Store for 1 hour
            
        except Exception as e:
            logger.error(f"Error storing performance metrics: {str(e)}")
    
    def _store_error_data(self, error_data):
        """Store error data for admin review"""
        try:
            cache_key = f"accounting_errors_{datetime.now().strftime('%Y%m%d')}"
            errors = cache.get(cache_key, [])
            errors.append(error_data)
            
            # Keep only last 50 errors per day
            if len(errors) > 50:
                errors = errors[-50:]
            
            cache.set(cache_key, errors, 86400)  # Store for 24 hours
            
        except Exception as e:
            logger.error(f"Error storing error data: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AccountingAuditMiddleware(MiddlewareMixin):
    """
    Middleware for audit trail of accounting operations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sensitive_operations = [
            'accounting:journal_entry_create',
            'accounting:post_journal_entry',
            'accounting:reverse_journal_entry',
            'accounting:account_create',
            'accounting:account_edit',
        ]
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Audit sensitive operations"""
        try:
            resolved = resolve(request.path_info)
            
            if resolved.view_name in self.sensitive_operations:
                self._create_audit_log(request, resolved.view_name, 'attempted')
                
        except Exception as e:
            logger.error(f"Error in audit middleware: {str(e)}")
    
    def process_response(self, request, response):
        """Log successful operations"""
        try:
            if hasattr(request, '_audit_required'):
                resolved = resolve(request.path_info)
                if response.status_code < 400:
                    self._create_audit_log(request, resolved.view_name, 'completed')
                else:
                    self._create_audit_log(request, resolved.view_name, 'failed')
                    
        except Exception as e:
            logger.error(f"Error in audit response processing: {str(e)}")
        
        return response
    
    def _create_audit_log(self, request, operation, status):
        """Create audit log entry"""
        try:
            audit_data = {
                'operation': operation,
                'status': status,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'username': str(request.user) if request.user.is_authenticated else 'anonymous',
                'ip_address': self._get_client_ip(request),
                'timestamp': datetime.now().isoformat(),
                'path': request.path_info,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            }
            
            # Store in cache and log
            cache_key = f"audit_log_{datetime.now().strftime('%Y%m%d')}"
            audit_logs = cache.get(cache_key, [])
            audit_logs.append(audit_data)
            
            # Keep only last 200 entries per day
            if len(audit_logs) > 200:
                audit_logs = audit_logs[-200:]
            
            cache.set(cache_key, audit_logs, 86400)
            
            logger.info(f"Audit Log: {json.dumps(audit_data)}")
            
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AccountingSecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for accounting operations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_cache = {}
    
    def process_request(self, request):
        """Check security before processing request"""
        # Rate limiting for API endpoints
        if '/api/' in request.path_info:
            if not self._check_rate_limit(request):
                return JsonResponse({
                    'error': 'معدل الطلبات مرتفع جداً. حاول مرة أخرى لاحقاً.'
                }, status=429)
        
        # Check for suspicious patterns
        if self._detect_suspicious_activity(request):
            logger.warning(f"Suspicious activity detected: {request.path_info} from {self._get_client_ip(request)}")
    
    def _check_rate_limit(self, request):
        """Check API rate limits"""
        try:
            client_ip = self._get_client_ip(request)
            current_time = time.time()
            
            # Clean old entries
            cutoff_time = current_time - 60  # 1 minute window
            self.rate_limit_cache = {
                ip: times for ip, times in self.rate_limit_cache.items()
                if times and max(times) > cutoff_time
            }
            
            # Check current IP
            if client_ip not in self.rate_limit_cache:
                self.rate_limit_cache[client_ip] = []
            
            # Count requests in last minute
            recent_requests = [
                t for t in self.rate_limit_cache[client_ip]
                if t > cutoff_time
            ]
            
            # Limit: 60 requests per minute for API
            if len(recent_requests) >= 60:
                return False
            
            # Add current request
            self.rate_limit_cache[client_ip].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {str(e)}")
            return True  # Allow request if error in rate limiting
    
    def _detect_suspicious_activity(self, request):
        """Detect potentially suspicious activity"""
        try:
            # Check for SQL injection patterns
            suspicious_patterns = [
                'union select', 'drop table', 'delete from',
                'insert into', 'update set', '--', ';--',
                '<script', 'javascript:', 'eval('
            ]
            
            query_string = request.META.get('QUERY_STRING', '').lower()
            
            for pattern in suspicious_patterns:
                if pattern in query_string:
                    return True
            
            # Check POST data if exists
            if request.method == 'POST':
                try:
                    body = request.body.decode('utf-8').lower()
                    for pattern in suspicious_patterns:
                        if pattern in body:
                            return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error in suspicious activity detection: {str(e)}")
            return False
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


def get_performance_dashboard_data():
    """Get performance data for admin dashboard"""
    try:
        current_hour = datetime.now().strftime('%Y%m%d_%H')
        cache_key = f"accounting_perf_{current_hour}"
        
        performance_data = cache.get(cache_key, [])
        
        if not performance_data:
            return {
                'total_requests': 0,
                'average_duration': 0,
                'slow_requests': 0,
                'error_rate': 0
            }
        
        total_requests = len(performance_data)
        durations = [p['duration_seconds'] for p in performance_data]
        slow_requests = len([d for d in durations if d > 2.0])
        
        return {
            'total_requests': total_requests,
            'average_duration': round(sum(durations) / len(durations), 3) if durations else 0,
            'slow_requests': slow_requests,
            'slow_percentage': round((slow_requests / total_requests) * 100, 1) if total_requests > 0 else 0,
            'fastest_request': min(durations) if durations else 0,
            'slowest_request': max(durations) if durations else 0,
        }
        
    except Exception as e:
        logger.error(f"Error getting performance dashboard data: {str(e)}")
        return {
            'total_requests': 0,
            'average_duration': 0,
            'slow_requests': 0,
            'error_rate': 0
        }


def get_error_dashboard_data():
    """Get error data for admin dashboard"""
    try:
        today = datetime.now().strftime('%Y%m%d')
        cache_key = f"accounting_errors_{today}"
        
        error_data = cache.get(cache_key, [])
        
        if not error_data:
            return {
                'total_errors': 0,
                'error_types': {},
                'recent_errors': []
            }
        
        error_types = {}
        for error in error_data:
            error_type = error.get('error_type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': len(error_data),
            'error_types': error_types,
            'recent_errors': error_data[-10:],  # Last 10 errors
        }
        
    except Exception as e:
        logger.error(f"Error getting error dashboard data: {str(e)}")
        return {
            'total_errors': 0,
            'error_types': {},
            'recent_errors': []
        }