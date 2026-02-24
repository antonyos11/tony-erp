#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أداة ترقية القوالب التلقائية (Auto-generated) إلى قوالب احترافية
تحافظ على نفس الوظائف لكن بتصميم أفضل
"""

from pathlib import Path
import re

# مسار مجلد القوالب
TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

# قالب List احترافي عام
LIST_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}{{ page_title|default:"القائمة" }} - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .page-header {{
    margin-bottom: 1.5rem;
  }}
  .page-header h1 {{
    font-weight: 700;
    font-size: 1.5rem;
  }}
  .stats-row {{
    margin-bottom: 1.5rem;
  }}
  .stat-card {{
    border-radius: 12px;
    padding: 1rem;
    background: white;
    border: 1px solid #e9ecef;
    transition: all 0.3s ease;
  }}
  .stat-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  }}
  .stat-icon {{
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
  }}
  .stat-value {{
    font-size: 1.5rem;
    font-weight: 700;
  }}
  .filter-card {{
    border-radius: 12px;
    margin-bottom: 1.5rem;
  }}
  .data-card {{
    border-radius: 12px;
    overflow: hidden;
  }}
  .data-card .card-header {{
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }}
  .table-custom th {{
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
    background: #f8f9fa;
  }}
  .table-custom td {{
    vertical-align: middle;
    font-size: 0.875rem;
  }}
  .empty-state {{
    padding: 4rem 2rem;
    text-align: center;
  }}
  .empty-state i {{
    font-size: 4rem;
    color: #dee2e6;
  }}
  .action-btn {{
    width: 32px;
    height: 32px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Page Header -->
  <div class="page-header d-flex flex-wrap gap-3 justify-content-between align-items-center">
    <div>
      <h1 class="mb-1">
        <i class="bi {{ page_icon|default:'bi-list-ul' }} text-primary me-2"></i>
        {{ page_title|default:"القائمة" }}
      </h1>
      {% if page_subtitle %}
      <p class="text-muted small mb-0">{{ page_subtitle }}</p>
      {% endif %}
    </div>
    <div class="d-flex gap-2">
      {% if create_url %}
      <a href="{% url create_url %}" class="btn btn-success">
        <i class="bi bi-plus-circle me-1"></i> {{ create_text|default:"إضافة جديد" }}
      </a>
      {% endif %}
      {% block header_actions %}{% endblock %}
    </div>
  </div>

  <!-- Stats Row (Optional) -->
  {% if stats %}
  <div class="row g-3 stats-row">
    {% for stat in stats %}
    <div class="col-6 col-md-3">
      <div class="stat-card">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon bg-{{ stat.color|default:'primary' }} bg-opacity-10 text-{{ stat.color|default:'primary' }}">
            <i class="bi bi-{{ stat.icon|default:'circle' }}"></i>
          </div>
          <div>
            <div class="stat-value text-{{ stat.color|default:'primary' }}">{{ stat.value|default:0 }}</div>
            <div class="small text-muted">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Filter Card -->
  {% if show_filter %}
  <div class="card filter-card">
    <div class="card-body py-3">
      <form method="get" class="row g-2 align-items-end">
        {% block filter_fields %}
        <div class="col-md-4">
          <label class="form-label small mb-1">{% trans 'بحث' %}</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text"><i class="bi bi-search"></i></span>
            <input type="text" class="form-control" name="search" value="{{ search }}" placeholder="{% trans 'بحث...' %}">
          </div>
        </div>
        {% endblock %}
        <div class="col-md-2 d-flex gap-2">
          <button type="submit" class="btn btn-primary btn-sm flex-grow-1">
            <i class="bi bi-funnel"></i> {% trans 'تصفية' %}
          </button>
          <a href="?" class="btn btn-outline-secondary btn-sm">
            <i class="bi bi-x-lg"></i>
          </a>
        </div>
      </form>
    </div>
  </div>
  {% endif %}

  <!-- Data Card -->
  <div class="card data-card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-list-ul text-primary"></i>
        <span class="fw-semibold">{% block table_title %}القائمة{% endblock %}</span>
        {% if object_list %}
        <span class="badge bg-primary">{{ object_list|length }}</span>
        {% endif %}
      </div>
      {% block table_actions %}{% endblock %}
    </div>
    <div class="card-body p-0">
      {% if object_list %}
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
                {% if detail_url_name %}
                <a href="{% url detail_url_name obj.pk %}" class="btn btn-sm btn-outline-primary action-btn" title="{% trans 'عرض' %}">
                  <i class="bi bi-eye"></i>
                </a>
                {% endif %}
              </td>
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
        <p class="text-muted small mb-3">{{ empty_message|default:"لم يتم العثور على أي عناصر" }}</p>
        {% if create_url %}
        <a href="{% url create_url %}" class="btn btn-success">
          <i class="bi bi-plus-circle me-1"></i> {{ create_text|default:"إضافة جديد" }}
        </a>
        {% endif %}
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
'''

# قالب Form احترافي عام
FORM_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}{{ page_title|default:"نموذج" }} - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .form-card {{
    border-radius: 12px;
    overflow: hidden;
  }}
  .form-card .card-header {{
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }}
  .form-section {{
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #e9ecef;
  }}
  .form-section:last-child {{
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }}
  .form-section-title {{
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 1rem;
    color: #495057;
  }}
  .required-field::after {{
    content: " *";
    color: #dc3545;
  }}
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Page Header -->
  <div class="d-flex flex-wrap gap-3 justify-content-between align-items-center mb-4">
    <div>
      <h1 class="h4 fw-bold mb-1">
        <i class="bi {{ page_icon|default:'bi-pencil-square' }} text-primary me-2"></i>
        {{ page_title|default:"نموذج" }}
      </h1>
      {% if page_subtitle %}
      <p class="text-muted small mb-0">{{ page_subtitle }}</p>
      {% endif %}
    </div>
    <div class="d-flex gap-2">
      {% if back_url %}
      <a href="{% url back_url %}" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
      {% else %}
      <a href="javascript:history.back()" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
      {% endif %}
    </div>
  </div>

  <!-- Form Card -->
  <div class="card form-card">
    <div class="card-header">
      <i class="bi bi-ui-checks text-primary me-2"></i>
      <span class="fw-semibold">{% block form_title %}تفاصيل النموذج{% endblock %}</span>
    </div>
    <div class="card-body">
      <form method="post" enctype="multipart/form-data" id="mainForm">
        {% csrf_token %}
        
        {% if form.non_field_errors %}
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
          {{ form.non_field_errors }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endif %}

        {% block form_content %}
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
        {% endblock %}

        <div class="mt-4 pt-3 border-top d-flex gap-2">
          <button type="submit" class="btn btn-primary">
            <i class="bi bi-check-lg me-1"></i> {% trans 'حفظ' %}
          </button>
          {% if back_url %}
          <a href="{% url back_url %}" class="btn btn-outline-secondary">
            <i class="bi bi-x-lg me-1"></i> {% trans 'إلغاء' %}
          </a>
          {% else %}
          <a href="javascript:history.back()" class="btn btn-outline-secondary">
            <i class="bi bi-x-lg me-1"></i> {% trans 'إلغاء' %}
          </a>
          {% endif %}
          {% block form_actions %}{% endblock %}
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
'''

# قالب Detail احترافي عام
DETAIL_TEMPLATE = '''{% extends 'base.html' %}
{% load static %}
{% load i18n %}

{% block title %}{{ page_title|default:"التفاصيل" }} - Tony ERP{% endblock %}

{% block extra_head %}
{{ block.super }}
<style>
  .detail-card {{
    border-radius: 12px;
    overflow: hidden;
  }}
  .detail-card .card-header {{
    background: white;
    border-bottom: 1px solid #e9ecef;
    padding: 1rem 1.25rem;
  }}
  .detail-section {{
    margin-bottom: 1.5rem;
  }}
  .detail-section-title {{
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e9ecef;
    color: #495057;
  }}
  .detail-item {{
    display: flex;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f1f3f5;
  }}
  .detail-item:last-child {{
    border-bottom: none;
  }}
  .detail-label {{
    flex: 0 0 200px;
    font-weight: 600;
    color: #6c757d;
  }}
  .detail-value {{
    flex: 1;
    color: #212529;
  }}
  .status-badge {{
    font-size: 0.875rem;
    padding: 0.35em 0.75em;
  }}
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <!-- Page Header -->
  <div class="d-flex flex-wrap gap-3 justify-content-between align-items-center mb-4">
    <div>
      <h1 class="h4 fw-bold mb-1">
        <i class="bi {{ page_icon|default:'bi-file-text' }} text-primary me-2"></i>
        {{ page_title|default:"التفاصيل" }}
      </h1>
      {% if page_subtitle %}
      <p class="text-muted small mb-0">{{ page_subtitle }}</p>
      {% endif %}
    </div>
    <div class="d-flex gap-2">
      {% block header_actions %}
      {% if edit_url %}
      <a href="{% url edit_url object.pk %}" class="btn btn-primary">
        <i class="bi bi-pencil me-1"></i> {% trans 'تعديل' %}
      </a>
      {% endif %}
      {% if back_url %}
      <a href="{% url back_url %}" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
      {% else %}
      <a href="javascript:history.back()" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-right me-1"></i> {% trans 'رجوع' %}
      </a>
      {% endif %}
      {% endblock %}
    </div>
  </div>

  <!-- Detail Card -->
  <div class="card detail-card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-info-circle text-primary"></i>
        <span class="fw-semibold">{% block detail_title %}معلومات أساسية{% endblock %}</span>
      </div>
      {% block detail_header_actions %}{% endblock %}
    </div>
    <div class="card-body">
      {% block detail_content %}
      {% if object %}
      <div class="detail-section">
        <div class="detail-item">
          <div class="detail-label">{% trans 'العنصر' %}</div>
          <div class="detail-value">{{ object }}</div>
        </div>
      </div>
      {% else %}
      <div class="text-center py-5">
        <i class="bi bi-exclamation-circle display-4 text-muted"></i>
        <h5 class="text-muted mt-3">{% trans 'لا توجد بيانات' %}</h5>
      </div>
      {% endif %}
      {% endblock %}
    </div>
  </div>

  {% block extra_sections %}{% endblock %}
</div>
{% endblock %}
'''

def find_auto_generated_templates():
    """البحث عن القوالب المولدة تلقائياً"""
    templates = []
    for html_file in TEMPLATES_DIR.rglob('*.html'):
        try:
            content = html_file.read_text(encoding='utf-8')
            if 'Auto-generated' in content or 'تم توليده تلقائيًا' in content:
                rel_path = html_file.relative_to(TEMPLATES_DIR)
                templates.append({
                    'path': html_file,
                    'relative': str(rel_path),
                    'type': detect_template_type(rel_path.name, content)
                })
        except Exception as e:
            print(f"خطأ في قراءة {html_file}: {e}")
    return templates


def detect_template_type(filename, content):
    """تحديد نوع القالب (list, form, detail)"""
    name_lower = filename.lower()
    if 'list' in name_lower or 'index' in name_lower:
        return 'list'
    elif 'form' in name_lower or 'create' in name_lower or 'edit' in name_lower or 'new' in name_lower:
        return 'form'
    elif 'detail' in name_lower or 'view' in name_lower or 'show' in name_lower:
        return 'detail'
    else:
        # تحليل المحتوى
        if 'object_list' in content or 'page_obj' in content:
            return 'list'
        elif 'form' in content and 'method="post"' in content:
            return 'form'
        elif 'object.' in content:
            return 'detail'
    return 'unknown'


def generate_report():
    """توليد تقرير بجميع القوالب المولدة تلقائياً"""
    templates = find_auto_generated_templates()
    
    print(f"\n{'='*60}")
    print(f"  تقرير القوالب المولدة تلقائياً (Auto-generated)")
    print(f"{'='*60}")
    print(f"\nإجمالي القوالب: {len(templates)}")
    
    # تصنيف حسب النوع
    by_type = {}
    for t in templates:
        ttype = t['type']
        if ttype not in by_type:
            by_type[ttype] = []
        by_type[ttype].append(t)
    
    print(f"\nتصنيف حسب النوع:")
    for ttype, items in by_type.items():
        print(f"  - {ttype}: {len(items)} قالب")
    
    # تصنيف حسب الوحدة
    by_module = {}
    for t in templates:
        parts = t['relative'].split('\\')
        if len(parts) > 1:
            module = parts[0]
        else:
            module = 'root'
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(t)
    
    print(f"\nتصنيف حسب الوحدة:")
    for module, items in sorted(by_module.items(), key=lambda x: -len(x[1])):
        print(f"  - {module}: {len(items)} قالب")
    
    print(f"\n{'='*60}")
    return templates


if __name__ == '__main__':
    generate_report()
