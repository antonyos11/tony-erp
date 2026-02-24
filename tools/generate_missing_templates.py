#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from pathlib import Path


STUB_TEMPLATE = """{{% extends 'base.html' %}}
{{% load static %}}
{{% load i18n %}}

{{% block title %}}{title}{{% endblock %}}

{{% block content %}}
<div class=\"container-fluid py-4\">
  <div class=\"d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3\">
    <h1 class=\"h4 m-0\">{title}</h1>
    <span class=\"badge text-bg-warning\">Stub template</span>
  </div>
  <div class=\"card\">
    <div class=\"card-body\">
      <p class=\"mb-2\">هذا القالب تم توليده تلقائيًا لأنه كان مفقودًا.</p>
      <p class=\"mb-0\"><strong>Template:</strong> <code>{template_name}</code></p>
    </div>
  </div>
</div>
{{% endblock %}}
"""


def _load_check_templates_module(app_root: Path):
    module_path = app_root / "check_templates.py"
    spec = importlib.util.spec_from_file_location("check_templates", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def _title_from_template_name(template_name: str) -> str:
    base = Path(template_name).stem
    base = base.replace("_", " ").replace("-", " ").strip()
    if not base:
        return "صفحة"
    # Keep it simple; Arabic titles will stay as-is.
    return base[:1].upper() + base[1:]


def main() -> int:
    # This script lives in app/tools/; app root is one level up.
    app_root = Path(__file__).resolve().parents[1]
    templates_dir = app_root / "templates"

    check_templates = _load_check_templates_module(app_root)

    # Run analysis from app root to match check_templates() expectations.
    cwd = Path.cwd()
    try:
        import os

        os.chdir(app_root)
        report = check_templates.check_templates()
    finally:
        import os

        os.chdir(cwd)

    missing = report.get("missing", [])

    created = 0
    skipped = 0

    for template_name, _locations in missing:
        out_path = templates_dir / template_name
        if out_path.exists():
            skipped += 1
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        title = _title_from_template_name(template_name)
        out_path.write_text(
            STUB_TEMPLATE.format(title=title, template_name=template_name),
            encoding="utf-8",
        )
        created += 1

    print("=" * 70)
    print("✅ توليد القوالب الناقصة انتهى")
    print(f"Created: {created}")
    print(f"Skipped (already existed): {skipped}")
    print("Templates dir:", templates_dir)
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
