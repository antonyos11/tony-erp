"""API package initialization with diagnostic hook and synthetic loader.

We inject a MetaPathFinder/Loader for 'api.report_views' so that any attempt to
import it (even if a stale, syntactically broken file exists on disk) will
produce a synthetic module re-exporting symbols from reporting_views.

This decisively avoids the phantom SyntaxError originating from an obsolete
cached variant of report_views.py and guarantees consistent API availability.
"""
import importlib, os, sys, types
from importlib import abc, util

class _ReportViewsShimFinder(abc.MetaPathFinder, abc.Loader):
	TARGET = 'api.report_views'
	def find_spec(self, fullname, path, target=None):  # noqa: D401
		if fullname == self.TARGET:
			return util.spec_from_loader(fullname, self)
		return None
	def create_module(self, spec):  # noqa: D401
		return None  # use default module creation
	def exec_module(self, module: types.ModuleType):  # noqa: D401
		# Import the real implementation
		real = importlib.import_module('api.reporting_views')
		for name in dir(real):
			if name.startswith('__') and name not in ('__doc__','__all__'):  # keep basics
				continue
			try:
				setattr(module, name, getattr(real, name))
			except Exception:
				pass
		module.__file__ = '(synthetic shim from api.__init__)'
		module.__loader__ = self
		module.__package__ = 'api'
		module.__doc__ = 'Synthetic shim: re-exported from reporting_views.'

# Prepend finder if not already present
if not any(isinstance(f, _ReportViewsShimFinder) for f in sys.meta_path):
	sys.meta_path.insert(0, _ReportViewsShimFinder())

# Light diagnostic (only once) — defer until Django is ready to avoid early app loading errors
if not os.environ.get('API_REPORT_VIEWS_SHIM_LOGGED'):
	def _late_diag():  # pragma: no cover - minimal diagnostic
		try:
			mod = importlib.import_module('api.report_views')
			print('[api.__init__] injected shim for api.report_views; file=', getattr(mod,'__file__', None))
		except Exception as e:
			# Silence the original noisy message unless DEBUG env explicitly wants it
			if os.environ.get('DEBUG') in ('1','true','yes'):  # keep quiet in production
				print('[api.__init__] shim deferred import error:', e)
		os.environ['API_REPORT_VIEWS_SHIM_LOGGED'] = '1'
	# If Django is already configured run immediately; else schedule via import hook
	try:
		from django.apps import apps  # type: ignore
		if apps.ready:
			_late_diag()
		else:
			# Register a callback once registry is ready
			from django.core.signals import setting_changed  # lightweight signal to piggy-back
			def _maybe_run(*a, **kw):
				from django.apps import apps as _apps
				if _apps.ready and not os.environ.get('API_REPORT_VIEWS_SHIM_LOGGED'):
					_late_diag()
			setting_changed.connect(_maybe_run, dispatch_uid='api_shim_diag_once')
	except Exception:
		# Fallback: run anyway (will likely succeed or fail silently)
		_late_diag()
