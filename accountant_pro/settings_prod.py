"""Production settings for accountant_pro.
Derived from base settings with hardened security & explicit production toggles.
"""
from .settings import *  # noqa

# Force production flags
DEBUG = False
ENVIRONMENT = 'production'

# Require explicit hosts
_raw_hosts = os.getenv('PROD_ALLOWED_HOSTS') or os.getenv('ALLOWED_HOSTS', '')
if not _raw_hosts:
    raise RuntimeError('PROD_ALLOWED_HOSTS (or ALLOWED_HOSTS) must be set in production environment')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip() and h.strip() != '*']
if '*' in (_raw_hosts or '').split(','):
    # Disallow wildcard in production
    raise RuntimeError('Wildcard * not permitted for ALLOWED_HOSTS in production')

# Security cookies & HTTPS enforcement
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = bool(int(os.getenv('SECURE_SSL_REDIRECT', '1')))

# HSTS (enable via env for staged rollout)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1') == '1'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', '1') == '1'

# Content Security Policy (simple baseline; extend as needed)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'",)
CSP_IMG_SRC = ("'self'", 'data:',)
CSP_FONT_SRC = ("'self'", 'data:',)
CSP_CONNECT_SRC = ("'self'",)

# Override logging: reduce console noise; elevate warnings
for handler in LOGGING.get('root', {}).get('handlers', []):
    # root handlers already defined; we keep them but adjust level
    pass
LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Disable browsable API & reduce renderers
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']

# JWT tightening (shorter access lifetime if override provided)
from datetime import timedelta
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '30')))
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '3')))

# Enforce strong password min length (override if base was lower)
for v in AUTH_PASSWORD_VALIDATORS:
    if v.get('NAME','').endswith('MinimumLengthValidator'):
        v.setdefault('OPTIONS', {})
        v['OPTIONS']['min_length'] = max(12, v['OPTIONS'].get('min_length', 12))

# Email backend MUST be explicit; fail if still console backend (unless explicitly allowed)
if os.getenv('ALLOW_CONSOLE_EMAIL', '0') != '1' and EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
    raise RuntimeError('EMAIL_BACKEND must be configured for production (set ALLOW_CONSOLE_EMAIL=1 to bypass)')

# CORS: restrict unless explicitly whitelisted
if 'CORS_ALLOW_ALL_ORIGINS' in globals():
    del globals()['CORS_ALLOW_ALL_ORIGINS']
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]

# Disable welcome banner
SHOW_WELCOME_BANNER = False

# Optional: ensure database not SQLite in production
if DATABASES['default']['ENGINE'].endswith('sqlite3') and os.getenv('ALLOW_SQLITE_PROD', '0') != '1':
    raise RuntimeError('SQLite not permitted in production (set ALLOW_SQLITE_PROD=1 to override temporarily)')

# Additional hardening toggles
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Rate limiting: allow overriding via env
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user'] = os.getenv('API_USER_THROTTLE_RATE', REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].get('user','1000/day'))
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['anon'] = os.getenv('API_ANON_THROTTLE_RATE', REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].get('anon','100/day'))

# Flag to identify production at runtime
IS_PRODUCTION = True
