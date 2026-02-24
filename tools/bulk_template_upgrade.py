#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أداة تحديث القوالب التلقائية بشكل جماعي
تحول القوالب من الشكل البدائي Auto-generated إلى شكل احترافي
"""

import os
import re
from pathlib import Path
from datetime import datetime

# مسار مجلد القوالب
APP_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = APP_DIR / 'templates'
BACKUP_DIR = APP_DIR / 'templates_backup'

# القالب الأساسي للقوائم المحسنة
ENHANCED_LIST_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}TITLE_PLACEHOLDER - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .page-header {
    margin-bottom: 1.5rem;
  }
  .filter-card {
    border-radius: 12px;
    margin-bottom: 1.5rem;
  }
  .data-card {
    border-radius: 12px;
    overflow: hidden;
  }
  .data-card .card-header {
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }
  .table-custom th {
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
    background: #f8f9fa;
  }
  .table-custom td {
    vertical-align: middle;
    font-size: 0.875rem;
  }
  .empty-state {
    padding: 4rem 2rem;
    text-align: center;
  }
  .empty-state i {
    font-size: 4rem;
    color: #dee2e6;
  }
  .status-badge {
    font-size: 0.75rem;
    padding: 0.35em 0.65em;
  }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Header -->
  <div class="d-flex flex-wrap gap-3 justify-content-between align-items-center mb-4">
    <div>
      <h1 class="h4 fw-bold mb-1">
        <i class="bi ICON_PLACEHOLDER text-primary me-2"></i>
        TITLE_PLACEHOLDER
      </h1>
      <p class="text-muted small mb-0">SUBTITLE_PLACEHOLDER</p>
    </div>
    <div class="d-flex gap-2">
      {% block header_actions %}
      {% endblock %}
    </div>
  </div>

  <!-- Filter Card -->
  <div class="card filter-card">
    <div class="card-body py-3">
      <form method="get" class="row g-2 align-items-end">
        <div class="col-md-4">
          <label class="form-label small mb-1">{% trans 'بحث' %}</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text"><i class="bi bi-search"></i></span>
            <input type="text" class="form-control" name="search" value="{{ search }}" placeholder="{% trans 'بحث...' %}">
          </div>
        </div>
        {% block filter_fields %}{% endblock %}
        <div class="col-md-2 d-flex gap-2">
          <button type="submit" class="btn btn-primary btn-sm flex-grow-1">
            <i class="bi bi-funnel"></i> {% trans 'بحث' %}
          </button>
          <a href="?" class="btn btn-outline-secondary btn-sm">
            <i class="bi bi-x-lg"></i>
          </a>
        </div>
      </form>
    </div>
  </div>

  <!-- Data Card -->
  <div class="card data-card">
    <div class="card-header d-flex justify-content-between align-items-center py-3">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-list-ul text-primary"></i>
        <span class="fw-semibold">{% trans 'القائمة' %}</span>
        {% if object_list %}
        <span class="badge bg-primary">{{ object_list|length }}</span>
        {% endif %}
      </div>
    </div>
    <div class="card-body p-0">
      {% if object_list or page_obj %}
      <div class="table-responsive">
        <table class="table table-hover table-custom mb-0">
          <thead>
            <tr>
              {% block table_headers %}
              <th>#</th>
              <th>{% trans 'العنصر' %}</th>
              <th class="text-end">{% trans 'إجراءات' %}</th>
              {% endblock %}
            </tr>
          </thead>
          <tbody>
            {% block table_body %}
            {% for obj in object_list %}
            <tr>
              <td>{{ forloop.counter }}</td>
              <td>{{ obj }}</td>
              <td class="text-end">
                <div class="btn-group btn-group-sm">
                  <a href="#" class="btn btn-outline-primary" title="{% trans 'عرض' %}">
                    <i class="bi bi-eye"></i>
                  </a>
                </div>
              </td>
            </tr>
            {% empty %}
            <tr>
              <td colspan="3" class="text-center text-muted py-4">{% trans 'لا توجد بيانات' %}</td>
            </tr>
            {% endfor %}
            {% endblock %}
          </tbody>
        </table>
      </div>
      
      {% if page_obj %}
      <div class="card-footer bg-white border-top">
        <nav aria-label="Pagination">
          <ul class="pagination mb-0 justify-content-center">
            {% if page_obj.has_previous %}
            <li class="page-item">
              <a class="page-link" href="?page={{ page_obj.previous_page_number }}">
                <i class="bi bi-chevron-right"></i>
              </a>
            </li>
            {% endif %}
            <li class="page-item disabled">
              <span class="page-link">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
            </li>
            {% if page_obj.has_next %}
            <li class="page-item">
              <a class="page-link" href="?page={{ page_obj.next_page_number }}">
                <i class="bi bi-chevron-left"></i>
              </a>
            </li>
            {% endif %}
          </ul>
        </nav>
      </div>
      {% endif %}
      
      {% else %}
      <div class="empty-state">
        <i class="bi bi-inbox"></i>
        <h5 class="text-muted mt-3">{% trans 'لا توجد بيانات' %}</h5>
        <p class="text-muted small mb-3">{% trans 'لم يتم العثور على أي عناصر' %}</p>
        {% block empty_actions %}{% endblock %}
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
'''

# القالب الأساسي للنماذج المحسنة
ENHANCED_FORM_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}TITLE_PLACEHOLDER - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .form-card {
    border-radius: 12px;
    overflow: hidden;
  }
  .form-card .card-header {
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }
  .required-field::after {
    content: " *";
    color: #dc3545;
  }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Header -->
  <div class="d-flex flex-wrap gap-3 justify-content-between align-items-center mb-4">
    <div>
      <h1 class="h4 fw-bold mb-1">
        <i class="bi ICON_PLACEHOLDER text-primary me-2"></i>
        TITLE_PLACEHOLDER
      </h1>
      <p class="text-muted small mb-0">SUBTITLE_PLACEHOLDER</p>
    </div>
    <div class="d-flex gap-2">
      <a href="javascript:history.back()" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
    </div>
  </div>

  <!-- Form Card -->
  <div class="card form-card">
    <div class="card-header">
      <i class="bi bi-ui-checks text-primary me-2"></i>
      <span class="fw-semibold">{% trans 'تفاصيل النموذج' %}</span>
    </div>
    <div class="card-body">
      <form method="post" enctype="multipart/form-data">
        {% csrf_token %}
        
        {% if form.non_field_errors %}
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
          {{ form.non_field_errors }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endif %}

        <div class="row g-3">
          {% for field in form %}
          <div class="col-md-6">
            <label for="{{ field.id_for_label }}" class="form-label{% if field.field.required %} required-field{% endif %}">
              {{ field.label }}
            </label>
            {{ field }}
            {% if field.help_text %}
            <small class="form-text text-muted">{{ field.help_text }}</small>
            {% endif %}
            {% if field.errors %}
            <div class="invalid-feedback d-block">{{ field.errors }}</div>
            {% endif %}
          </div>
          {% endfor %}
        </div>

        <div class="mt-4 pt-3 border-top d-flex gap-2">
          <button type="submit" class="btn btn-primary">
            <i class="bi bi-check-lg me-1"></i> {% trans 'حفظ' %}
          </button>
          <a href="javascript:history.back()" class="btn btn-outline-secondary">
            <i class="bi bi-x-lg me-1"></i> {% trans 'إلغاء' %}
          </a>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
'''

# القالب الأساسي للتفاصيل المحسنة
ENHANCED_DETAIL_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}TITLE_PLACEHOLDER - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .detail-card {
    border-radius: 12px;
    overflow: hidden;
  }
  .detail-card .card-header {
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }
  .detail-item {
    display: flex;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f1f3f5;
  }
  .detail-item:last-child {
    border-bottom: none;
  }
  .detail-label {
    flex: 0 0 200px;
    font-weight: 600;
    color: #6c757d;
  }
  .detail-value {
    flex: 1;
    color: #212529;
  }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Header -->
  <div class="d-flex flex-wrap gap-3 justify-content-between align-items-center mb-4">
    <div>
      <h1 class="h4 fw-bold mb-1">
        <i class="bi ICON_PLACEHOLDER text-primary me-2"></i>
        TITLE_PLACEHOLDER
      </h1>
      <p class="text-muted small mb-0">SUBTITLE_PLACEHOLDER</p>
    </div>
    <div class="d-flex gap-2">
      {% block header_actions %}
      <a href="javascript:history.back()" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
      {% endblock %}
    </div>
  </div>

  <!-- Detail Card -->
  <div class="card detail-card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-info-circle text-primary"></i>
        <span class="fw-semibold">{% trans 'معلومات أساسية' %}</span>
      </div>
    </div>
    <div class="card-body">
      {% if object %}
      <div class="detail-item">
        <div class="detail-label">{% trans 'العنصر' %}</div>
        <div class="detail-value">{{ object }}</div>
      </div>
      {% block detail_content %}{% endblock %}
      {% else %}
      <div class="text-center py-5">
        <i class="bi bi-exclamation-circle display-4 text-muted"></i>
        <h5 class="text-muted mt-3">{% trans 'لا توجد بيانات' %}</h5>
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
'''

# تعيين الأيقونات حسب الوحدة
MODULE_ICONS = {
    'purchases': 'bi-bag-check',
    'sales': 'bi-cart-check',
    'inventory': 'bi-box-seam',
    'accounting': 'bi-calculator',
    'hr': 'bi-people',
    'crm': 'bi-person-lines-fill',
    'production': 'bi-gear-wide-connected',
    'fleet': 'bi-truck',
    'maintenance': 'bi-tools',
    'projects': 'bi-kanban',
    'pos': 'bi-shop',
    'ecommerce': 'bi-globe',
    'reports': 'bi-bar-chart-line',
    'partners': 'bi-building',
    'users': 'bi-person-circle',
    'default': 'bi-grid',
}

# تعيين العناوين حسب نوع القالب
TEMPLATE_TITLES = {
    'list': 'القائمة',
    'form': 'النموذج',
    'detail': 'التفاصيل',
    'create': 'إضافة جديد',
    'edit': 'تعديل',
}


def get_module_from_path(template_path):
    """استخراج اسم الوحدة من مسار القالب"""
    parts = str(template_path).split(os.sep)
    if 'templates' in parts:
        idx = parts.index('templates')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return 'default'


def get_icon_for_module(module):
    """الحصول على الأيقونة المناسبة للوحدة"""
    return MODULE_ICONS.get(module, MODULE_ICONS['default'])


def detect_template_type(filename, content):
    """تحديد نوع القالب"""
    name_lower = filename.lower()
    if 'list' in name_lower or 'index' in name_lower:
        return 'list'
    elif 'form' in name_lower or 'create' in name_lower or 'edit' in name_lower:
        return 'form'
    elif 'detail' in name_lower or 'view' in name_lower:
        return 'detail'
    elif 'object_list' in content or 'page_obj' in content:
        return 'list'
    elif 'method="post"' in content.lower():
        return 'form'
    return 'list'  # افتراضي


def generate_title_from_path(template_path):
    """توليد عنوان من مسار القالب"""
    filename = Path(template_path).stem
    # تحويل snake_case إلى عنوان قابل للقراءة
    title = filename.replace('_', ' ').replace('-', ' ').title()
    return title


def upgrade_template(template_path, dry_run=False):
    """ترقية قالب واحد"""
    try:
        content = template_path.read_text(encoding='utf-8')
        
        # التحقق من أنه قالب تلقائي
        if 'Auto-generated' not in content and 'تم توليده تلقائيًا' not in content:
            return False, "ليس قالب تلقائي"
        
        # تحديد النوع والوحدة
        template_type = detect_template_type(template_path.name, content)
        module = get_module_from_path(template_path)
        icon = get_icon_for_module(module)
        title = generate_title_from_path(template_path)
        
        # اختيار القالب المناسب
        if template_type == 'list':
            new_content = ENHANCED_LIST_TEMPLATE
        elif template_type == 'form':
            new_content = ENHANCED_FORM_TEMPLATE
        else:
            new_content = ENHANCED_DETAIL_TEMPLATE
        
        # استبدال العناصر النائبة
        new_content = new_content.replace('TITLE_PLACEHOLDER', title)
        new_content = new_content.replace('ICON_PLACEHOLDER', icon)
        new_content = new_content.replace('SUBTITLE_PLACEHOLDER', f'إدارة {title}')
        
        if not dry_run:
            # إنشاء نسخة احتياطية
            backup_path = BACKUP_DIR / template_path.relative_to(TEMPLATES_DIR)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(content, encoding='utf-8')
            
            # كتابة القالب الجديد
            template_path.write_text(new_content, encoding='utf-8')
        
        return True, f"تم ترقية {template_type}"
    except Exception as e:
        return False, str(e)


def find_auto_generated_templates():
    """البحث عن جميع القوالب التلقائية"""
    templates = []
    for html_file in TEMPLATES_DIR.rglob('*.html'):
        try:
            content = html_file.read_text(encoding='utf-8')
            if 'Auto-generated' in content or 'تم توليده تلقائيًا' in content:
                templates.append(html_file)
        except:
            pass
    return templates


def upgrade_all(dry_run=True, limit=None):
    """ترقية جميع القوالب"""
    templates = find_auto_generated_templates()
    
    if limit:
        templates = templates[:limit]
    
    print(f"\n{'='*60}")
    print(f"  ترقية القوالب التلقائية")
    print(f"  الوضع: {'معاينة فقط' if dry_run else 'تنفيذ فعلي'}")
    print(f"  عدد القوالب: {len(templates)}")
    print(f"{'='*60}\n")
    
    success = 0
    failed = 0
    
    for t in templates:
        rel_path = t.relative_to(TEMPLATES_DIR)
        result, msg = upgrade_template(t, dry_run=dry_run)
        status = "✓" if result else "✗"
        print(f"  {status} {rel_path}: {msg}")
        if result:
            success += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"  النتائج: {success} نجاح, {failed} فشل")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--apply':
        # تطبيق فعلي
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        upgrade_all(dry_run=False, limit=limit)
    else:
        # معاينة فقط
        print("استخدام: python bulk_template_upgrade.py --apply [limit]")
        print("بدون --apply سيتم عرض معاينة فقط")
        upgrade_all(dry_run=True, limit=10)
