# -*- coding: utf-8 -*-
"""
Stub view for placeholder URL patterns.
Returns a simple "under development" page for any URL that
has been registered but doesn't have a real view yet.
"""
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required


@login_required
def stub_view(request, *args, **kwargs):
    """Generic placeholder view for unimplemented features."""
    path = request.path
    # Try to guess a nice title from the URL
    parts = [p for p in path.strip('/').split('/') if p and not p.isdigit()]
    title = ' / '.join(p.replace('-', ' ').replace('_', ' ').title() for p in parts[-2:])

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>{title} - قيد التطوير</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow-sm">
                    <div class="card-body text-center py-5">
                        <i class="fas fa-hard-hat fa-4x text-warning mb-4"></i>
                        <h3 class="mb-3">{title}</h3>
                        <p class="text-muted fs-5">هذه الصفحة قيد التطوير</p>
                        <p class="text-muted"><code>{path}</code></p>
                        <hr>
                        <a href="javascript:history.back()" class="btn btn-secondary me-2">
                            <i class="fas fa-arrow-right"></i> رجوع
                        </a>
                        <a href="/" class="btn btn-primary">
                            <i class="fas fa-home"></i> الرئيسية
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html)
