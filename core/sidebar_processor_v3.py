"""
Sidebar Context Processor v3 — 6 Parent Groups with Role-Based Visibility
==========================================================================
Builds the sidebar tree filtered by user permissions, resolves URLs,
and provides a flat search index for the global search bar.
"""

import json
import logging

from django.urls import reverse, NoReverseMatch

from core.sidebar_config_v3 import (
    get_parent_groups,
    get_sections_for_parent,
    CATEGORY_DAILY,
    CATEGORY_MASTER,
    CATEGORY_REPORTS,
)

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    CATEGORY_DAILY: 'عمليات يومية',
    CATEGORY_MASTER: 'تعريفات وإعدادات',
    CATEGORY_REPORTS: 'تقارير',
}

# Paths that should skip sidebar processing entirely
SKIP_PREFIXES = ('/store', '/home-services', '/api/', '/static/', '/media/')


def sidebar_menu_v3(request):
    """
    Context processor that returns:
      - sidebar_v3:             list of parent-group dicts (tree)
      - sidebar_search_items:   JSON string for client-side instant search
    """
    empty = {'sidebar_v3': [], 'sidebar_search_items': '[]'}

    # Fast exit for non-sidebar paths
    if any(request.path.startswith(p) for p in SKIP_PREFIXES):
        return empty

    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return empty

    user = request.user
    is_superuser = user.is_superuser

    # Collect modules the user may access
    user_modules = _get_user_modules(user)

    current_path = request.path
    sidebar_tree = []
    search_items = []

    for group in get_parent_groups():
        group_sections = []
        group_has_active = False

        for section in get_sections_for_parent(group['id']):
            module = section.get('module')
            if not _has_module_access(module, user_modules, is_superuser):
                continue

            categorized = {
                CATEGORY_DAILY: [],
                CATEGORY_MASTER: [],
                CATEGORY_REPORTS: [],
            }

            section_has_active = False

            for item in section.get('items', []):
                url_name = item.get('url', '')
                url_kwargs = item.get('url_kwargs')
                resolved_url = _safe_reverse(url_name, url_kwargs)
                if resolved_url is None:
                    continue

                is_active = (
                    current_path == resolved_url
                    or (resolved_url != '/' and current_path.startswith(resolved_url.rstrip('/') + '/'))
                )

                if is_active:
                    section_has_active = True
                    group_has_active = True

                built_item = {
                    'id': item['id'],
                    'label': str(item['label']),
                    'url': resolved_url,
                    'icon': item.get('icon', 'bi-circle'),
                    'active': is_active,
                    'badge_source': item.get('badge_source'),
                }

                cat = item.get('category', CATEGORY_DAILY)
                categorized.setdefault(cat, []).append(built_item)

                search_items.append({
                    'label': str(item['label']),
                    'url': resolved_url,
                    'icon': item.get('icon', ''),
                    'section': str(section['label']),
                    'group': str(group['label']),
                })

            # Build non-empty category groups
            categories = []
            for cat_key in [CATEGORY_DAILY, CATEGORY_MASTER, CATEGORY_REPORTS]:
                if categorized.get(cat_key):
                    categories.append({
                        'key': cat_key,
                        'label': CATEGORY_LABELS.get(cat_key, ''),
                        'items': categorized[cat_key],
                    })

            if categories:
                group_sections.append({
                    'id': section['id'],
                    'label': str(section['label']),
                    'icon': section.get('icon', 'bi-folder'),
                    'active': section_has_active,
                    'categories': categories,
                })

        if group_sections:
            sidebar_tree.append({
                'id': group['id'],
                'label': str(group['label']),
                'label_en': group.get('label_en', ''),
                'icon': group.get('icon', 'bi-folder'),
                'color': group.get('color', '#7c7bff'),
                'active': group_has_active,
                'sections': group_sections,
            })

    search_json = json.dumps(search_items, ensure_ascii=False)
    return {
        'sidebar_v3': sidebar_tree,
        'sidebar_search_items': search_json,
    }


# ─── Helpers ──────────────────────────────────────────────────

def _safe_reverse(url_name, kwargs=None):
    """Try to reverse a URL name; return None on failure."""
    if not url_name:
        return None
    try:
        return reverse(url_name, kwargs=kwargs)
    except NoReverseMatch:
        pass
    # Try without namespace prefix
    if ':' in url_name:
        try:
            return reverse(url_name.split(':')[-1], kwargs=kwargs)
        except NoReverseMatch:
            pass
    return None


def _has_module_access(module, user_modules, is_superuser):
    """Check if user can see items from this module."""
    if module is None or is_superuser:
        return True
    return module in user_modules


def _get_user_modules(user):
    """
    Return a set of module/app names the user has access to.
    Integrates with Django's built-in permission system.
    """
    if user.is_superuser:
        return set()  # superuser sees everything (handled by _has_module_access)

    modules = set()

    try:
        from django.apps import apps
        all_app_labels = {c.label for c in apps.get_app_configs()}

        # Derive accessible app labels from user permissions
        user_perms = set()
        if hasattr(user, 'get_all_permissions'):
            user_perms = user.get_all_permissions()

        for perm in user_perms:
            app_label = perm.split('.')[0] if '.' in perm else perm
            if app_label in all_app_labels:
                modules.add(app_label)

        # Also check if user has a profile with explicit modules
        if hasattr(user, 'profile') and hasattr(user.profile, 'allowed_modules'):
            allowed = user.profile.allowed_modules
            if isinstance(allowed, (list, set)):
                modules.update(allowed)
    except Exception as exc:
        logger.debug("Error getting user modules: %s", exc)

    return modules
