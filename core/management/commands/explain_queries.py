from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from importlib import import_module
from django.urls import resolve
from django.test import RequestFactory
import json

class Command(BaseCommand):
    help = "Execute EXPLAIN on a model queryset or a raw SQL / path. Usage: --model app.Model --sql 'SELECT ...' --path '/url/?q=1'"

    def add_arguments(self, parser):
        parser.add_argument('--model', help='Model path app_label.ModelName to run a simple all() EXPLAIN')
        parser.add_argument('--sql', help='Raw SQL to EXPLAIN (SELECT only)')
        parser.add_argument('--path', help='URL path to simulate a GET and capture ORM queries')
        parser.add_argument('--limit', type=int, default=1, help='Limit rows for model queryset')
        parser.add_argument('--format', choices=['text','json'], default='text')

    def handle(self, *args, **opts):
        model_path = opts.get('model')
        raw_sql = opts.get('sql')
        path = opts.get('path')
        out_format = opts['format']
        results = []

        if not any([model_path, raw_sql, path]):
            raise CommandError('Provide at least one of --model / --sql / --path')

        if model_path:
            try:
                app_label, model_name = model_path.split('.')
            except ValueError:
                raise CommandError('model should be app_label.ModelName')
            from django.apps import apps
            model = apps.get_model(app_label, model_name)
            limit = max(1, opts['limit'] or 1)
            qs = model.objects.all()[:limit]
            self.stdout.write(f"# EXPLAIN for queryset {model_path} (limit={limit})")
            sql = str(qs.query)
            results.append(self._explain_sql(sql))

        if raw_sql:
            if not raw_sql.strip().lower().startswith('select'):
                raise CommandError('Only SELECT statements are allowed for safety')
            self.stdout.write('# EXPLAIN for raw SQL')
            results.append(self._explain_sql(raw_sql))

        if path:
            rf = RequestFactory()
            request = rf.get(path)
            # Resolve without executing middlewares for speed
            resolver_match = resolve(path.split('?')[0])
            view_func = resolver_match.func
            with self._capture_queries() as captured:
                try:
                    response = view_func(request, *resolver_match.args, **resolver_match.kwargs)
                except Exception as e:
                    self.stderr.write(f'View execution error (still showing queries if any): {e}')
            self.stdout.write(f'# Captured {len(captured)} queries for path {path}')
            for q in captured:
                results.append(self._explain_sql(q['sql']))

        if out_format == 'json':
            self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for block in results:
                self.stdout.write(block)

    def _explain_sql(self, sql: str) -> str:
        with connection.cursor() as cur:
            cur.execute(f'EXPLAIN {sql}')
            rows = cur.fetchall()
            headers = [c[0] for c in cur.description]
        # Format simple table
        lines = [' | '.join(headers)]
        for r in rows:
            lines.append(' | '.join(str(x) for x in r))
        return '\n'.join(lines)

    from contextlib import contextmanager
    @contextmanager
    def _capture_queries(self):
        from django.db import connections
        conn = connection
        old = conn.queries_log
        conn.force_debug_cursor = True
        try:
            yield conn.queries_log
        finally:
            conn.force_debug_cursor = False
            conn.queries_log = old
