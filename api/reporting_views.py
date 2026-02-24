"""Reporting API Views (alternate module name to bypass phantom import issues with report_views).

Implements: Overview, Sales, Inventory, Purchases reports
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
from io import BytesIO, StringIO
import csv
from typing import Any, Dict, Iterable, List
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.utils.timezone import now
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, throttling
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer, BaseRenderer
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes
import logging
from reports import alerts
from reports.services import (
    get_overview_report,
    get_sales_report,
    get_inventory_report,
    get_purchases_report,
    parse_date,
    get_full_system_report,
    get_profit_loss_report,
    get_ar_aging_report,
    get_crm_pipeline_report,
    get_ap_aging_report,
    get_balance_sheet,
    get_cash_flow_report,
    get_inventory_turnover_report,
    get_stock_aging_report,
    get_snapshot_series,
    create_daily_snapshot,
)

# ---- Shared helpers ----
def _apply_variance_warning(report_name: str, data: dict, d_from, d_to, warn_threshold: float):
    """Apply variance warning & alert dispatch if both costing methods present.

    Keeps duplicated logic DRY across P&L and Inventory Turnover endpoints.
    Safe no-op if required keys missing.
    """
    try:
        if not isinstance(data, dict):
            return
        if 'fifo_vs_weighted_cogs_percent' not in data:
            return
        pct = abs(float(data.get('fifo_vs_weighted_cogs_percent') or 0))
        level = 'low'
        if pct >= 15:
            level = 'high'
        elif pct >= 5:
            level = 'medium'
        # Global minimal threshold override (settings.VARIANCE_ALERT_MIN_PERCENT) if higher
        threshold_used = warn_threshold
        global_min_applied = False
        try:
            from django.conf import settings
            global_min = getattr(settings, 'VARIANCE_ALERT_MIN_PERCENT', None)
            if global_min is not None:
                try:
                    gm = float(global_min)
                    if gm > threshold_used:
                        threshold_used = gm
                        global_min_applied = True
                except Exception:
                    pass
        except Exception:
            pass
        triggered = pct >= threshold_used
        data['variance_warning'] = {
            'metric': 'cogs_percent_diff_fifo_vs_weighted',
            'percent': pct,
            'threshold_used': threshold_used,
            'triggered': triggered,
            'level': level,
            'global_min_applied': global_min_applied,
        }
        if triggered and level == 'high':
            try:
                # Include level & global_min_applied for persistence/audit.
                alerts.send_variance_alert(report_name, pct, threshold_used, d_from, d_to, extra={'global_min_applied': global_min_applied, 'level': level})
            except Exception:
                pass
            # Increment counter (cache) for health endpoint visibility
            try:
                from django.core.cache import cache as _cache
                key = 'reports:variance:incidents'
                if _cache.get(key) is None:
                    _cache.set(key, 0, None)
                _cache.incr(key)
            except Exception:
                pass
    except Exception:
        # Never let variance decoration break base report response
        pass

class ReportsPermission(permissions.BasePermission):
    view_perm = 'reports.view_reports'
    export_perm = 'reports.export_reports'
    def has_permission(self, request, view):  # type: ignore[override]
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        if not user.has_perm(self.view_perm):
            return False
        export_format = request.query_params.get('export') or request.query_params.get('format')
        if export_format:
            # إن طلب تصدير بدون صلاحية نرفع مباشرة PermissionDenied لضمان 403 صريح
            if not user.has_perm(self.export_perm):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(detail='Export permission required')
            return True
        return True

class ReportsRateThrottle(throttling.UserRateThrottle):
    scope = 'reports'

class ExportMixin:
    EXPORT_PARAM = 'export'
    EXPORT_FORMATS = {'csv','xlsx'}
    def maybe_export(self, request, base_filename: str, rows: Iterable[Dict[str, Any]]):
        fmt = (request.query_params.get(self.EXPORT_PARAM) or request.query_params.get('format') or '').lower()
        if not fmt:
            return None
        if fmt not in self.EXPORT_FORMATS and fmt not in ('txt',):
            return Response({'detail':'Unsupported export format'}, status=400)
        rows_list = list(rows)
        filename = f"{base_filename}_{now().strftime('%Y%m%d_%H%M%S')}"
        if fmt in ('csv','txt'):
            if len(rows_list) > 5000:
                resp = self.stream_csv(filename, iter(rows_list))
            else:
                resp = self._export_csv(filename, rows_list)
            # Optional gzip compression for large CSV exports (>50k rows) unless disabled
            force_compress = request.query_params.get('force_compress') == '1'
            if fmt == 'csv' and (force_compress or len(rows_list) > 50000) and request.query_params.get('no_compress') != '1':
                import gzip
                import io
                raw = resp.content  # type: ignore[attr-defined]
                gz_buf = io.BytesIO()
                with gzip.GzipFile(filename='data.csv', mode='wb', fileobj=gz_buf) as gz:
                    gz.write(raw)
                gz_buf.seek(0)
                c = gz_buf.read()
                resp = HttpResponse(c, content_type='text/csv')
                resp['Content-Encoding'] = 'gzip'
                resp['Content-Disposition'] = resp.get('Content-Disposition', f'attachment; filename="{filename}.csv.gz"')
            return resp
        return self._export_xlsx(filename, rows_list)

    # Experimental streaming (large datasets) – if rows length exceeds threshold and format csv
    def stream_csv(self, filename: str, rows_iter):  # rows_iter yields dict rows
        from django.http import StreamingHttpResponse
        def row_iter():
            header_written = False
            header = []
            yield '\ufeff'
            for r in rows_iter:
                if not header_written:
                    header = list(r.keys())
                    yield ','.join(header) + '\n'
                    header_written = True
                yield ','.join(str(r.get(h,'')) for h in header) + '\n'
        resp = StreamingHttpResponse(row_iter(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition']=f'attachment; filename="{filename}.csv"'
        return resp
    def _export_csv(self, filename: str, rows: List[Dict[str, Any]]):
        if not rows:
            rows=[{}]
        headers=list(rows[0].keys())
        sio=StringIO()
        w=csv.DictWriter(sio, fieldnames=headers, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k:self._cell(v) for k,v in r.items()})
        data='\ufeff'+sio.getvalue()
        resp=HttpResponse(data, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition']=f'attachment; filename="{filename}.csv"'
        return resp
    def _export_xlsx(self, filename: str, rows: List[Dict[str, Any]]):
        try:
            import openpyxl  # type: ignore
        except Exception:
            return self._export_csv(filename, rows)
        if not rows:
            rows=[{}]
        headers=list(rows[0].keys())
        wb=openpyxl.Workbook(); ws=wb.active; assert ws is not None
        if ws: ws.append(headers)
        for r in rows:
            if ws: ws.append([self._cell(r.get(h)) for h in headers])
        bio=BytesIO(); wb.save(bio); bio.seek(0)
        resp=HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition']=f'attachment; filename="{filename}.xlsx"'
        return resp
    @staticmethod
    def _cell(v: Any):
        if v is None: return ''
        if isinstance(v,(int,float,str)): return v
        return smart_str(v)

class CSVRenderer(BaseRenderer):  # top-level so DRF can introspect reliably
    media_type='text/csv'
    format='csv'
    charset='utf-8'
    def render(self, data, accepted_media_type=None, renderer_context=None):  # type: ignore[override]
        if data is None:
            return b''
        if not isinstance(data, (list, tuple)):
            return smart_str(data).encode('utf-8')
        if not data:
            return b''
        first=data[0]
        if isinstance(first, dict):
            sio=StringIO(); w=csv.DictWriter(sio, fieldnames=list(first.keys()))
            w.writeheader()
            for row in data:
                if isinstance(row, dict):
                    w.writerow({k: ('' if v is None else v) for k,v in row.items()})
            return ('\ufeff'+sio.getvalue()).encode('utf-8')
        return ('\n'.join(smart_str(x) for x in data)).encode('utf-8')

@extend_schema_view(get=extend_schema(responses=OpenApiTypes.OBJECT))
class BaseReportView(ExportMixin, APIView):
    permission_classes=[ReportsPermission]
    throttle_classes=[ReportsRateThrottle]
    renderer_classes=[JSONRenderer, BrowsableAPIRenderer, CSVRenderer]
    cache_timeout=300
    cache_key_prefix=''
    def initial(self, request, *args, **kwargs):  # type: ignore[override]
        # Capture start time for lightweight performance timing (per request)
        self._start_time = time.perf_counter()
        return super().initial(request, *args, **kwargs)
    def _ck(self, *parts: Any) -> str:
        """Build a cache key.

        Historically this method accepted a single suffix string. Some legacy
        code (and future defensive usage) may call it with multiple positional
        arguments – e.g. self._ck(as_of, limit). To avoid a repeat of the
        earlier TypeError (BaseReportView._ck() takes 2 positional arguments but 3 were given)
        we now accept *parts and join them with ':' while skipping empties.
        Any None values are ignored to keep keys stable.
        """
        if not parts:
            suffix = 'v1'
        elif len(parts) == 1:
            suffix = str(parts[0])
        else:
            suffix = ':'.join(str(p) for p in parts if p is not None and str(p)!='')
        return f"reports:{self.cache_key_prefix}:{suffix}"
    def method_cache_key(self, *parts: Any, method: str | None = None) -> str:
        # Distinguish costing / calculation method variants explicitly to avoid collisions
        m = method or 'auto'
        return self._ck(*(list(parts) + [f"m={m}"]))
    def _get(self, key: str):
        """Fetch from cache while tracking hit/miss stats per prefix.

        Uses two simple integer keys (hits, misses). We guard incr with set on
        first use because Django's cache.incr requires the key to exist.
        """
        val = cache.get(key)
        hits_key = f"reports:stats:{self.cache_key_prefix}:hits"
        misses_key = f"reports:stats:{self.cache_key_prefix}:misses"
        if val is not None:
            try:
                cache.incr(hits_key)
            except ValueError:
                cache.set(hits_key, 1, None)
        else:
            try:
                cache.incr(misses_key)
            except ValueError:
                cache.set(misses_key, 1, None)
        return val
    def _set(self,key:str,val:Any):
        cache.set(key,val,self.cache_timeout)
    def _maybe_stats(self, request, payload: dict) -> dict:
        # Only augment when stats=1 and payload is a dict (avoid mutating non-dict responses)
        if request.query_params.get('stats') != '1' or not isinstance(payload, dict):
            return payload
        if 'cache_stats' in payload:  # already processed
            return payload
        hits = cache.get(f"reports:stats:{self.cache_key_prefix}:hits") or 0
        misses = cache.get(f"reports:stats:{self.cache_key_prefix}:misses") or 0
        new_payload = dict(payload)
        new_payload['cache_stats'] = {'hits': hits, 'misses': misses}
        if hasattr(self, '_start_time'):
            try:
                elapsed_ms = (time.perf_counter() - self._start_time) * 1000
                new_payload['timing_ms'] = round(elapsed_ms, 2)
                # Rolling average timing aggregation (non-atomic but sufficient for diagnostics)
                try:
                    sum_key = f"reports:perf:{self.cache_key_prefix}:sum_ms"
                    cnt_key = f"reports:perf:{self.cache_key_prefix}:count"
                    cur_sum = cache.get(sum_key) or 0.0
                    cur_cnt = cache.get(cnt_key) or 0
                    cur_sum += elapsed_ms
                    cur_cnt += 1
                    cache.set(sum_key, cur_sum, None)
                    cache.set(cnt_key, cur_cnt, None)
                    avg = cur_sum / cur_cnt if cur_cnt else elapsed_ms
                    new_payload['avg_ms'] = round(avg, 2)
                except Exception:
                    pass
            except Exception:
                pass
        return new_payload

class ReportsOverviewAPI(BaseReportView):
    cache_key_prefix = 'overview'
    def get(self, request, format=None):  # type: ignore[override]
        k = self._ck('v1')
        data = self._get(k) or get_overview_report()
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'overview_top_products', data.get('top_products', []))
        return exp or Response(data)

class SalesReportAPI(BaseReportView):
    cache_key_prefix = 'sales'
    cache_timeout = 120
    def get(self, request, format=None):  # type: ignore[override]
        export_fmt = request.query_params.get('export') or request.query_params.get('format')
        if export_fmt and not (request.user.is_superuser or request.user.has_perm(ReportsPermission.export_perm)):
            return Response({'detail': 'Export permission required'}, status=403)
        today = date.today(); default_from = today - timedelta(days=30)
        d_from = parse_date(request.query_params.get('date_from', ''), default_from)
        d_to = parse_date(request.query_params.get('date_to', ''), today)
        if d_to < d_from:
            return Response({'detail': 'date_to must be >= date_from'}, status=400)
        def to_int(v):
            if not v:
                return None
            try:
                return int(v)
            except ValueError:
                raise
        try:
            customer_id = to_int(request.query_params.get('customer'))
        except ValueError:
            return Response({'detail': 'Invalid customer id'}, status=400)
        try:
            product_id = to_int(request.query_params.get('product'))
        except ValueError:
            return Response({'detail': 'Invalid product id'}, status=400)
        k = self._ck(f"{d_from}:{d_to}:{customer_id}:{product_id}")
        data = self._get(k) or get_sales_report(d_from, d_to, customer_id, product_id)
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'sales_top_products', data.get('top_products', []))
        return exp or Response(data)

class InventoryReportAPI(BaseReportView):
    cache_key_prefix = 'inventory'
    def get(self, request, format=None):  # type: ignore[override]
        k = self._ck('v1')
        data = self._get(k) or get_inventory_report()
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'inventory_low_stock', data.get('low_stock_products', []))
        return exp or Response(data)

class PurchasesReportAPI(BaseReportView):
    cache_key_prefix = 'purchases'
    cache_timeout = 120
    def get(self, request, format=None):  # type: ignore[override]
        today = date.today(); default_from = today - timedelta(days=30)
        d_from = parse_date(request.query_params.get('date_from', ''), default_from)
        d_to = parse_date(request.query_params.get('date_to', ''), today)
        if d_to < d_from:
            return Response({'detail': 'date_to must be >= date_from'}, status=400)
        supplier = request.query_params.get('supplier')
        try:
            supplier_id = int(supplier) if supplier else None
        except ValueError:
            return Response({'detail': 'Invalid supplier id'}, status=400)
        k = self._ck(f"{d_from}:{d_to}:{supplier_id}")
        data = self._get(k) or get_purchases_report(d_from, d_to, supplier_id)
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'purchases_top_suppliers', data.get('top_suppliers', []))
        return exp or Response(data)

__all__=['ReportsOverviewAPI','SalesReportAPI','InventoryReportAPI','PurchasesReportAPI','ReportsPermission']
class FullSystemReportAPI(BaseReportView):
    cache_key_prefix = 'full_system'
    cache_timeout = 180
    def get(self, request, format=None):  # type: ignore[override]
        k = self._ck('v1')
        data = self._get(k) or get_full_system_report()
        if data and not self._get(k):
            self._set(k, data)
        overview_top: list = []
        try:
            overview_top = data.get('overview', {}).get('top_products', [])  # type: ignore[assignment]
        except Exception:
            overview_top = []
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'full_overview_top_products', overview_top)
        return exp or Response(data)

__all__+=['FullSystemReportAPI']

class ProfitLossReportAPI(BaseReportView):
    cache_key_prefix='pl'; cache_timeout=180
    def get(self,request,format=None):
        today=date.today(); default_from=today - timedelta(days=30)
        d_from=parse_date(request.query_params.get('date_from',''), default_from)
        d_to=parse_date(request.query_params.get('date_to',''), today)
        if d_to < d_from: return Response({'detail':'date_to must be >= date_from'}, status=400)
        raw_method = request.query_params.get('cogs_method')
        cogs_method: Optional[str]
        if not raw_method:
            cogs_method = None  # auto mode (service decides best method)
        else:
            rm = raw_method.strip().lower()
            if rm in ('approx','fifo','weighted'):
                cogs_method = rm
            elif rm in ('auto','default'):
                cogs_method = None
            else:
                return Response({'detail':'Invalid cogs_method'}, status=400)
        compare_all = request.query_params.get('compare') == '1'
        # Parse variance warning threshold (only used when compare_all)
        warn_threshold_param = request.query_params.get('warn_threshold')
        try:
            warn_threshold = float(warn_threshold_param) if warn_threshold_param is not None else 5.0
        except Exception:
            warn_threshold = 5.0
        k = self.method_cache_key(f"{d_from}:{d_to}:cmp={int(compare_all)}", method=cogs_method)
        data = self._get(k) or get_profit_loss_report(d_from,d_to,cogs_method, compare_all=compare_all)
        if data and not self._get(k):
            self._set(k,data)
        # Variance warning logic (does not affect cache contents)
        if compare_all:
            _apply_variance_warning('profit_loss', data, d_from, d_to, warn_threshold)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request,'profit_loss',[data])
        return exp or Response(data)

class ARAgingReportAPI(BaseReportView):
    cache_key_prefix = 'ar_aging'
    cache_timeout = 300
    def get(self, request, format=None):  # type: ignore[override]
        today = date.today()
        as_of = parse_date(request.query_params.get('as_of', ''), today)
        k = self._ck(as_of.isoformat())
        data = self._get(k) or get_ar_aging_report(as_of)
        # Optional previous period delta (same length back) if ?compare=1
        if request.query_params.get('compare') == '1':
            prev_as_of = as_of - timedelta(days=30)
            prev = get_ar_aging_report(prev_as_of)
            data['previous_period'] = prev
            data['total_outstanding_delta'] = data.get('total_outstanding',0) - prev.get('total_outstanding',0)
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'ar_aging_customers', data.get('customers', []))
        return exp or Response(data)

class CRMPipelineReportAPI(BaseReportView):
    cache_key_prefix = 'crm_pipeline'
    cache_timeout = 180
    def get(self, request, format=None):  # type: ignore[override]
        k = self._ck('v1')
        data = self._get(k) or get_crm_pipeline_report()
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'crm_pipeline_stages', data.get('stages', []))
        return exp or Response(data)

__all__+=['ProfitLossReportAPI','ARAgingReportAPI','CRMPipelineReportAPI']
class APAgingReportAPI(BaseReportView):
    cache_key_prefix = 'ap_aging'
    cache_timeout = 300
    def get(self, request, format=None):  # type: ignore[override]
        as_of = parse_date(request.query_params.get('as_of', ''), date.today())
        k = self._ck(as_of.isoformat())
        data = self._get(k) or get_ap_aging_report(as_of)
        if request.query_params.get('compare') == '1':
            prev_as_of = as_of - timedelta(days=30)
            prev = get_ap_aging_report(prev_as_of)
            data['previous_period'] = prev
            data['total_outstanding_delta'] = data.get('total_outstanding',0) - prev.get('total_outstanding',0)
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'ap_aging_suppliers', data.get('suppliers', []))
        return exp or Response(data)

class BalanceSheetAPI(BaseReportView):
    cache_key_prefix = 'balance_sheet'
    cache_timeout = 300
    def get(self, request, format=None):  # type: ignore[override]
        as_of = parse_date(request.query_params.get('as_of', ''), date.today())
        k = self._ck(as_of.isoformat())
        data = self._get(k) or get_balance_sheet(as_of)
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        return Response(data)

__all__+=['APAgingReportAPI','BalanceSheetAPI']

class CashFlowReportAPI(BaseReportView):
    cache_key_prefix = 'cash_flow'
    cache_timeout = 180
    def get(self, request, format=None):  # type: ignore[override]
        today = date.today(); default_from = today - timedelta(days=30)
        d_from = parse_date(request.query_params.get('date_from', ''), default_from)
        d_to = parse_date(request.query_params.get('date_to', ''), today)
        if d_to < d_from:
            return Response({'detail': 'date_to must be >= date_from'}, status=400)
        k = self._ck(f"{d_from}:{d_to}")
        data = self._get(k) or get_cash_flow_report(d_from, d_to)
        # Add monthly series if requested
        if request.query_params.get('series') == '1':
            series: list[dict[str, Any]] = []  # type: ignore[name-defined]
            cur_start = date(d_from.year, d_from.month, 1)
            while cur_start <= d_to:
                # month end
                if cur_start.month == 12:
                    month_end = date(cur_start.year, 12, 31)
                else:
                    month_end = date(cur_start.year, cur_start.month + 1, 1) - timedelta(days=1)
                month_end = min(month_end, d_to)
                rep = get_cash_flow_report(cur_start, month_end)
                series.append({
                    'month': cur_start.strftime('%Y-%m'),
                    'net_operating': rep['operating']['net_operating'],
                    'net_total': rep['net_total'],
                    'inflows': rep['operating']['inflows']['total_inflows'],
                    'outflows': rep['operating']['outflows']['total_outflows'],
                })
                # advance
                if cur_start.month == 12:
                    cur_start = date(cur_start.year + 1, 1, 1)
                else:
                    cur_start = date(cur_start.year, cur_start.month + 1, 1)
            data['monthly_series'] = series
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'cash_flow_summary', [{k: v for k, v in data.items() if isinstance(v, (int, float, str))}])
        return exp or Response(data)

class InventoryTurnoverReportAPI(BaseReportView):
    cache_key_prefix='inv_turnover'; cache_timeout=300
    def get(self,request,format=None):
        today=date.today(); default_from=today - timedelta(days=90)
        d_from=parse_date(request.query_params.get('date_from',''), default_from)
        d_to=parse_date(request.query_params.get('date_to',''), today)
        if d_to < d_from: return Response({'detail':'date_to must be >= date_from'}, status=400)
        raw_method = request.query_params.get('cogs_method')
        cogs_method: Optional[str]
        if not raw_method:
            cogs_method = None
        else:
            rm = raw_method.strip().lower()
            if rm in ('approx','fifo','weighted'):
                cogs_method = rm
            elif rm in ('auto','default'):
                cogs_method = None
            else:
                return Response({'detail':'Invalid cogs_method'}, status=400)
        compare_all = request.query_params.get('compare') == '1'
        warn_threshold_param = request.query_params.get('warn_threshold')
        try:
            warn_threshold = float(warn_threshold_param) if warn_threshold_param is not None else 5.0
        except Exception:
            warn_threshold = 5.0
        k = self.method_cache_key(f"{d_from}:{d_to}:cmp={int(compare_all)}", method=cogs_method)
        data = self._get(k) or get_inventory_turnover_report(d_from,d_to,cogs_method, compare_all=compare_all)
        if data and not self._get(k):
            self._set(k,data)
        if compare_all:
            _apply_variance_warning('inventory_turnover', data, d_from, d_to, warn_threshold)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request,'inventory_turnover',[data])
        return exp or Response(data)

class StockAgingReportAPI(BaseReportView):
    cache_key_prefix = 'stock_aging'
    cache_timeout = 600
    def get(self, request, format=None):  # type: ignore[override]
        as_of = parse_date(request.query_params.get('as_of', ''), date.today())
        limit_param = request.GET.get('limit')
        try:
            limit = int(limit_param) if limit_param else None
            if limit and limit < 0:
                limit = None
        except Exception:
            limit = None
        export_requested = bool(request.query_params.get('export') or request.query_params.get('format'))
        full_flag = request.query_params.get('all') == '1'
        # Support pagination via page & page_size when not exporting full
        page_param = request.GET.get('page')
        page_size_param = request.GET.get('page_size')
        try:
            page = int(page_param) if page_param else 1
            page_size = int(page_size_param) if page_size_param else 300
        except Exception:
            page = 1; page_size = 300
        page = max(page,1); page_size = max(50, min(page_size, 2000))
        slice_limit = None if (export_requested and not limit and full_flag) else (limit or (page * page_size))
        suffix = f"{as_of.isoformat()}:{slice_limit}" if slice_limit is not None else f"{as_of.isoformat()}:all"
        k = self._ck(suffix)
        data = self._get(k)
        if not data:
            data = get_stock_aging_report(as_of, slice_limit=None if slice_limit is None else slice_limit)
            if limit:
                data = {**data, 'limit_applied': limit}
            elif slice_limit is None:
                data = {**data, 'limit_applied': 'all'}
            self._set(k, data)
        # Apply page slice (non-export) if pagination used
        if slice_limit is not None and not export_requested and (page_param or page>1):
            products = data.get('products', [])
            start = (page-1)*page_size
            end = start + page_size
            data = {**data, 'products': products[start:end], 'page': page, 'page_size': page_size, 'total_products': len(products)}
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'stock_aging_products', data.get('products', []))
        return exp or Response(data)

class SnapshotSeriesAPI(BaseReportView):
    cache_key_prefix = 'snapshot_series'
    cache_timeout = 120
    def get(self, request, format=None):  # type: ignore[override]
        days_param = request.query_params.get('days')
        try:
            days = int(days_param) if days_param else 30
        except Exception:
            days = 30
        days = max(7, min(days, 365))
        k = self._ck(days)
        data = self._get(k) or {'days': days, 'series': get_snapshot_series(days)}
        if data and not self._get(k):
            self._set(k, data)
        data = self._maybe_stats(request, data)
        exp = self.maybe_export(request, 'daily_snapshots', data.get('series', []))
        return exp or Response(data)

class ReportsHealthAPI(BaseReportView):
    cache_key_prefix = 'health'
    cache_timeout = 30
    def get(self, request, format=None):  # type: ignore[override]
        # Lightweight health: cache stats summary + latest snapshot age
        latest_snapshot = None
        try:
            from reports.models import ReportDailySnapshot
            snap = ReportDailySnapshot.objects.order_by('-date').first()
            if snap:
                latest_snapshot = {'date': snap.date.strftime('%Y-%m-%d'), 'age_days': (date.today()-snap.date).days}
        except Exception:
            pass
        payload = {
            'cache': {
                'overview': {'hits': cache.get('reports:stats:overview:hits') or 0, 'misses': cache.get('reports:stats:overview:misses') or 0},
                'sales': {'hits': cache.get('reports:stats:sales:hits') or 0, 'misses': cache.get('reports:stats:sales:misses') or 0},
                'pl': {'hits': cache.get('reports:stats:pl:hits') or 0, 'misses': cache.get('reports:stats:pl:misses') or 0},
            },
            'variance_incidents': cache.get('reports:variance:incidents') or 0,
            'latest_snapshot': latest_snapshot,
            'timestamp': now().isoformat(),
        }
        return Response(self._maybe_stats(request, payload))

__all__+=['CashFlowReportAPI','InventoryTurnoverReportAPI','StockAgingReportAPI']


class ReportsVarianceIncidentsAPI(BaseReportView):
    cache_key_prefix = 'variance_incidents'
    cache_timeout = 15
    def get(self, request, format=None):  # type: ignore[override]
        # Filters
        report_filter = request.query_params.get('report') or ''
        d_from_raw = request.query_params.get('date_from')
        d_to_raw = request.query_params.get('date_to')
        limit_param = request.query_params.get('limit')  # legacy optional cap
        export = request.query_params.get('export')
        page_param = request.query_params.get('page')
        page_size_param = request.query_params.get('page_size')
        ordering = request.query_params.get('ordering', '-created_at')

        # Parse paging / limits
        def _int(val, default):
            try:
                return int(val) if val is not None else default
            except Exception:
                return default
        limit_cap = _int(limit_param, 0)
        page = max(1, _int(page_param, 1))
        page_size = _int(page_size_param, 50)
        page_size = max(1, min(page_size, 500 if not export else 2000))
        overall_cap = limit_cap if limit_cap > 0 else (2000 if export else 5000)
        allowed_order = {'created_at','-created_at','percent','-percent'}
        if ordering not in allowed_order:
            ordering = '-created_at'

        ck = self._ck(report_filter or 'all', d_from_raw or 'na', d_to_raw or 'na', f"p{page}", f"s{page_size}", ordering, 'exp' if export else 'noexp')
        cached = None if export else self._get(ck)
        if cached:
            return Response(cached)

        from datetime import datetime as _dt
        def _parse(d):
            if not d:
                return None
            try:
                return _dt.strptime(d, '%Y-%m-%d').date()
            except Exception:
                return None
        d_from = _parse(d_from_raw); d_to = _parse(d_to_raw)

        results = []
        total = 0
        try:
            from reports.models import ReportVarianceIncident
            qs = ReportVarianceIncident.objects.all()
            qs = qs.order_by(ordering)
            if report_filter:
                qs = qs.filter(report=report_filter)
            if d_from:
                qs = qs.filter(created_at__date__gte=d_from)
            if d_to:
                qs = qs.filter(created_at__date__lte=d_to)
            total = qs.count()
            qs = qs[:overall_cap]
            start = (page - 1) * page_size
            end = start + page_size
            for inc in qs[start:end]:
                results.append({
                    'id': inc.id,
                    'created_at': inc.created_at.isoformat(),
                    'report': inc.report,
                    'percent': inc.percent,
                    'threshold_used': inc.threshold_used,
                    'global_min_applied': inc.global_min_applied,
                    'date_from': inc.date_from.isoformat() if inc.date_from else None,
                    'date_to': inc.date_to.isoformat() if inc.date_to else None,
                    'level': (inc.extra or {}).get('level') if inc.extra else None,
                    'extra': inc.extra or None,
                })
        except Exception:
            pass

        payload = {
            'results': results,
            'page': page,
            'page_size': page_size,
            'total': total,
            'ordering': ordering,
            'report': report_filter or None,
            'date_from': d_from_raw,
            'date_to': d_to_raw,
        }

        if export == 'csv':
            import csv, io
            sio = io.StringIO(); w = csv.writer(sio)
            w.writerow(['id','created_at','report','percent','threshold_used','global_min_applied','level','date_from','date_to'])
            for r in results:
                w.writerow([r['id'], r['created_at'], r['report'], r['percent'], r['threshold_used'], r['global_min_applied'], r.get('level'), r['date_from'], r['date_to']])
            data='\ufeff'+sio.getvalue()
            resp=HttpResponse(data, content_type='text/csv; charset=utf-8')
            resp['Content-Disposition']='attachment; filename="variance_incidents.csv"'
            return resp
        if export == 'xlsx':
            try:
                import openpyxl
                from io import BytesIO
                wb=openpyxl.Workbook(); ws=wb.active; assert ws is not None; ws.title='Incidents'
                headers=['id','created_at','report','percent','threshold_used','global_min_applied','level','date_from','date_to']
                if ws: ws.append(headers)
                for r in results:
                    if ws: ws.append([r['id'], r['created_at'], r['report'], r['percent'], r['threshold_used'], r['global_min_applied'], r.get('level'), r['date_from'], r['date_to']])
                bio=BytesIO(); wb.save(bio); bio.seek(0)
                resp=HttpResponse(bio.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                resp['Content-Disposition']='attachment; filename="variance_incidents.xlsx"'
                return resp
            except Exception:
                pass
        if not export:
            self._set(ck, payload)
        return Response(payload)

__all__ += ['ReportsVarianceIncidentsAPI']
