import os, sys, json
print('CWD=', os.getcwd())
print('PY=', sys.executable)
print('PY_VER=', sys.version)
try:
    import django
    print('DJANGO_VER=', django.get_version())
    from django.conf import settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accountant_pro.settings')
    django.setup()
    print('DEBUG=', getattr(settings, 'DEBUG', None))
    print('DB_ENGINE=', settings.DATABASES['default']['ENGINE'])
    print('ALLOWED_HOSTS=', settings.ALLOWED_HOSTS[:5])
    print('STATIC_ROOT=', str(getattr(settings, 'STATIC_ROOT', '')))
    print('OK=1')
except Exception as e:
    print('ERR=', repr(e))
