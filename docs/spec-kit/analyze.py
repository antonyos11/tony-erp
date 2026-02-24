#!/usr/bin/env python3
"""
Tony ERP Spec-Kit Analyzer
===========================
أداة تحليل شاملة لنظام Tony ERP
تقوم بفحص وتحليل جميع مكونات النظام وإنشاء تقارير تفصيلية

Usage:
    python analyze.py                    # Full analysis
    python analyze.py --quick            # Quick summary
    python analyze.py --apps             # Apps analysis only
    python analyze.py --models           # Models analysis only
    python analyze.py --urls             # URLs analysis only
    python analyze.py --security         # Security analysis
    python analyze.py --performance      # Performance analysis
    python analyze.py --dependencies     # Dependencies analysis
    python analyze.py --report html      # Generate HTML report
    python analyze.py --report json      # Generate JSON report
    python analyze.py --report md        # Generate Markdown report
"""

import os
import sys
import json
import argparse
import importlib
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple

# Add project to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
import django
django.setup()

from django.conf import settings
from django.apps import apps
from django.urls import get_resolver, URLPattern, URLResolver
from django.db import connection
from django.contrib.auth import get_user_model


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SpecKitAnalyzer:
    """Main analyzer class for Tony ERP system"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system': 'Tony ERP',
            'version': '1.0.0',
            'analysis': {}
        }
        self.warnings = []
        self.errors = []
        self.recommendations = []
        
    def log(self, message: str, level: str = 'info'):
        """Log message with color"""
        if not self.verbose:
            return
            
        colors = {
            'info': Colors.CYAN,
            'success': Colors.GREEN,
            'warning': Colors.WARNING,
            'error': Colors.FAIL,
            'header': Colors.HEADER + Colors.BOLD
        }
        color = colors.get(level, '')
        print(f"{color}{message}{Colors.END}")
        
    def section(self, title: str):
        """Print section header"""
        self.log(f"\n{'='*60}", 'header')
        self.log(f"  {title}", 'header')
        self.log(f"{'='*60}", 'header')

    # =========================================================================
    # APPS ANALYSIS
    # =========================================================================
    
    def analyze_apps(self) -> Dict[str, Any]:
        """Analyze all Django apps"""
        self.section("📦 APPS ANALYSIS")
        
        all_apps = list(apps.get_app_configs())
        custom_apps = [a for a in all_apps if not a.name.startswith(('django.', 'rest_framework', 'corsheaders', 'debug_toolbar', 'celery', 'allauth', 'drf_', 'crispy', 'widget_tweaks', 'simple_history', 'import_export', 'channels', 'storages', 'whitenoise', 'axes', 'defender'))]
        third_party = [a for a in all_apps if a not in custom_apps]
        
        # Categorize apps
        categories = {
            'core': [],
            'finance': [],
            'hr': [],
            'inventory': [],
            'sales': [],
            'crm': [],
            'integrations': [],
            'utilities': [],
            'other': []
        }
        
        finance_keywords = ['account', 'invoice', 'payment', 'budget', 'bank', 'tax', 'financial', 'pos', 'installment']
        hr_keywords = ['hr', 'employee', 'attendance', 'payroll', 'leave', 'recruit']
        inventory_keywords = ['inventory', 'stock', 'warehouse', 'product']
        sales_keywords = ['sales', 'order', 'customer', 'quote', 'pricing']
        crm_keywords = ['crm', 'lead', 'opportunity', 'campaign', 'loyalty']
        integration_keywords = ['api', 'integration', 'ecommerce', 'sms', 'email', 'notification']
        utility_keywords = ['report', 'backup', 'import', 'export', 'config', 'setting', 'monitor']
        core_keywords = ['core', 'auth', 'account', 'user', 'permission', 'home']
        
        for app in custom_apps:
            name = app.name.lower()
            if any(k in name for k in finance_keywords):
                categories['finance'].append(app.name)
            elif any(k in name for k in hr_keywords):
                categories['hr'].append(app.name)
            elif any(k in name for k in inventory_keywords):
                categories['inventory'].append(app.name)
            elif any(k in name for k in sales_keywords):
                categories['sales'].append(app.name)
            elif any(k in name for k in crm_keywords):
                categories['crm'].append(app.name)
            elif any(k in name for k in integration_keywords):
                categories['integrations'].append(app.name)
            elif any(k in name for k in utility_keywords):
                categories['utilities'].append(app.name)
            elif any(k in name for k in core_keywords):
                categories['core'].append(app.name)
            else:
                categories['other'].append(app.name)
        
        # App details
        app_details = []
        for app in custom_apps:
            models = list(app.get_models())
            app_path = Path(app.path) if hasattr(app, 'path') else None
            
            detail = {
                'name': app.name,
                'label': app.label,
                'models_count': len(models),
                'models': [m.__name__ for m in models],
                'has_admin': (app_path / 'admin.py').exists() if app_path else False,
                'has_views': (app_path / 'views.py').exists() if app_path else False,
                'has_urls': (app_path / 'urls.py').exists() if app_path else False,
                'has_api': (app_path / 'api.py').exists() or (app_path / 'serializers.py').exists() if app_path else False,
                'has_tests': (app_path / 'tests.py').exists() or (app_path / 'tests').exists() if app_path else False,
                'has_signals': (app_path / 'signals.py').exists() if app_path else False,
                'has_tasks': (app_path / 'tasks.py').exists() if app_path else False,
            }
            app_details.append(detail)
        
        # Statistics
        stats = {
            'total_apps': len(all_apps),
            'custom_apps': len(custom_apps),
            'third_party_apps': len(third_party),
            'apps_with_models': len([a for a in app_details if a['models_count'] > 0]),
            'apps_with_admin': len([a for a in app_details if a['has_admin']]),
            'apps_with_api': len([a for a in app_details if a['has_api']]),
            'apps_with_tests': len([a for a in app_details if a['has_tests']]),
            'apps_with_signals': len([a for a in app_details if a['has_signals']]),
            'apps_with_tasks': len([a for a in app_details if a['has_tasks']]),
        }
        
        result = {
            'statistics': stats,
            'categories': categories,
            'custom_apps': [a.name for a in custom_apps],
            'third_party_apps': [a.name for a in third_party],
            'details': app_details
        }
        
        self.log(f"✓ Total Apps: {stats['total_apps']}", 'success')
        self.log(f"  • Custom Apps: {stats['custom_apps']}")
        self.log(f"  • Third-party Apps: {stats['third_party_apps']}")
        self.log(f"  • Apps with Models: {stats['apps_with_models']}")
        self.log(f"  • Apps with Admin: {stats['apps_with_admin']}")
        self.log(f"  • Apps with API: {stats['apps_with_api']}")
        self.log(f"  • Apps with Tests: {stats['apps_with_tests']}")
        
        # Categories breakdown
        self.log("\n📊 Apps by Category:")
        for cat, app_list in categories.items():
            if app_list:
                self.log(f"  • {cat.title()}: {len(app_list)} apps")
        
        # Recommendations
        if stats['apps_with_tests'] < stats['custom_apps'] * 0.5:
            self.recommendations.append({
                'category': 'testing',
                'severity': 'medium',
                'message': f"Only {stats['apps_with_tests']}/{stats['custom_apps']} apps have tests. Consider adding tests."
            })
            
        self.results['analysis']['apps'] = result
        return result

    # =========================================================================
    # MODELS ANALYSIS
    # =========================================================================
    
    def analyze_models(self) -> Dict[str, Any]:
        """Analyze all Django models"""
        self.section("📊 MODELS ANALYSIS")
        
        all_models = apps.get_models()
        
        model_details = []
        field_types = Counter()
        relationship_count = 0
        total_fields = 0
        
        for model in all_models:
            fields = model._meta.get_fields()
            
            field_info = []
            relations = []
            
            for field in fields:
                field_type = type(field).__name__
                field_types[field_type] += 1
                total_fields += 1
                
                field_data: dict[str, str] = {
                    'name': field.name,
                    'type': field_type,
                }
                
                max_length = getattr(field, 'max_length', None)
                if max_length is not None:
                    field_data['max_length'] = str(max_length)
                null_val = getattr(field, 'null', None)
                if null_val is not None:
                    field_data['null'] = str(null_val)
                blank_val = getattr(field, 'blank', None)
                if blank_val is not None:
                    field_data['blank'] = str(blank_val)
                    
                field_info.append(field_data)
                
                # Track relationships
                if field_type in ('ForeignKey', 'OneToOneField', 'ManyToManyField', 'ManyToOneRel', 'ManyToManyRel'):
                    relationship_count += 1
                    if hasattr(field, 'related_model') and field.related_model:
                        relations.append({
                            'field': field.name,
                            'type': field_type,
                            'to': field.related_model.__name__ if field.related_model else 'Unknown'
                        })
            
            model_details.append({
                'app': model._meta.app_label,
                'name': model.__name__,
                'db_table': model._meta.db_table,
                'fields_count': len(fields),
                'fields': field_info,
                'relationships': relations,
                'has_str': hasattr(model, '__str__') and model.__str__ is not object.__str__,
                'is_abstract': model._meta.abstract,
                'ordering': list(model._meta.ordering) if model._meta.ordering else None,
            })
        
        # Group by app
        models_by_app = defaultdict(list)
        for model in model_details:
            models_by_app[model['app']].append(model['name'])
        
        # Find largest models
        largest_models = sorted(model_details, key=lambda x: x['fields_count'], reverse=True)[:10]
        
        # Find orphan models (no relationships)
        orphan_models = [m['name'] for m in model_details if not m['relationships']]
        
        stats = {
            'total_models': len(all_models),
            'total_fields': total_fields,
            'total_relationships': relationship_count,
            'avg_fields_per_model': round(total_fields / len(all_models), 2) if all_models else 0,
            'field_types': dict(field_types.most_common(20)),
            'models_by_app_count': {k: len(v) for k, v in models_by_app.items()},
            'orphan_models_count': len(orphan_models),
        }
        
        result = {
            'statistics': stats,
            'models_by_app': dict(models_by_app),
            'largest_models': [{'name': m['name'], 'app': m['app'], 'fields': m['fields_count']} for m in largest_models],
            'orphan_models': orphan_models[:20],  # First 20
            'details': model_details
        }
        
        self.log(f"✓ Total Models: {stats['total_models']}", 'success')
        self.log(f"  • Total Fields: {stats['total_fields']}")
        self.log(f"  • Total Relationships: {stats['total_relationships']}")
        self.log(f"  • Avg Fields/Model: {stats['avg_fields_per_model']}")
        
        self.log("\n📊 Top 10 Largest Models:")
        for m in largest_models:
            self.log(f"  • {m['app']}.{m['name']}: {m['fields_count']} fields")
        
        self.log("\n📊 Field Types Distribution:")
        for ft, count in list(field_types.most_common(10)):
            self.log(f"  • {ft}: {count}")
        
        self.results['analysis']['models'] = result
        return result

    # =========================================================================
    # URLS ANALYSIS
    # =========================================================================
    
    def analyze_urls(self) -> Dict[str, Any]:
        """Analyze all URL patterns"""
        self.section("🔗 URLS ANALYSIS")
        
        def extract_urls(urlpatterns, prefix=''):
            urls = []
            for pattern in urlpatterns:
                if isinstance(pattern, URLResolver):
                    nested_prefix = prefix + str(pattern.pattern)
                    urls.extend(extract_urls(pattern.url_patterns, nested_prefix))
                elif isinstance(pattern, URLPattern):
                    full_path = prefix + str(pattern.pattern)
                    urls.append({
                        'path': full_path,
                        'name': pattern.name or '',
                        'view': str(pattern.callback) if pattern.callback else '',
                    })
            return urls
        
        try:
            resolver = get_resolver()
            all_urls = extract_urls(resolver.url_patterns)
        except Exception as e:
            self.log(f"✗ Error analyzing URLs: {e}", 'error')
            return {'error': str(e)}
        
        # Categorize URLs
        api_urls = [u for u in all_urls if '/api/' in u['path']]
        admin_urls = [u for u in all_urls if u['path'].startswith('admin/')]
        auth_urls = [u for u in all_urls if any(x in u['path'] for x in ['login', 'logout', 'password', 'register'])]
        
        # Group by app/prefix
        url_prefixes = Counter()
        for url in all_urls:
            parts = url['path'].strip('/').split('/')
            if parts and parts[0]:
                url_prefixes[parts[0]] += 1
        
        # Named vs unnamed
        named_urls = [u for u in all_urls if u['name']]
        unnamed_urls = [u for u in all_urls if not u['name']]
        
        stats = {
            'total_urls': len(all_urls),
            'api_urls': len(api_urls),
            'admin_urls': len(admin_urls),
            'auth_urls': len(auth_urls),
            'named_urls': len(named_urls),
            'unnamed_urls': len(unnamed_urls),
            'url_prefixes': dict(url_prefixes.most_common(20)),
        }
        
        result = {
            'statistics': stats,
            'sample_api_urls': [u['path'] for u in api_urls[:20]],
            'url_prefixes': dict(url_prefixes),
        }
        
        self.log(f"✓ Total URLs: {stats['total_urls']}", 'success')
        self.log(f"  • API URLs: {stats['api_urls']}")
        self.log(f"  • Admin URLs: {stats['admin_urls']}")
        self.log(f"  • Named URLs: {stats['named_urls']}")
        self.log(f"  • Unnamed URLs: {stats['unnamed_urls']}")
        
        if stats['unnamed_urls'] > stats['total_urls'] * 0.3:
            self.recommendations.append({
                'category': 'urls',
                'severity': 'low',
                'message': f"{stats['unnamed_urls']} URLs are unnamed. Consider naming them for reverse URL lookup."
            })
        
        self.log("\n📊 Top URL Prefixes:")
        for prefix, count in url_prefixes.most_common(15):
            self.log(f"  • /{prefix}/: {count} URLs")
        
        self.results['analysis']['urls'] = result
        return result

    # =========================================================================
    # DATABASE ANALYSIS
    # =========================================================================
    
    def analyze_database(self) -> Dict[str, Any]:
        """Analyze database structure"""
        self.section("🗄️ DATABASE ANALYSIS")
        
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Table sizes (PostgreSQL)
            table_sizes = {}
            try:
                cursor.execute("""
                    SELECT 
                        relname as table_name,
                        n_live_tup as row_count,
                        pg_size_pretty(pg_total_relation_size(relid)) as total_size
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                    LIMIT 20
                """)
                for row in cursor.fetchall():
                    table_sizes[row[0]] = {'rows': row[1], 'size': row[2]}
            except:
                pass
            
            # Index count
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'
                """)
                result = cursor.fetchone()
                index_count = result[0] if result else 0
            except:
                index_count = 0
        
        # Migration status
        try:
            from django.db.migrations.recorder import MigrationRecorder
            from django.db.backends.base.base import BaseDatabaseWrapper
            from typing import cast
            recorder = MigrationRecorder(cast(BaseDatabaseWrapper, connection))
            applied_migrations = list(recorder.applied_migrations())
            migration_count = len(applied_migrations)
        except:
            migration_count = 0
        
        stats = {
            'total_tables': len(tables),
            'index_count': index_count,
            'migration_count': migration_count,
            'database_engine': connection.vendor,
        }
        
        result = {
            'statistics': stats,
            'tables': tables,
            'table_sizes': table_sizes,
        }
        
        self.log(f"✓ Database: {connection.vendor.upper()}", 'success')
        self.log(f"  • Total Tables: {stats['total_tables']}")
        self.log(f"  • Total Indexes: {stats['index_count']}")
        self.log(f"  • Applied Migrations: {stats['migration_count']}")
        
        if table_sizes:
            self.log("\n📊 Largest Tables (by rows):")
            for table, info in list(table_sizes.items())[:10]:
                self.log(f"  • {table}: {info['rows']:,} rows ({info['size']})")
        
        self.results['analysis']['database'] = result
        return result

    # =========================================================================
    # SECURITY ANALYSIS
    # =========================================================================
    
    def analyze_security(self) -> Dict[str, Any]:
        """Analyze security configuration"""
        self.section("🔐 SECURITY ANALYSIS")
        
        security_checks = []
        
        # DEBUG mode
        debug = getattr(settings, 'DEBUG', True)
        security_checks.append({
            'check': 'DEBUG Mode',
            'status': 'PASS' if not debug else 'FAIL',
            'value': debug,
            'recommendation': 'DEBUG should be False in production' if debug else None
        })
        
        # SECRET_KEY
        secret_key = getattr(settings, 'SECRET_KEY', '')
        has_real_key = len(secret_key) > 30 and 'your-secret' not in secret_key.lower()
        security_checks.append({
            'check': 'SECRET_KEY',
            'status': 'PASS' if has_real_key else 'FAIL',
            'recommendation': 'Set a strong, unique SECRET_KEY' if not has_real_key else None
        })
        
        # ALLOWED_HOSTS
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        security_checks.append({
            'check': 'ALLOWED_HOSTS',
            'status': 'PASS' if allowed_hosts and '*' not in allowed_hosts else 'WARNING',
            'value': allowed_hosts[:5] if allowed_hosts else [],
            'recommendation': 'Configure ALLOWED_HOSTS properly' if not allowed_hosts or '*' in allowed_hosts else None
        })
        
        # CSRF
        csrf_middleware = 'django.middleware.csrf.CsrfViewMiddleware' in getattr(settings, 'MIDDLEWARE', [])
        security_checks.append({
            'check': 'CSRF Protection',
            'status': 'PASS' if csrf_middleware else 'FAIL',
            'recommendation': 'Enable CSRF middleware' if not csrf_middleware else None
        })
        
        # XSS Protection
        security_checks.append({
            'check': 'XSS Protection',
            'status': 'PASS' if getattr(settings, 'SECURE_BROWSER_XSS_FILTER', False) else 'WARNING',
        })
        
        # HTTPS
        security_checks.append({
            'check': 'SECURE_SSL_REDIRECT',
            'status': 'PASS' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'WARNING',
        })
        
        # Session security
        security_checks.append({
            'check': 'SESSION_COOKIE_SECURE',
            'status': 'PASS' if getattr(settings, 'SESSION_COOKIE_SECURE', False) else 'WARNING',
        })
        
        security_checks.append({
            'check': 'CSRF_COOKIE_SECURE',
            'status': 'PASS' if getattr(settings, 'CSRF_COOKIE_SECURE', False) else 'WARNING',
        })
        
        # HSTS
        security_checks.append({
            'check': 'HSTS',
            'status': 'PASS' if getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0 else 'WARNING',
        })
        
        # Content Type Sniffing
        security_checks.append({
            'check': 'X_CONTENT_TYPE_OPTIONS',
            'status': 'PASS' if getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False) else 'WARNING',
        })
        
        # Password validators
        password_validators = getattr(settings, 'AUTH_PASSWORD_VALIDATORS', [])
        security_checks.append({
            'check': 'Password Validators',
            'status': 'PASS' if len(password_validators) >= 3 else 'WARNING',
            'value': len(password_validators),
        })
        
        # Authentication backends
        auth_backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        security_checks.append({
            'check': 'Auth Backends',
            'status': 'PASS',
            'value': len(auth_backends),
        })
        
        # Calculate scores
        passed = len([c for c in security_checks if c['status'] == 'PASS'])
        warnings = len([c for c in security_checks if c['status'] == 'WARNING'])
        failed = len([c for c in security_checks if c['status'] == 'FAIL'])
        total = len(security_checks)
        score = round((passed / total) * 100) if total > 0 else 0
        
        stats = {
            'total_checks': total,
            'passed': passed,
            'warnings': warnings,
            'failed': failed,
            'score': score,
        }
        
        result = {
            'statistics': stats,
            'checks': security_checks,
        }
        
        self.log(f"✓ Security Score: {score}%", 'success' if score >= 80 else 'warning')
        self.log(f"  • Passed: {passed}")
        self.log(f"  • Warnings: {warnings}")
        self.log(f"  • Failed: {failed}")
        
        self.log("\n📊 Security Checks:")
        for check in security_checks:
            icon = '✓' if check['status'] == 'PASS' else ('⚠' if check['status'] == 'WARNING' else '✗')
            color = 'success' if check['status'] == 'PASS' else ('warning' if check['status'] == 'WARNING' else 'error')
            self.log(f"  {icon} {check['check']}: {check['status']}", color)
        
        if failed > 0:
            self.errors.extend([c for c in security_checks if c['status'] == 'FAIL'])
        if warnings > 0:
            self.warnings.extend([c for c in security_checks if c['status'] == 'WARNING'])
        
        self.results['analysis']['security'] = result
        return result

    # =========================================================================
    # PERFORMANCE ANALYSIS
    # =========================================================================
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance configuration"""
        self.section("⚡ PERFORMANCE ANALYSIS")
        
        perf_checks = []
        
        # Caching
        caches = getattr(settings, 'CACHES', {})
        cache_backend = caches.get('default', {}).get('BACKEND', '')
        is_redis = 'redis' in cache_backend.lower()
        is_memcached = 'memcached' in cache_backend.lower()
        perf_checks.append({
            'check': 'Cache Backend',
            'status': 'PASS' if (is_redis or is_memcached) else 'WARNING',
            'value': 'Redis' if is_redis else ('Memcached' if is_memcached else 'Local Memory'),
        })
        
        # Database connection pooling
        db_config = getattr(settings, 'DATABASES', {}).get('default', {})
        conn_max_age = db_config.get('CONN_MAX_AGE', 0)
        perf_checks.append({
            'check': 'DB Connection Pooling',
            'status': 'PASS' if conn_max_age > 0 else 'WARNING',
            'value': f"{conn_max_age}s" if conn_max_age else 'Disabled',
        })
        
        # Static files
        staticfiles_storage = getattr(settings, 'STATICFILES_STORAGE', '')
        uses_whitenoise = 'whitenoise' in staticfiles_storage.lower()
        perf_checks.append({
            'check': 'Static Files Compression',
            'status': 'PASS' if uses_whitenoise else 'WARNING',
            'value': 'WhiteNoise' if uses_whitenoise else 'Default',
        })
        
        # Celery
        has_celery = hasattr(settings, 'CELERY_BROKER_URL')
        perf_checks.append({
            'check': 'Async Tasks (Celery)',
            'status': 'PASS' if has_celery else 'INFO',
            'value': 'Configured' if has_celery else 'Not configured',
        })
        
        # Middleware count
        middleware = getattr(settings, 'MIDDLEWARE', [])
        perf_checks.append({
            'check': 'Middleware Count',
            'status': 'PASS' if len(middleware) < 20 else 'WARNING',
            'value': len(middleware),
        })
        
        # Template caching
        templates = getattr(settings, 'TEMPLATES', [{}])
        loaders = templates[0].get('OPTIONS', {}).get('loaders', [])
        cached_loader = any('cached' in str(l).lower() for l in loaders) if loaders else False
        perf_checks.append({
            'check': 'Template Caching',
            'status': 'PASS' if cached_loader or not getattr(settings, 'DEBUG', True) else 'WARNING',
            'value': 'Enabled' if cached_loader else 'Auto (DEBUG dependent)',
        })
        
        # REST Framework pagination
        rf_settings = getattr(settings, 'REST_FRAMEWORK', {})
        has_pagination = 'PAGE_SIZE' in rf_settings or 'DEFAULT_PAGINATION_CLASS' in rf_settings
        perf_checks.append({
            'check': 'API Pagination',
            'status': 'PASS' if has_pagination else 'WARNING',
            'value': rf_settings.get('PAGE_SIZE', 'Not set'),
        })
        
        # Compression middleware
        has_gzip = any('gzip' in m.lower() for m in middleware)
        perf_checks.append({
            'check': 'GZIP Compression',
            'status': 'PASS' if has_gzip else 'WARNING',
            'value': 'Enabled' if has_gzip else 'Disabled',
        })
        
        stats = {
            'total_checks': len(perf_checks),
            'passed': len([c for c in perf_checks if c['status'] == 'PASS']),
            'warnings': len([c for c in perf_checks if c['status'] == 'WARNING']),
        }
        
        result = {
            'statistics': stats,
            'checks': perf_checks,
        }
        
        self.log(f"✓ Performance Checks: {stats['passed']}/{stats['total_checks']} optimal", 'success')
        
        self.log("\n📊 Performance Checks:")
        for check in perf_checks:
            icon = '✓' if check['status'] == 'PASS' else ('⚠' if check['status'] == 'WARNING' else 'ℹ')
            color = 'success' if check['status'] == 'PASS' else ('warning' if check['status'] == 'WARNING' else 'info')
            self.log(f"  {icon} {check['check']}: {check['value']}", color)
        
        self.results['analysis']['performance'] = result
        return result

    # =========================================================================
    # DEPENDENCIES ANALYSIS
    # =========================================================================
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze project dependencies"""
        self.section("📦 DEPENDENCIES ANALYSIS")
        
        requirements_file = BASE_DIR / 'requirements.txt'
        dependencies = []
        
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse package==version
                        if '==' in line:
                            name, version = line.split('==', 1)
                        elif '>=' in line:
                            name, version = line.split('>=', 1)
                        elif '<=' in line:
                            name, version = line.split('<=', 1)
                        else:
                            name, version = line, ''
                        dependencies.append({
                            'name': name.strip(),
                            'version': version.strip(),
                        })
        
        # Categorize dependencies
        categories = {
            'django_core': [],
            'django_extensions': [],
            'api': [],
            'database': [],
            'caching': [],
            'async': [],
            'security': [],
            'testing': [],
            'utilities': [],
            'other': []
        }
        
        for dep in dependencies:
            name = dep['name'].lower()
            if name == 'django':
                categories['django_core'].append(dep)
            elif name.startswith('django-') or name.startswith('django_'):
                categories['django_extensions'].append(dep)
            elif any(x in name for x in ['rest', 'drf', 'api', 'graphql', 'graphene']):
                categories['api'].append(dep)
            elif any(x in name for x in ['psycopg', 'mysql', 'postgres', 'sqlalchemy', 'pymongo']):
                categories['database'].append(dep)
            elif any(x in name for x in ['redis', 'memcache', 'cache']):
                categories['caching'].append(dep)
            elif any(x in name for x in ['celery', 'channels', 'async', 'websocket']):
                categories['async'].append(dep)
            elif any(x in name for x in ['crypt', 'auth', 'jwt', 'oauth', 'security']):
                categories['security'].append(dep)
            elif any(x in name for x in ['pytest', 'test', 'coverage', 'mock', 'faker']):
                categories['testing'].append(dep)
            elif any(x in name for x in ['pillow', 'boto', 'requests', 'numpy', 'pandas']):
                categories['utilities'].append(dep)
            else:
                categories['other'].append(dep)
        
        stats = {
            'total_dependencies': len(dependencies),
            'categories': {k: len(v) for k, v in categories.items()},
        }
        
        result = {
            'statistics': stats,
            'dependencies': dependencies,
            'categories': {k: [d['name'] for d in v] for k, v in categories.items()},
        }
        
        self.log(f"✓ Total Dependencies: {stats['total_dependencies']}", 'success')
        
        self.log("\n📊 Dependencies by Category:")
        for cat, deps in categories.items():
            if deps:
                self.log(f"  • {cat.replace('_', ' ').title()}: {len(deps)}")
        
        # Check for outdated
        critical_deps = ['django', 'djangorestframework', 'celery', 'redis', 'psycopg2-binary']
        self.log("\n📊 Critical Dependencies:")
        for dep in dependencies:
            if dep['name'].lower() in [d.lower() for d in critical_deps]:
                self.log(f"  • {dep['name']}: {dep['version'] or 'any'}")
        
        self.results['analysis']['dependencies'] = result
        return result

    # =========================================================================
    # CODE QUALITY ANALYSIS
    # =========================================================================
    
    def analyze_code_quality(self) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        self.section("📝 CODE QUALITY ANALYSIS")
        
        metrics = {
            'python_files': 0,
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'docstring_count': 0,
            'class_count': 0,
            'function_count': 0,
            'files_with_docstrings': 0,
        }
        
        # Scan Python files
        for py_file in BASE_DIR.rglob('*.py'):
            # Skip migrations, venv, etc.
            if any(x in str(py_file) for x in ['migrations', 'venv', 'env', '__pycache__', '.git', 'node_modules']):
                continue
                
            metrics['python_files'] += 1
            
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    metrics['total_lines'] += len(lines)
                    
                    in_docstring = False
                    has_docstring = False
                    
                    for line in lines:
                        stripped = line.strip()
                        
                        if not stripped:
                            metrics['blank_lines'] += 1
                        elif stripped.startswith('#'):
                            metrics['comment_lines'] += 1
                        elif '"""' in stripped or "'''" in stripped:
                            metrics['docstring_count'] += 1
                            has_docstring = True
                            in_docstring = not in_docstring
                        elif stripped.startswith('class '):
                            metrics['class_count'] += 1
                            metrics['code_lines'] += 1
                        elif stripped.startswith('def '):
                            metrics['function_count'] += 1
                            metrics['code_lines'] += 1
                        else:
                            metrics['code_lines'] += 1
                    
                    if has_docstring:
                        metrics['files_with_docstrings'] += 1
            except:
                pass
        
        # Calculate ratios
        if metrics['total_lines'] > 0:
            metrics['comment_ratio'] = int(round((metrics['comment_lines'] / metrics['total_lines']) * 100, 2))
            metrics['blank_ratio'] = int(round((metrics['blank_lines'] / metrics['total_lines']) * 100, 2))
        
        if metrics['python_files'] > 0:
            metrics['avg_lines_per_file'] = int(round(metrics['total_lines'] / metrics['python_files'], 2))
            metrics['docstring_coverage'] = int(round((metrics['files_with_docstrings'] / metrics['python_files']) * 100, 2))
        
        result = {
            'metrics': metrics,
        }
        
        self.log(f"✓ Python Files: {metrics['python_files']}", 'success')
        self.log(f"  • Total Lines: {metrics['total_lines']:,}")
        self.log(f"  • Code Lines: {metrics['code_lines']:,}")
        self.log(f"  • Comment Lines: {metrics['comment_lines']:,} ({metrics.get('comment_ratio', 0)}%)")
        self.log(f"  • Blank Lines: {metrics['blank_lines']:,} ({metrics.get('blank_ratio', 0)}%)")
        self.log(f"  • Classes: {metrics['class_count']:,}")
        self.log(f"  • Functions: {metrics['function_count']:,}")
        self.log(f"  • Docstring Coverage: {metrics.get('docstring_coverage', 0)}%")
        self.log(f"  • Avg Lines/File: {metrics.get('avg_lines_per_file', 0)}")
        
        if metrics.get('comment_ratio', 0) < 5:
            self.recommendations.append({
                'category': 'code_quality',
                'severity': 'low',
                'message': f"Comment ratio is {metrics.get('comment_ratio', 0)}%. Consider adding more comments."
            })
        
        self.results['analysis']['code_quality'] = result
        return result

    # =========================================================================
    # SUMMARY & RECOMMENDATIONS
    # =========================================================================
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary"""
        self.section("📋 ANALYSIS SUMMARY")
        
        summary = {
            'timestamp': self.results['timestamp'],
            'system': 'Tony ERP',
            'overall_health': 'GOOD',
            'key_metrics': {},
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors),
            'recommendations_count': len(self.recommendations),
        }
        
        # Extract key metrics
        if 'apps' in self.results['analysis']:
            summary['key_metrics']['apps'] = self.results['analysis']['apps']['statistics']['custom_apps']
        if 'models' in self.results['analysis']:
            summary['key_metrics']['models'] = self.results['analysis']['models']['statistics']['total_models']
        if 'urls' in self.results['analysis']:
            summary['key_metrics']['urls'] = self.results['analysis']['urls']['statistics']['total_urls']
        if 'database' in self.results['analysis']:
            summary['key_metrics']['tables'] = self.results['analysis']['database']['statistics']['total_tables']
        if 'security' in self.results['analysis']:
            summary['key_metrics']['security_score'] = self.results['analysis']['security']['statistics']['score']
        
        # Determine overall health
        if len(self.errors) > 0:
            summary['overall_health'] = 'CRITICAL'
        elif len(self.warnings) > 5:
            summary['overall_health'] = 'NEEDS_ATTENTION'
        elif len(self.warnings) > 0:
            summary['overall_health'] = 'GOOD'
        else:
            summary['overall_health'] = 'EXCELLENT'
        
        self.results['summary'] = summary
        self.results['warnings'] = self.warnings
        self.results['errors'] = self.errors
        self.results['recommendations'] = self.recommendations
        
        health_color = {
            'EXCELLENT': 'success',
            'GOOD': 'success',
            'NEEDS_ATTENTION': 'warning',
            'CRITICAL': 'error'
        }
        
        self.log(f"\n✓ Overall Health: {summary['overall_health']}", health_color.get(summary['overall_health'], 'info'))
        
        self.log("\n📊 Key Metrics:")
        for key, value in summary['key_metrics'].items():
            self.log(f"  • {key.replace('_', ' ').title()}: {value}")
        
        if self.recommendations:
            self.log(f"\n💡 Recommendations ({len(self.recommendations)}):")
            for rec in self.recommendations[:5]:
                self.log(f"  [{rec['severity'].upper()}] {rec['message']}", 'warning')
        
        if self.errors:
            self.log(f"\n❌ Errors ({len(self.errors)}):", 'error')
            for err in self.errors[:5]:
                self.log(f"  • {err.get('check', err)}", 'error')
        
        return summary

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================
    
    def generate_report(self, format: str = 'json') -> str:
        """Generate report in specified format"""
        output_dir = BASE_DIR / 'docs' / 'spec-kit' / 'reports'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'analysis_report_{timestamp}.json'  # Default
        
        if format == 'json':
            output_file = output_dir / f'analysis_report_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
                
        elif format == 'md':
            output_file = output_dir / f'analysis_report_{timestamp}.md'
            md_content = self._generate_markdown_report()
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
        elif format == 'html':
            output_file = output_dir / f'analysis_report_{timestamp}.html'
            html_content = self._generate_html_report()
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        self.log(f"\n📄 Report saved to: {output_file}", 'success')
        return str(output_file)
    
    def _generate_markdown_report(self) -> str:
        """Generate Markdown report"""
        lines = [
            "# Tony ERP - Spec-Kit Analysis Report",
            f"\n**Generated:** {self.results['timestamp']}",
            f"\n**Overall Health:** {self.results.get('summary', {}).get('overall_health', 'N/A')}",
            "\n---\n",
        ]
        
        # Summary
        if 'summary' in self.results:
            lines.append("## 📋 Summary\n")
            for key, value in self.results['summary'].get('key_metrics', {}).items():
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            lines.append("")
        
        # Apps
        if 'apps' in self.results['analysis']:
            stats = self.results['analysis']['apps']['statistics']
            lines.append("## 📦 Apps Analysis\n")
            lines.append(f"- Total Apps: {stats['total_apps']}")
            lines.append(f"- Custom Apps: {stats['custom_apps']}")
            lines.append(f"- Third-party Apps: {stats['third_party_apps']}")
            lines.append("")
        
        # Models
        if 'models' in self.results['analysis']:
            stats = self.results['analysis']['models']['statistics']
            lines.append("## 📊 Models Analysis\n")
            lines.append(f"- Total Models: {stats['total_models']}")
            lines.append(f"- Total Fields: {stats['total_fields']}")
            lines.append(f"- Total Relationships: {stats['total_relationships']}")
            lines.append("")
        
        # URLs
        if 'urls' in self.results['analysis']:
            stats = self.results['analysis']['urls']['statistics']
            lines.append("## 🔗 URLs Analysis\n")
            lines.append(f"- Total URLs: {stats['total_urls']}")
            lines.append(f"- API URLs: {stats['api_urls']}")
            lines.append(f"- Named URLs: {stats['named_urls']}")
            lines.append("")
        
        # Security
        if 'security' in self.results['analysis']:
            stats = self.results['analysis']['security']['statistics']
            lines.append("## 🔐 Security Analysis\n")
            lines.append(f"- Security Score: {stats['score']}%")
            lines.append(f"- Passed: {stats['passed']}")
            lines.append(f"- Warnings: {stats['warnings']}")
            lines.append(f"- Failed: {stats['failed']}")
            lines.append("")
        
        # Recommendations
        if self.recommendations:
            lines.append("## 💡 Recommendations\n")
            for rec in self.recommendations:
                lines.append(f"- [{rec['severity'].upper()}] {rec['message']}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_html_report(self) -> str:
        """Generate HTML report"""
        summary = self.results.get('summary', {})
        health = summary.get('overall_health', 'UNKNOWN')
        health_color = {
            'EXCELLENT': '#28a745',
            'GOOD': '#28a745', 
            'NEEDS_ATTENTION': '#ffc107',
            'CRITICAL': '#dc3545'
        }.get(health, '#6c757d')
        
        html = f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tony ERP - Analysis Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1a237e, #283593); color: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .health-badge {{ display: inline-block; padding: 8px 20px; background: {health_color}; border-radius: 20px; font-weight: bold; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #1a237e; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }}
        .card .metric {{ font-size: 2rem; font-weight: bold; color: #1a237e; }}
        .section {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #1a237e; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; }}
        .check {{ display: flex; align-items: center; padding: 10px; border-radius: 5px; margin-bottom: 5px; }}
        .check.pass {{ background: #e8f5e9; }}
        .check.warning {{ background: #fff3e0; }}
        .check.fail {{ background: #ffebee; }}
        .check-icon {{ width: 24px; height: 24px; margin-right: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .recommendation {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #1a237e; }}
        .footer {{ text-align: center; padding: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 Tony ERP - Analysis Report</h1>
            <p>Generated: {self.results['timestamp']}</p>
            <div class="health-badge">{health}</div>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>📦 Apps</h3>
                <div class="metric">{summary.get('key_metrics', {}).get('apps', 'N/A')}</div>
                <p>Custom Applications</p>
            </div>
            <div class="card">
                <h3>📊 Models</h3>
                <div class="metric">{summary.get('key_metrics', {}).get('models', 'N/A')}</div>
                <p>Database Models</p>
            </div>
            <div class="card">
                <h3>🔗 URLs</h3>
                <div class="metric">{summary.get('key_metrics', {}).get('urls', 'N/A')}</div>
                <p>URL Endpoints</p>
            </div>
            <div class="card">
                <h3>🔐 Security</h3>
                <div class="metric">{summary.get('key_metrics', {}).get('security_score', 'N/A')}%</div>
                <p>Security Score</p>
            </div>
        </div>
"""
        
        # Security checks
        if 'security' in self.results['analysis']:
            html += """
        <div class="section">
            <h2>🔐 Security Checks</h2>
"""
            for check in self.results['analysis']['security']['checks']:
                status_class = check['status'].lower()
                icon = '✓' if check['status'] == 'PASS' else ('⚠' if check['status'] == 'WARNING' else '✗')
                html += f"""
            <div class="check {status_class}">
                <span class="check-icon">{icon}</span>
                <strong>{check['check']}</strong>: {check['status']}
            </div>
"""
            html += "</div>"
        
        # Recommendations
        if self.recommendations:
            html += """
        <div class="section">
            <h2>💡 Recommendations</h2>
"""
            for rec in self.recommendations:
                html += f"""
            <div class="recommendation">
                <strong>[{rec['severity'].upper()}]</strong> {rec['message']}
            </div>
"""
            html += "</div>"
        
        html += """
        <div class="footer">
            <p>Tony ERP Spec-Kit Analyzer | Generated automatically</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    # =========================================================================
    # MAIN ANALYSIS
    # =========================================================================
    
    def run_full_analysis(self):
        """Run complete system analysis"""
        self.log("\n" + "="*60, 'header')
        self.log("  TONY ERP - SPEC-KIT ANALYZER", 'header')
        self.log("  Full System Analysis", 'header')
        self.log("="*60, 'header')
        
        self.analyze_apps()
        self.analyze_models()
        self.analyze_urls()
        self.analyze_database()
        self.analyze_security()
        self.analyze_performance()
        self.analyze_dependencies()
        self.analyze_code_quality()
        self.generate_summary()
        
        return self.results
    
    def run_quick_analysis(self):
        """Run quick summary analysis"""
        self.log("\n" + "="*60, 'header')
        self.log("  TONY ERP - QUICK ANALYSIS", 'header')
        self.log("="*60, 'header')
        
        self.analyze_apps()
        self.analyze_models()
        self.analyze_urls()
        self.analyze_security()
        self.generate_summary()
        
        return self.results


def main():
    parser = argparse.ArgumentParser(description='Tony ERP Spec-Kit Analyzer')
    parser.add_argument('--quick', action='store_true', help='Run quick analysis')
    parser.add_argument('--apps', action='store_true', help='Analyze apps only')
    parser.add_argument('--models', action='store_true', help='Analyze models only')
    parser.add_argument('--urls', action='store_true', help='Analyze URLs only')
    parser.add_argument('--security', action='store_true', help='Analyze security only')
    parser.add_argument('--performance', action='store_true', help='Analyze performance only')
    parser.add_argument('--dependencies', action='store_true', help='Analyze dependencies only')
    parser.add_argument('--database', action='store_true', help='Analyze database only')
    parser.add_argument('--code', action='store_true', help='Analyze code quality only')
    parser.add_argument('--report', choices=['json', 'md', 'html'], help='Generate report')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    analyzer = SpecKitAnalyzer(verbose=not args.quiet)
    
    # Run specific analysis or full
    if args.quick:
        analyzer.run_quick_analysis()
    elif args.apps:
        analyzer.analyze_apps()
        analyzer.generate_summary()
    elif args.models:
        analyzer.analyze_models()
        analyzer.generate_summary()
    elif args.urls:
        analyzer.analyze_urls()
        analyzer.generate_summary()
    elif args.security:
        analyzer.analyze_security()
        analyzer.generate_summary()
    elif args.performance:
        analyzer.analyze_performance()
        analyzer.generate_summary()
    elif args.dependencies:
        analyzer.analyze_dependencies()
        analyzer.generate_summary()
    elif args.database:
        analyzer.analyze_database()
        analyzer.generate_summary()
    elif args.code:
        analyzer.analyze_code_quality()
        analyzer.generate_summary()
    else:
        analyzer.run_full_analysis()
    
    # Generate report if requested
    if args.report:
        analyzer.generate_report(args.report)
    
    print(f"\n{'='*60}")
    print("  Analysis Complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
