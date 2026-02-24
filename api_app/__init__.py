"""New stable API package that proxies existing viewsets from legacy 'api'.
Adds a meta path shim so any import of 'api.urls' is transparently
redirected to 'api_app.urls' to defeat stale/phantom copies of the
original module.
"""

import sys, importlib
from importlib import abc, util

class _ApiUrlsRedirectFinder(abc.MetaPathFinder, abc.Loader):
	SRC = 'api.urls'
	DEST = 'api_app.urls'
	def find_spec(self, fullname, path, target=None):
		if fullname == self.SRC:
			return util.spec_from_loader(fullname, self)
		return None
	def create_module(self, spec):  # use default
		return None
	def exec_module(self, module):
		real = importlib.import_module(self.DEST)
		# Copy attributes
		for k,v in vars(real).items():
			if k.startswith('__') and k not in ('__all__','__doc__'): continue
			setattr(module, k, v)
		module.__file__ = '(redirect shim to %s)' % self.DEST
		module.__package__ = 'api'
		module.__doc__ = 'Redirect shim: api.urls -> api_app.urls'

if not any(isinstance(f, _ApiUrlsRedirectFinder) for f in sys.meta_path):
	sys.meta_path.insert(0, _ApiUrlsRedirectFinder())
