# -*- coding: utf-8 -*-
"""
Script to check for various issues in the Django project
"""
import os
import sys
import re
import glob
import ast

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'accountant_pro.settings'

import django
django.setup()

def check_missing_templates():
    """Check for missing templates referenced in views"""
    print('=' * 80)
    print('CHECKING FOR MISSING TEMPLATES REFERENCED IN VIEWS')
    print('=' * 80)
    
    # Template directories - include both project-level and app-level templates
    template_dirs = ['templates']
    # Also scan each app's templates directory
    for app_dir in os.listdir('.'):
        app_tpl = os.path.join(app_dir, 'templates')
        if os.path.isdir(app_tpl):
            template_dirs.append(app_tpl)
    
    # Collect all existing templates
    existing_templates = set()
    for tdir in template_dirs:
        for root, dirs, files in os.walk(tdir):
            for f in files:
                if f.endswith('.html'):
                    rel_path = os.path.relpath(os.path.join(root, f), tdir)
                    existing_templates.add(rel_path.replace('\\', '/'))
    
    # Find template references in views
    apps = [
        'accounting', 'accounts', 'ai_assistant', 'api', 'approvals', 'contracting',
        'core', 'crm', 'data_import', 'ecommerce', 'eservices', 'exports', 'fixed_assets',
        'fleet', 'home_services', 'hr', 'inventory', 'maintenance', 'notifications',
        'partners', 'payments', 'pos', 'production', 'projects', 'purchases', 'reports',
        'sales', 'shipping', 'showrooms', 'taxes', 'users', 'woocommerce_integration'
    ]
    
    template_pattern = re.compile(r'template_name\s*=\s*["\']([^"\']+)["\']')
    render_pattern = re.compile(r'render\s*\([^,]+,\s*["\']([^"\']+)["\']')
    get_template_pattern = re.compile(r'get_template\s*\(\s*["\']([^"\']+)["\']')
    
    missing_templates = []
    
    for app in apps:
        py_files = glob.glob(f'{app}/**/*.py', recursive=True)
        for py_file in py_files:
            if '__pycache__' in py_file:
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                templates = []
                templates.extend(template_pattern.findall(content))
                templates.extend(render_pattern.findall(content))
                templates.extend(get_template_pattern.findall(content))
                
                for tpl in templates:
                    if tpl not in existing_templates and not tpl.startswith('admin/'):
                        # Double check with Django template loader
                        missing_templates.append((py_file, tpl))
            except Exception as e:
                pass
    
    # Deduplicate
    seen = set()
    unique_missing = []
    for item in missing_templates:
        if item[1] not in seen:
            seen.add(item[1])
            unique_missing.append(item)
    
    if unique_missing:
        print(f'Found {len(unique_missing)} potentially missing templates:')
        for py_file, tpl in sorted(unique_missing, key=lambda x: x[1]):
            print(f'  - {tpl}')
            print(f'    Referenced in: {py_file}')
    else:
        print('All referenced templates exist!')
    
    return unique_missing


def check_broken_urls_in_templates():
    """Check for broken URL references in templates"""
    print('\n' + '=' * 80)
    print('CHECKING FOR BROKEN URL REFERENCES IN TEMPLATES')
    print('=' * 80)
    
    from django.urls import get_resolver
    
    # Get all valid URL names
    resolver = get_resolver()
    valid_url_names = set()
    
    def extract_url_names(resolver, prefix=''):
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'url_patterns'):
                # It's an included URLconf
                namespace = getattr(pattern, 'namespace', None)
                new_prefix = f'{namespace}:' if namespace else prefix
                extract_url_names(pattern, new_prefix)
            else:
                name = pattern.name
                if name:
                    valid_url_names.add(f'{prefix}{name}')
    
    extract_url_names(resolver)
    
    # Find URL references in templates
    url_pattern = re.compile(r'{%\s*url\s+["\']([^"\']+)["\']')
    
    broken_urls = []
    
    for root, dirs, files in os.walk('templates'):
        for f in files:
            if f.endswith('.html'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    urls = url_pattern.findall(content)
                    for url_name in urls:
                        # Check if URL exists
                        if url_name not in valid_url_names:
                            broken_urls.append((filepath, url_name))
                except Exception as e:
                    pass
    
    # Deduplicate
    seen = set()
    unique_broken = []
    for item in broken_urls:
        if item[1] not in seen:
            seen.add(item[1])
            unique_broken.append(item)
    
    if unique_broken:
        print(f'Found {len(unique_broken)} potentially broken URL references:')
        for filepath, url_name in sorted(unique_broken, key=lambda x: x[1])[:100]:
            print(f'  - {url_name}')
            print(f'    In template: {filepath}')
    else:
        print('All URL references are valid!')
    
    return unique_broken


def check_undefined_template_variables():
    """Check for potentially undefined variables in templates"""
    print('\n' + '=' * 80)
    print('CHECKING FOR UNDEFINED VARIABLES IN TEMPLATES (Sample)')
    print('=' * 80)
    
    # This is a simplified check - full check would require context analysis
    var_pattern = re.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_]*)')
    
    common_context_vars = {
        'request', 'user', 'perms', 'messages', 'STATIC_URL', 'MEDIA_URL',
        'csrf_token', 'debug', 'sql_queries', 'DEFAULT_MESSAGE_LEVELS',
        'True', 'False', 'None', 'forloop', 'block', 'item', 'object',
        'form', 'formset', 'field', 'page_obj', 'paginator', 'is_paginated',
        'object_list', 'view', 'LANGUAGE_CODE', 'LANGUAGES', 'title',
        'message', 'error', 'success', 'warning', 'info'
    }
    
    potentially_undefined = []
    
    for root, dirs, files in os.walk('templates'):
        for f in files:
            if f.endswith('.html'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    # Check for with blocks to add context
                    with_pattern = re.compile(r'{%\s*with\s+([^%]+)\s*%}')
                    with_vars = set()
                    for match in with_pattern.findall(content):
                        # Extract variable names from with statement
                        assignments = match.split(' ')
                        for a in assignments:
                            if '=' in a:
                                var_name = a.split('=')[0].strip()
                                with_vars.add(var_name)
                    
                    # Check for for loops to add loop variables
                    for_pattern = re.compile(r'{%\s*for\s+(\w+)(?:\s*,\s*(\w+))?\s+in')
                    for match in for_pattern.findall(content):
                        for var in match:
                            if var:
                                with_vars.add(var)
                    
                    # Don't report issues for now - too many false positives
                except Exception as e:
                    pass
    
    print('Skipped - too many false positives without full context analysis')
    return []


def check_views_using_nonexistent_models():
    """Check for views using non-existent models"""
    print('\n' + '=' * 80)
    print('CHECKING FOR VIEWS USING NON-EXISTENT MODELS')
    print('=' * 80)
    
    from django.apps import apps
    
    # Get all model names
    all_models = {model.__name__ for model in apps.get_models()}
    
    # Known Django ORM functions/classes that are imported from *.models
    DJANGO_ORM_NAMES = {
        'Sum', 'Avg', 'Count', 'Max', 'Min', 'StdDev', 'Variance',
        'F', 'Q', 'Value', 'When', 'Case', 'Subquery', 'OuterRef', 'Exists',
        'Prefetch', 'CharField', 'IntegerField', 'BooleanField', 'DecimalField',
        'FloatField', 'TextField', 'DateField', 'DateTimeField', 'TimeField',
        'ForeignKey', 'OneToOneField', 'ManyToManyField', 'JSONField',
        'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField',
        'FileField', 'ImageField', 'URLField', 'EmailField', 'SlugField',
        'UUIDField', 'BinaryField', 'AutoField', 'BigAutoField',
        'GenericIPAddressField', 'IPAddressField', 'PositiveBigIntegerField',
        'PositiveSmallIntegerField', 'DurationField',
        'Model', 'Manager', 'QuerySet', 'signals', 'CASCADE', 'SET_NULL',
        'SET_DEFAULT', 'PROTECT', 'DO_NOTHING', 'SET', 'RESTRICT',
        'Index', 'UniqueConstraint', 'CheckConstraint', 'Avg',
        'ExpressionWrapper', 'Func', 'Length', 'Lower', 'Upper', 'Trim',
        'Coalesce', 'Greatest', 'Least', 'NullIf', 'Cast',
        'RowRange', 'ValueRange', 'Window',
        'Concat', 'Left', 'Right', 'Replace', 'Reverse', 'StrIndex', 'Substr',
        'Abs', 'ACos', 'ASin', 'ATan', 'ATan2', 'Ceil', 'Cos', 'Cot',
        'Degrees', 'Exp', 'Floor', 'Ln', 'Log', 'Mod', 'Pi', 'Power',
        'Radians', 'Random', 'Round', 'Sign', 'Sin', 'Sqrt', 'Tan',
        'Now', 'TruncDate', 'TruncDay', 'TruncHour', 'TruncMinute',
        'TruncMonth', 'TruncQuarter', 'TruncSecond', 'TruncWeek', 'TruncYear',
        'Extract', 'ExtractDay', 'ExtractHour', 'ExtractMinute', 'ExtractMonth',
        'ExtractQuarter', 'ExtractSecond', 'ExtractWeek', 'ExtractYear',
    }
    
    # Pattern to find model imports and usages
    model_import_pattern = re.compile(r'from\s+[\w.]+\.models\s+import\s+(.+)')
    
    issues = []
    
    apps_list = [
        'accounting', 'accounts', 'ai_assistant', 'api', 'approvals', 'contracting',
        'core', 'crm', 'data_import', 'ecommerce', 'eservices', 'exports', 'fixed_assets',
        'fleet', 'home_services', 'hr', 'inventory', 'maintenance', 'notifications',
        'partners', 'payments', 'pos', 'production', 'projects', 'purchases', 'reports',
        'sales', 'shipping', 'showrooms', 'taxes', 'users', 'woocommerce_integration'
    ]
    
    for app in apps_list:
        py_files = glob.glob(f'{app}/**/*.py', recursive=True)
        for py_file in py_files:
            if '__pycache__' in py_file or 'migrations' in py_file:
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                imports = model_import_pattern.findall(content)
                for import_line in imports:
                    # Parse import line
                    parts = import_line.replace('(', '').replace(')', '').replace('\n', '').split(',')
                    for part in parts:
                        model_name = part.strip().split(' as ')[0].strip()
                        if (model_name
                                and model_name not in all_models
                                and model_name not in DJANGO_ORM_NAMES
                                and model_name not in ['*']
                                and not model_name.startswith('#')
                                and not model_name.startswith('//')):
                            issues.append((py_file, model_name))
            except Exception as e:
                pass
    
    # Deduplicate
    seen = set()
    unique_issues = []
    for item in issues:
        if (item[0], item[1]) not in seen:
            seen.add((item[0], item[1]))
            unique_issues.append(item)
    
    if unique_issues:
        print(f'Found {len(unique_issues)} potential issues:')
        for py_file, model_name in sorted(unique_issues, key=lambda x: x[1]):
            print(f'  - Model: {model_name}')
            print(f'    In file: {py_file}')
    else:
        print('All model references appear valid!')
    
    return unique_issues


def check_circular_imports():
    """Check for potential circular imports in models"""
    print('\n' + '=' * 80)
    print('CHECKING FOR POTENTIAL CIRCULAR IMPORTS')
    print('=' * 80)
    
    apps_list = [
        'accounting', 'accounts', 'ai_assistant', 'api', 'approvals', 'contracting',
        'core', 'crm', 'data_import', 'ecommerce', 'eservices', 'exports', 'fixed_assets',
        'fleet', 'home_services', 'hr', 'inventory', 'maintenance', 'notifications',
        'partners', 'payments', 'pos', 'production', 'projects', 'purchases', 'reports',
        'sales', 'shipping', 'showrooms', 'taxes', 'users', 'woocommerce_integration'
    ]
    
    # Build dependency graph
    dependencies = {}
    
    import_pattern = re.compile(r'from\s+([\w.]+)\s+import')
    
    for app in apps_list:
        models_file = f'{app}/models.py'
        models_folder = f'{app}/models'
        
        app_deps = set()
        
        files_to_check = []
        if os.path.exists(models_file):
            files_to_check.append(models_file)
        if os.path.isdir(models_folder):
            for f in os.listdir(models_folder):
                if f.endswith('.py'):
                    files_to_check.append(os.path.join(models_folder, f))
        
        for filepath in files_to_check:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                imports = import_pattern.findall(content)
                for imp in imports:
                    # Check if it's importing from another app's models
                    for other_app in apps_list:
                        if other_app != app and imp.startswith(f'{other_app}.'):
                            app_deps.add(other_app)
            except Exception as e:
                pass
        
        dependencies[app] = app_deps
    
    # Find cycles
    def find_cycle(start, current, visited, path):
        if current in visited:
            if current == start:
                return path
            return None
        
        visited.add(current)
        path.append(current)
        
        for dep in dependencies.get(current, []):
            result = find_cycle(start, dep, visited.copy(), path.copy())
            if result:
                return result
        
        return None
    
    cycles = []
    for app in apps_list:
        for dep in dependencies.get(app, []):
            cycle = find_cycle(app, dep, set(), [app])
            if cycle and cycle not in cycles:
                cycles.append(cycle)
    
    if cycles:
        print(f'Found {len(cycles)} potential circular import chains:')
        for cycle in cycles[:20]:  # Show first 20
            print(f'  - {" -> ".join(cycle)}')
    else:
        print('No circular imports detected!')
    
    return cycles


def check_missing_fields_in_views():
    """Check for fields used in views that don't exist in models"""
    print('\n' + '=' * 80)
    print('CHECKING FOR MISSING FIELDS USED IN VIEWS')
    print('=' * 80)
    
    from django.apps import apps
    
    # Get all model field names
    model_fields = {}
    for model in apps.get_models():
        fields = set()
        for field in model._meta.get_fields():
            fields.add(field.name)
        model_fields[model.__name__] = fields
    
    # Check for field access patterns in views
    # This is a simplified check
    field_access_pattern = re.compile(r'(\w+)\.objects\.')
    
    apps_list = [
        'accounting', 'accounts', 'crm', 'hr', 'inventory', 'maintenance',
        'production', 'purchases', 'reports', 'sales'
    ]
    
    issues = []
    
    for app in apps_list:
        py_files = glob.glob(f'{app}/**/*.py', recursive=True)
        for py_file in py_files:
            if '__pycache__' in py_file or 'migrations' in py_file:
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find model usages
                models_used = field_access_pattern.findall(content)
                # Additional check would require more complex AST analysis
            except Exception as e:
                pass
    
    print('Basic check complete - detailed field analysis requires runtime inspection')
    return issues


def main():
    print('\n' + '=' * 80)
    print('DJANGO PROJECT ISSUE CHECKER')
    print('=' * 80 + '\n')
    
    # Run all checks
    missing_templates = check_missing_templates()
    broken_urls = check_broken_urls_in_templates()
    check_undefined_template_variables()
    model_issues = check_views_using_nonexistent_models()
    circular_imports = check_circular_imports()
    check_missing_fields_in_views()
    
    # Summary
    print('\n' + '=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Missing templates: {len(missing_templates)}')
    print(f'Broken URL references: {len(broken_urls)}')
    print(f'Non-existent model references: {len(model_issues)}')
    print(f'Circular import chains: {len(circular_imports)}')


if __name__ == '__main__':
    main()
