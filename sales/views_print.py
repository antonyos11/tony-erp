"""
sales/views_print.py – A4 print views for sales invoices
Provides:
  • sales_invoice_a4_data  – JSON API returning rendered A4 HTML (for print agent)
  • sales_invoice_a4_print – Browser view for direct A4 printing
"""
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Invoice


def _get_invoice_context(pk):
    """Shared context builder for print views."""
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.select_related('product').all()

    # Company info
    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    return {
        'invoice': invoice,
        'items': items,
        'company': company,
    }


def sales_invoice_a4_data(request, pk):
    """Return rendered A4 HTML as JSON – consumed by print agent via WebSocket."""
    ctx = _get_invoice_context(pk)
    html = render_to_string('sales/invoice_print_a4_new.html', ctx, request=request)
    return JsonResponse({'success': True, 'html': html})


def sales_invoice_a4_print(request, pk):
    """Browser-based A4 print view (opens window.print)."""
    ctx = _get_invoice_context(pk)
    return render(request, 'sales/invoice_print_a4_new.html', ctx)
