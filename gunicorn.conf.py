"""
Gunicorn Configuration — RITA ERP
"""

bind    = '127.0.0.1:8000'
workers = 3
timeout = 120

# Logging
accesslog = '/var/www/rita-erp/logs/gunicorn_access.log'
errorlog  = '/var/www/rita-erp/logs/gunicorn_error.log'
loglevel  = 'info'

# Worker class
worker_class = 'sync'

# Process name
proc_name = 'rita-erp'

# Reload on code change (disable in production)
reload = False

# Max requests before worker restart (prevents memory leaks)
max_requests          = 1000
max_requests_jitter   = 50

# Keep-alive
keepalive = 5
