import importlib, sys

try:
    rv = importlib.import_module('api.report_views')
    print('Imported api.report_views OK')
    print('File:', getattr(rv, '__file__', None))
    print('Attributes containing "Report":', [a for a in dir(rv) if 'Report' in a][:15])
except Exception as e:
    print('FAILED importing api.report_views:', e)
    raise
