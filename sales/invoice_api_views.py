"""
API Views للميزات المحسنة للفواتير
Enhanced Invoice Features API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from core.auth_helpers import login_or_jwt_required
from decimal import Decimal
import json
from datetime import timedelta

from sales.models import Invoice, InvoiceItem
from sales.invoice_templates import (
    InvoiceTemplate, 
    InvoiceAutosave, 
    InvoiceAttachment, 
    InvoiceHistory,
    CustomerCreditLimit
)
from partners.models import Customer


# ============================================
# 1. الحفظ التلقائي
# ============================================

@login_required
@require_POST
def autosave_invoice(request):
    """حفظ الفاتورة تلقائياً"""
    try:
        data = json.loads(request.body)
        session_key = data.get('session_key', f'invoice_draft_{request.user.id}')
        form_data = data.get('form_data', {})
        
        # حذف أو تحديث الحفظ السابق
        autosave, created = InvoiceAutosave.objects.update_or_create(
            user=request.user,
            session_key=session_key,
            defaults={
                'form_data': form_data.get('form_data', {}),
                'items_data': form_data.get('items', []),
                'expires_at': timezone.now() + timedelta(days=7)
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'تم الحفظ تلقائياً',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_GET
def load_autosave(request):
    """تحميل آخر حفظ تلقائي"""
    session_key = request.GET.get('session_key', f'invoice_draft_{request.user.id}')
    
    try:
        autosave = InvoiceAutosave.objects.filter(
            user=request.user,
            session_key=session_key
        ).latest('updated_at')
        
        if autosave.is_expired():
            autosave.delete()
            return JsonResponse({
                'success': False,
                'message': 'انتهت صلاحية الحفظ التلقائي'
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'form_data': autosave.form_data,
                'items_data': autosave.items_data,
                'updated_at': autosave.updated_at.isoformat()
            }
        })
        
    except InvoiceAutosave.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'لا يوجد حفظ تلقائي'
        })


# ============================================
# 2. نماذج الفواتير
# ============================================

@login_required
@require_GET
def list_templates(request):
    """قائمة نماذج الفواتير"""
    templates = InvoiceTemplate.objects.filter(
        is_active=True
    ).select_related('customer', 'payment_method')
    
    # فلترة حسب العميل إذا كان محدداً
    customer_id = request.GET.get('customer_id')
    if customer_id:
        templates = templates.filter(customer_id=customer_id)
    
    data = []
    for template in templates:
        data.append({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'customer_id': template.customer_id,
            'customer_name': template.customer.name,
            'payment_method_id': template.payment_method_id if template.payment_method else None,
            'discount': str(template.discount),
            'is_tax_inclusive': template.is_tax_inclusive,
            'items_data': template.items_data,
            'usage_count': template.usage_count
        })
    
    return JsonResponse({
        'success': True,
        'templates': data
    })


@login_required
@require_POST
def create_template(request):
    """إنشاء نموذج فاتورة جديد"""
    try:
        data = json.loads(request.body)
        
        template = InvoiceTemplate.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            customer_id=data.get('customer_id'),
            payment_method_id=data.get('payment_method_id'),
            discount=Decimal(data.get('discount', 0)),
            is_tax_inclusive=data.get('is_tax_inclusive', False),
            items_data=data.get('items_data', []),
            notes=data.get('notes', ''),
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'message': 'تم حفظ النموذج بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def increment_template_usage(request, template_id):
    """زيادة عداد استخدام النموذج"""
    try:
        template = get_object_or_404(InvoiceTemplate, id=template_id)
        template.increment_usage()
        
        return JsonResponse({
            'success': True,
            'usage_count': template.usage_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# 3. البحث الذكي للعملاء
# ============================================

@login_or_jwt_required
@require_GET
def search_customers(request):
    """بحث ذكي في العملاء مع معلومات إضافية"""
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    # البحث في الاسم والهاتف والبريد
    customers = Customer.objects.filter(
        Q(name__icontains=query) |
        Q(phone__icontains=query) |
        Q(email__icontains=query)
    )
    
    total = customers.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    customers = customers[start:end]
    
    results = []
    for customer in customers:
        # حساب الرصيد
        balance = Invoice.objects.filter(
            customer=customer,
            is_deleted=False
        ).aggregate(
            total=Sum('cached_total'),
            paid=Sum('paid')
        )
        
        total_balance = (balance['total'] or Decimal('0')) - (balance['paid'] or Decimal('0'))
        
        # آخر فاتورة
        last_invoice = Invoice.objects.filter(
            customer=customer,
            is_deleted=False
        ).order_by('-date').first()
        
        results.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email,
            'balance': str(total_balance),
            'last_invoice_date': last_invoice.date.isoformat() if last_invoice else None,
        })
    
    return JsonResponse({
        'success': True,
        'results': results,
        'has_more': end < total
    })


@login_required
@require_GET
def customer_last_transactions(request, customer_id):
    """جلب آخر معاملات العميل"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # آخر 3 فواتير
    invoices = Invoice.objects.filter(
        customer=customer,
        is_deleted=False
    ).order_by('-date')[:3]
    
    transactions = []
    for invoice in invoices:
        transactions.append({
            'number': invoice.number,
            'date': invoice.date.isoformat(),
            'total': str(invoice.total),
            'paid': str(invoice.paid),
            'status': 'paid' if invoice.remaining <= 0 else 'pending'
        })
    
    # حساب الرصيد
    balance_data = Invoice.objects.filter(
        customer=customer,
        is_deleted=False
    ).aggregate(
        total=Sum('cached_total'),
        paid=Sum('paid'),
        count=Count('id')
    )
    
    balance = (balance_data['total'] or Decimal('0')) - (balance_data['paid'] or Decimal('0'))
    
    # آخر فاتورة
    last_invoice = invoices.first()
    
    return JsonResponse({
        'success': True,
        'balance': str(balance),
        'invoice_count': balance_data['count'] or 0,
        'last_invoice_date': last_invoice.date.isoformat() if last_invoice else None,
        'last_transactions': transactions
    })


# ============================================
# 4. نسخ من فاتورة سابقة
# ============================================

@login_required
@require_GET
def get_invoice_details(request, invoice_number):
    """جلب تفاصيل فاتورة للنسخ"""
    try:
        invoice = Invoice.objects.get(number=invoice_number, is_deleted=False)
        
        # جلب الأصناف
        items = []
        for item in invoice.items.all():
            items.append({
                'product_id': item.product_id,
                'product_name': item.product.name,
                'location_id': item.location_id,
                'location_name': item.location.name,
                'quantity': item.quantity,
                'price': str(item.price),
                'total': str(item.total)
            })
        
        return JsonResponse({
            'success': True,
            'invoice': {
                'number': invoice.number,
                'customer_id': invoice.customer_id,
                'customer_name': invoice.customer.name,
                'payment_method_id': invoice.payment_method_id if invoice.payment_method else None,
                'discount': str(invoice.discount),
                'is_tax_inclusive': invoice.is_tax_inclusive,
                'items': items
            }
        })
        
    except Invoice.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'الفاتورة غير موجودة'
        }, status=404)


# ============================================
# 5. رفع المرفقات
# ============================================

@login_required
@require_POST
def upload_attachment(request):
    """رفع مرفق للفاتورة"""
    try:
        file = request.FILES.get('file')
        invoice_id = request.POST.get('invoice_id')
        description = request.POST.get('description', '')
        
        if not file:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم اختيار ملف'
            }, status=400)
        
        # التحقق من حجم الملف (5 MB)
        if file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'message': 'حجم الملف كبير جداً (أكثر من 5 MB)'
            }, status=400)
        
        # إذا كان هناك معرف فاتورة، احفظ المرفق
        if invoice_id:
            invoice = get_object_or_404(Invoice, id=invoice_id)
            
            attachment = InvoiceAttachment.objects.create(
                invoice=invoice,
                file=file,
                original_filename=file.name,
                file_type=file.content_type,
                file_size=file.size,
                description=description,
                uploaded_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'attachment_id': attachment.id,
                'filename': attachment.original_filename,
                'message': 'تم رفع الملف بنجاح'
            })
        else:
            # حفظ مؤقت للمرفق
            return JsonResponse({
                'success': True,
                'message': 'تم رفع الملف مؤقتاً'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# 6. تحقق من حد الائتمان
# ============================================

@login_required
@require_POST
def check_credit_limit(request, customer_id):
    """التحقق من حد الائتمان للعميل"""
    try:
        customer = get_object_or_404(Customer, id=customer_id)
        amount = Decimal(request.POST.get('amount', 0))
        
        # الحصول على معلومات الائتمان
        credit_info, created = CustomerCreditLimit.objects.get_or_create(
            customer=customer,
            defaults={
                'credit_limit': Decimal('0'),
                'current_balance': Decimal('0')
            }
        )
        
        # تحديث الرصيد الحالي
        credit_info.update_balance()
        
        # حساب الرصيد الجديد
        new_balance = credit_info.current_balance + amount
        over_limit = new_balance > credit_info.credit_limit
        over_amount = new_balance - credit_info.credit_limit if over_limit else Decimal('0')
        
        # التحقق من الفواتير المتأخرة
        overdue_invoices = Invoice.objects.filter(
            customer=customer,
            is_deleted=False,
            due_date__lt=timezone.now().date()
        ).exclude(
            remaining__lte=0
        )
        
        overdue_count = overdue_invoices.count()
        overdue_amount = sum(inv.remaining for inv in overdue_invoices)
        
        return JsonResponse({
            'success': True,
            'customer_id': customer_id,
            'credit_limit': str(credit_info.credit_limit),
            'current_balance': str(credit_info.current_balance),
            'new_balance': str(new_balance),
            'over_limit': over_limit,
            'over_amount': str(over_amount),
            'is_blocked': credit_info.is_blocked,
            'overdue_invoices': overdue_count,
            'overdue_amount': str(overdue_amount)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# 7. سجل التغييرات
# ============================================

@login_required
@require_GET
def invoice_history(request, invoice_id):
    """عرض سجل تغييرات الفاتورة"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    history = InvoiceHistory.objects.filter(
        invoice=invoice
    ).select_related('user').order_by('-timestamp')[:20]
    
    history_data = []
    for entry in history:
        history_data.append({
            'action': entry.get_action_display(),
            'user': entry.user.username if entry.user else 'نظام',
            'timestamp': entry.timestamp.isoformat(),
            'changes': entry.changes,
            'previous_data': entry.previous_data
        })
    
    return JsonResponse({
        'success': True,
        'history': history_data
    })


# ============================================
# دوال مساعدة لتسجيل التغييرات
# ============================================

def log_invoice_change(invoice, action, user, changes=None, previous_data=None, request=None):
    """تسجيل تغيير في الفاتورة"""
    try:
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        
        InvoiceHistory.objects.create(
            invoice=invoice,
            action=action,
            user=user,
            changes=changes or {},
            previous_data=previous_data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        # لا نريد أن يفشل الطلب بسبب فشل التسجيل
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"فشل تسجيل تغيير الفاتورة: {e}")
