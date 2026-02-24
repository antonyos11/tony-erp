"""
HR module integration:
  - Print employee ID card with QR code
تكامل الموارد البشرية:
  - طباعة بطاقة هوية الموظف مع رمز QR
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def print_employee_id_card(employee, user=None) -> Tuple[bool, str]:
    """
    Generate and print an employee ID card.
    Renders an HTML card with employee photo and QR code,
    converts to PDF, and sends to the card/A4 printer.
    """
    from printing.dispatch import PrintDispatcher
    from django.template.loader import render_to_string

    try:
        from core.models import Company
        company = Company.objects.first()
    except Exception:
        company = None

    # Generate QR code data
    import json
    qr_data = json.dumps({
        'emp_id': employee.employee_id or str(employee.pk),
        'name': str(employee),
        'dept': str(employee.department) if hasattr(employee, 'department') and employee.department else '',
    }, ensure_ascii=False)

    html = render_to_string('hr/id_card_print.html', {
        'employee': employee,
        'company': company,
        'qr_data': qr_data,
    })

    # Try PDF
    pdf_bytes = None
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
    except Exception as e:
        logger.warning(f"WeasyPrint failed for ID card: {e}")

    if pdf_bytes:
        success, msg, job = PrintDispatcher.print_pdf(
            document_type='hr_id_card',
            pdf_bytes=pdf_bytes,
            title=f"بطاقة هوية - {employee}",
            user=user,
            source_app='hr',
            source_model='Employee',
            source_id=str(employee.pk),
        )
    else:
        success, msg, job = PrintDispatcher.print_html(
            document_type='hr_id_card',
            html=html,
            title=f"بطاقة هوية - {employee}",
            user=user,
            source_app='hr',
            source_model='Employee',
            source_id=str(employee.pk),
        )

    return success, msg
