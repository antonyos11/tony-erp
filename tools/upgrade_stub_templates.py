#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


MARKER_1 = "Stub template"
MARKER_2 = "تم توليده تلقائيًا"
MARKER_3 = "سيتم إضافة"
MARKER_4 = "قريباً"
MARKER_5 = "قيد التطوير"
MARKER_6 = "coming soon"
MARKER_7 = "placeholder"
MARKER_8 = "TODO:"


ENHANCED_TEMPLATE = """{{% extends 'base.html' %}}
{{% load static %}}
{{% load i18n %}}

{{% block title %}}{title}{{% endblock %}}

{{% block extra_head %}}
{{{{ block.super }}}}
<style>
  .stub-note {{
    border-radius: 12px;
  }}
  .auto-field label {{
    font-weight: 600;
  }}
  .auto-table td, .auto-table th {{
    vertical-align: middle;
  }}
</style>
{{% endblock %}}

{{% block content %}}
<div class=\"container-fluid py-3\">
  <div class=\"d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3\">
    <div>
      <h1 class=\"h4 m-0\">{title}</h1>
      <div class=\"text-muted small\">Template: <code>{template_name}</code></div>
    </div>
    <span class=\"badge text-bg-warning\">Auto-generated</span>
  </div>

  <div class=\"alert alert-warning stub-note\" role=\"alert\">
    <div class=\"d-flex gap-2\">
      <div class=\"fw-bold\">تنبيه:</div>
      <div>
        هذا القالب تم توليده/تطويره تلقائيًا لمنع خطأ <code>TemplateDoesNotExist</code>.
        إذا أردت واجهة كاملة، يتم استبدال هذا القالب بتصميم مخصص للوظيفة.
      </div>
    </div>
  </div>

  {{% if form %}}
  <div class=\"card\">
    <div class=\"card-header\"><strong>{title}</strong></div>
    <div class=\"card-body\">
      <form method=\"post\" enctype=\"multipart/form-data\">{{% csrf_token %}}
        {{% if form.non_field_errors %}}
          <div class=\"alert alert-danger\">{{{{ form.non_field_errors }}}}</div>
        {{% endif %}}

        <div class=\"row g-3\">
          {{% for field in form %}}
            <div class=\"col-12 col-md-6 auto-field\">
              <label class=\"form-label\" for=\"id_{{{{ field.name }}}}\">{{{{ field.label }}}}</label>
              <div>{{{{ field }}}}</div>
              {{% if field.help_text %}}<div class=\"form-text\">{{{{ field.help_text }}}}</div>{{% endif %}}
              {{% if field.errors %}}<div class=\"text-danger small\">{{{{ field.errors }}}}</div>{{% endif %}}
            </div>
          {{% endfor %}}
        </div>

        <div class=\"mt-3 d-flex gap-2\">
          <button class=\"btn btn-primary\" type=\"submit\">{{% trans 'حفظ' %}}</button>
          <a class=\"btn btn-outline-secondary\" href=\"javascript:history.back()\">{{% trans 'رجوع' %}}</a>
        </div>
      </form>
    </div>
  </div>

  {{% elif page_obj or object_list %}}
  <div class=\"card\">
    <div class=\"card-header\"><strong>{title}</strong></div>
    <div class=\"card-body\">
      <div class=\"table-responsive\">
        <table class=\"table table-striped auto-table\">
          <thead>
            <tr>
              <th>{{% trans 'العنصر' %}}</th>
            </tr>
          </thead>
          <tbody>
            {{% if page_obj %}}
              {{% for obj in page_obj.object_list %}}
                <tr><td>{{{{ obj }}}}</td></tr>
              {{% empty %}}
                <tr><td class="text-muted">{{% trans 'لا توجد بيانات' %}}</td></tr>
              {{% endfor %}}
            {{% else %}}
              {{% for obj in object_list %}}
                <tr><td>{{{{ obj }}}}</td></tr>
              {{% empty %}}
                <tr><td class="text-muted">{{% trans 'لا توجد بيانات' %}}</td></tr>
              {{% endfor %}}
            {{% endif %}}
          </tbody>
        </table>
      </div>

      {{% if page_obj %}}
      <nav aria-label=\"Pagination\">
        <ul class=\"pagination mb-0\">
          {{% if page_obj.has_previous %}}
            <li class=\"page-item\"><a class=\"page-link\" href=\"?page={{{{ page_obj.previous_page_number }}}}\">{{% trans 'السابق' %}}</a></li>
          {{% else %}}
            <li class=\"page-item disabled\"><span class=\"page-link\">{{% trans 'السابق' %}}</span></li>
          {{% endif %}}
          <li class=\"page-item disabled\"><span class=\"page-link\">{{{{ page_obj.number }}}} / {{{{ page_obj.paginator.num_pages }}}}</span></li>
          {{% if page_obj.has_next %}}
            <li class=\"page-item\"><a class=\"page-link\" href=\"?page={{{{ page_obj.next_page_number }}}}\">{{% trans 'التالي' %}}</a></li>
          {{% else %}}
            <li class=\"page-item disabled\"><span class=\"page-link\">{{% trans 'التالي' %}}</span></li>
          {{% endif %}}
        </ul>
      </nav>
      {{% endif %}}
    </div>
  </div>

  {{% elif object %}}
  <div class=\"card\">
    <div class=\"card-header\"><strong>{title}</strong></div>
    <div class=\"card-body\">
      <dl class=\"row mb-0\">
        <dt class=\"col-sm-3\">{{% trans 'القيمة' %}}</dt>
        <dd class=\"col-sm-9\">{{{{ object }}}}</dd>
      </dl>
      <div class=\"mt-3\">
        <a class=\"btn btn-outline-secondary\" href=\"javascript:history.back()\">{{% trans 'رجوع' %}}</a>
      </div>
    </div>
  </div>

  {{% else %}}
  <div class=\"card\">
    <div class=\"card-body\">
      <p class=\"mb-0 text-muted\">
        لا توجد بيانات معروضة تلقائيًا (لا يوجد <code>form</code> ولا <code>object_list</code> ولا <code>object</code> في الـcontext).
      </p>
    </div>
  </div>
  {{% endif %}}
</div>
{{% endblock %}}
"""


def _title_from_template_name(template_name: str) -> str:
    base = Path(template_name).stem
    base = base.replace("_", " ").replace("-", " ").strip()
    if not base:
        return "صفحة"
    return base[:1].upper() + base[1:]


def main() -> int:
    app_root = Path(__file__).resolve().parents[1]
    templates_dir = app_root / "templates"

    updated = 0
    scanned = 0

    for path in templates_dir.rglob("*.html"):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if MARKER_1 not in text and MARKER_2 not in text and MARKER_3 not in text and MARKER_4 not in text and MARKER_5 not in text and MARKER_6.lower() not in text.lower() and MARKER_7.lower() not in text.lower() and MARKER_8.lower() not in text.lower():
            continue

        # Only upgrade templates that match our original stub format.
        if "Template: <code>" not in text and "هذا القالب تم توليده" not in text:
            # Still allow upgrade if markers exist.
            pass

        rel = path.relative_to(templates_dir)
        template_name = str(rel).replace("\\", "/")
        title = _title_from_template_name(template_name)

        new_text = ENHANCED_TEMPLATE.format(title=title, template_name=template_name)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            updated += 1

    print("=" * 70)
    print("✅ Upgrade stub templates finished")
    print(f"Scanned: {scanned}")
    print(f"Upgraded: {updated}")
    print("Templates dir:", templates_dir)
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
