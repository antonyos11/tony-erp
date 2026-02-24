# -*- coding: utf-8 -*-
"""
مثال لدمج نظام الطباعة مع Django
ضع هذا الكود في ملف views.py أو أنشئ ملف جديد في تطبيقك
"""

from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
import json


@login_required
@require_http_methods(["GET"])
def invoice_print_html(request, invoice_id):
    """
    API لإرجاع HTML للطباعة
    استخدم هذا مع Print Agent
    
    URL: /api/invoices/<invoice_id>/print-html/
    """
    Invoice = None  # type: ignore
    try:
        # استيراد النماذج (عدّل حسب المشروع)
        from invoices.models import Invoice  # type: ignore[import-unresolved]
        
        # جلب الفاتورة
        invoice = Invoice.objects.select_related(
            'branch', 'cashier', 'customer'
        ).prefetch_related('items__product').get(id=invoice_id)
        
        # التحقق من الصلاحيات
        if not request.user.has_perm('invoices.view_invoice'):
            return HttpResponse('غير مصرح', status=403)
        
        # إعداد البيانات
        context = {
            'invoice': invoice,
            'items': invoice.items.all(),
            'company': {
                'name': 'شركة توني للإسفنج',
                'name_en': 'Tony Foam Company',
                'address': 'الرياض، المملكة العربية مصر',
                'cr_number': '1234567890',
                'vat_number': '310123456700003',
                'phone': '+966 11 234 5678',
            },
            'branch': invoice.branch,
        }
        
        # تحويل لـ HTML
        html = render_to_string('invoices/print_invoice.html', context)
        
        return HttpResponse(html, content_type='text/html; charset=utf-8')
        
    except Exception as e:
        if 'DoesNotExist' in type(e).__name__:
            return JsonResponse({'error': 'الفاتورة غير موجودة'}, status=404)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def receipt_print_html(request, receipt_id):
    """
    API لطباعة إيصال استلام
    
    URL: /api/receipts/<receipt_id>/print-html/
    """
    Receipt = None  # type: ignore
    try:
        from receipts.models import Receipt  # type: ignore[import-unresolved]
        
        receipt = Receipt.objects.select_related('customer', 'cashier').get(id=receipt_id)
        
        context = {
            'receipt': receipt,
            'company': {
                'name': 'شركة توني للإسفنج',
                'address': 'الرياض، المملكة العربية مصر',
            }
        }
        
        html = render_to_string('receipts/print_receipt.html', context)
        
        return HttpResponse(html, content_type='text/html; charset=utf-8')
        
    except Exception as e:
        if 'DoesNotExist' in type(e).__name__:
            return JsonResponse({'error': 'الإيصال غير موجود'}, status=404)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def print_test(request):
    """
    API لاختبار الطباعة
    
    URL: /api/print/test/
    Body: {"printer": "default", "type": "text"}
    """
    try:
        data = json.loads(request.body)
        printer = data.get('printer', 'default')
        print_type = data.get('type', 'text')
        
        # محتوى الاختبار
        test_content = f"""
╔═══════════════════════════════════════╗
║      Tony ERP - طباعة اختبارية       ║
╚═══════════════════════════════════════╝

الطابعة: {printer}
المستخدم: {request.user.get_full_name()}
الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✓ الطابعة تعمل بشكل صحيح
✓ الاتصال سليم
✓ النظام جاهز للطباعة

════════════════════════════════════════
        """
        
        return JsonResponse({
            'success': True,
            'content': test_content,
            'printer': printer,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# إضافة هذه الـ URLs في urls.py
# ============================================
"""
from django.urls import path
from . import views

urlpatterns = [
    # طباعة الفواتير
    path('api/invoices/<int:invoice_id>/print-html/', 
         views.invoice_print_html, 
         name='invoice_print_html'),
    
    # طباعة الإيصالات
    path('api/receipts/<int:receipt_id>/print-html/', 
         views.receipt_print_html, 
         name='receipt_print_html'),
    
    # اختبار الطباعة
    path('api/print/test/', 
         views.print_test, 
         name='print_test'),
]
"""
