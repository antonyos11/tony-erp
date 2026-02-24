import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','accountant_pro.settings')
try:
    import django
    django.setup()
    from django.utils.translation import gettext as _
    samples = [
            '\u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u062d\u0643\u0645',  # لوحة التحكم
            '\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u062a\u062f\u0642\u064a\u0642',  # سجلات التدقيق
            '%(from)s-%(to)s relationship',  # internal format string
    ]
    try:
        from accountant_pro import settings
        print('LANGUAGE_CODE =', getattr(settings, 'LANGUAGE_CODE', '?'))
    except ImportError:
        print('LANGUAGE_CODE = Could not import settings')
    for s in samples:
        try:
            print('IN:', s, ' -> OUT:', _(s))
        except Exception as e:
            print('ERROR translating', s, e)
    print('SUCCESS: Translation system initialized.')
except Exception as e:
    print('FAILED during Django setup:', repr(e))
    raise
