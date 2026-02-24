"""
نقاط API للميزات المتقدمة في نموذج الإيراد/المنصرف
Tony ERP - Accounting Module

الميزات المدعومة:
1. الحفظ التلقائي (Autosave)
2. جلب بيانات الفاتورة
3. فحص الحد الائتماني
4. سجل التغييرات
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def autosave_entry(request):
    """
    حفظ مسودة القيد تلقائياً
    
    يستقبل بيانات النموذج ويحفظها في الكاش لمدة ساعة
    """
    try:
        data = json.loads(request.body)
        
        # إنشاء مفتاح فريد للمستخدم
        cache_key = f"entry_draft_{request.user.id}_{data.get('entry_type', 'revenue')}"
        
        # حفظ في الكاش لمدة ساعة
        cache.set(cache_key, {
            'data': data,
            'user_id': request.user.id,
            'timestamp': str(__import__('datetime').datetime.now())
        }, 3600)
        
        return JsonResponse({
            'success': True,
            'message': 'تم حفظ المسودة بنجاح'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات غير صالحة'
        }, status=400)
    except Exception as e:
        logger.error(f"خطأ في الحفظ التلقائي: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في الحفظ'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_invoice_data(request, invoice_number):
    """
    جلب بيانات فاتورة لنسخها إلى قيد جديد
    
    يبحث في فواتير المبيعات والمشتريات
    """
    try:
        # البحث في فواتير المبيعات
        try:
            from sales.models import Invoice
            invoice = Invoice.objects.filter(number=invoice_number).first()
            if invoice:
                return JsonResponse({
                    'success': True,
                    'type': 'sales',
                    'amount': str(invoice.cached_total or invoice.total or 0),
                    'description': f"إيراد من فاتورة مبيعات رقم {invoice.number}",
                    'customer_name': getattr(invoice.customer, 'name', '') if invoice.customer else '',
                    'date': str(invoice.date) if invoice.date else '',
                })
        except ImportError:
            pass
        
        # البحث في فواتير الشراء
        try:
            from purchases.models import PurchaseBill
            bill = PurchaseBill.objects.filter(number=invoice_number).first()
            if bill:
                return JsonResponse({
                    'success': True,
                    'type': 'purchase',
                    'amount': str(bill.total or 0),
                    'description': f"منصرف من فاتورة شراء رقم {bill.number}",
                    'supplier_name': getattr(bill.supplier, 'name', '') if bill.supplier else '',
                    'date': str(bill.date) if bill.date else '',
                })
        except ImportError:
            pass
        
        return JsonResponse({
            'success': False,
            'error': 'لم يتم العثور على الفاتورة'
        }, status=404)
        
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات الفاتورة: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب البيانات'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def check_supplier_credit(request, supplier_id):
    """
    فحص الحد الائتماني للمورد
    
    يعيد معلومات عن الرصيد الحالي والحد المسموح
    """
    try:
        from partners.models import Supplier
        
        supplier = Supplier.objects.filter(id=supplier_id).first()
        if not supplier:
            return JsonResponse({
                'success': False,
                'error': 'المورد غير موجود'
            }, status=404)
        
        # محاولة حساب الرصيد الحالي
        balance = 0
        try:
            from accounting.models import AccountEntry
            from django.db.models import Sum
            
            # مجموع الإيرادات المرتبطة بالمورد
            revenue_total = AccountEntry.objects.filter(
                supplier=supplier,
                entry_type='revenue'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            balance = float(revenue_total)
        except Exception:
            pass
        
        # الحد الائتماني (إذا كان موجوداً في نموذج المورد)
        credit_limit = getattr(supplier, 'credit_limit', None) or 0
        
        exceeded = credit_limit > 0 and balance > credit_limit
        
        return JsonResponse({
            'success': True,
            'supplier_name': supplier.name,
            'balance': balance,
            'limit': float(credit_limit),
            'exceeded': exceeded,
            'remaining': max(0, float(credit_limit) - balance) if credit_limit else None
        })
        
    except Exception as e:
        logger.error(f"خطأ في فحص الحد الائتماني: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في الفحص'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_entry_history(request):
    """
    جلب سجل التغييرات للقيود
    
    يعيد آخر 10 تغييرات أجراها المستخدم
    """
    try:
        history = []
        
        # محاولة جلب من سجل التدقيق
        try:
            from core.models import AuditLog
            
            logs = AuditLog.objects.filter(
                user=request.user,
                model_name='AccountEntry'
            ).order_by('-created_at')[:10]
            
            for log in logs:
                history.append({
                    'action': str(log.action),
                    'timestamp': log.created_at.strftime('%Y-%m-%d %H:%M'),
                    'changes': str(log.changes) if hasattr(log, 'changes') else None
                })
        except ImportError:
            # إذا لم يكن نموذج AuditLog موجوداً
            history.append({
                'action': 'سجل التغييرات غير متاح',
                'timestamp': '',
                'changes': None
            })
        
        return JsonResponse({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب سجل التغييرات: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب السجل'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def search_accounts(request):
    """
    البحث الذكي عن الحسابات
    
    يبحث بالكود أو الاسم ويعيد أفضل 20 نتيجة
    """
    try:
        from accounting.models import Account
        from django.db.models import Q
        
        query = request.GET.get('q', '').strip()
        if len(query) < 1:
            return JsonResponse({'accounts': []})
        
        # البحث في الكود والاسم
        accounts = Account.objects.filter(
            Q(code__icontains=query) | Q(name__icontains=query),
            is_active=True,
            can_post=True
        ).order_by('code')[:20]
        
        results = []
        for account in accounts:
            try:
                balance = float(account.balance) if hasattr(account, 'balance') else 0
            except Exception:
                balance = 0
            
            results.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'type': account.account_type,
                'balance': balance,
                'display': f"{account.code} - {account.name}"
            })
        
        return JsonResponse({
            'success': True,
            'accounts': results
        })
        
    except Exception as e:
        logger.error(f"خطأ في البحث عن الحسابات: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في البحث'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_templates(request):
    """
    جلب قوالب القيود المحفوظة
    
    يعيد القوالب الافتراضية والقوالب التي أنشأها المستخدم
    """
    try:
        # قوالب افتراضية
        default_templates = [
            {
                'id': 'rent',
                'name': 'إيجار شهري',
                'icon': 'bi-building',
                'is_default': True,
                'data': {
                    'description': 'إيجار شهر ',
                    'amount': ''
                }
            },
            {
                'id': 'salary',
                'name': 'رواتب موظفين',
                'icon': 'bi-people',
                'is_default': True,
                'data': {
                    'description': 'رواتب شهر ',
                    'amount': ''
                }
            },
            {
                'id': 'utilities',
                'name': 'فواتير خدمات',
                'icon': 'bi-lightning',
                'is_default': True,
                'data': {
                    'description': 'فواتير خدمات ',
                    'amount': ''
                }
            },
            {
                'id': 'commission',
                'name': 'عمولة مبيعات',
                'icon': 'bi-percent',
                'is_default': True,
                'data': {
                    'description': 'عمولة مبيعات ',
                    'amount': ''
                }
            },
        ]
        
        # القوالب المحفوظة من قاعدة البيانات (إذا وجدت)
        user_templates = []
        try:
            from accounting.models import EntryTemplate
            
            templates = EntryTemplate.objects.filter(
                created_by=request.user,
                is_active=True
            ).order_by('-created_at')[:10]
            
            for tpl in templates:
                user_templates.append({
                    'id': f'user_{tpl.id}',
                    'name': tpl.name,
                    'icon': 'bi-star',
                    'is_default': False,
                    'data': tpl.data if hasattr(tpl, 'data') else {}
                })
        except ImportError:
            pass
        
        return JsonResponse({
            'success': True,
            'default_templates': default_templates,
            'user_templates': user_templates
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب القوالب: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب القوالب'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def save_template(request):
    """
    حفظ قالب جديد
    
    يحفظ بيانات النموذج الحالي كقالب قابل لإعادة الاستخدام
    """
    try:
        data = json.loads(request.body)
        
        template_name = data.get('name', '').strip()
        if not template_name:
            return JsonResponse({
                'success': False,
                'error': 'اسم القالب مطلوب'
            }, status=400)
        
        template_data = data.get('data', {})
        
        # محاولة الحفظ في قاعدة البيانات
        try:
            from accounting.models import EntryTemplate
            
            template = EntryTemplate.objects.create(
                name=template_name,
                data=template_data,
                created_by=request.user,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'template_id': template.id,
                'message': 'تم حفظ القالب بنجاح'
            })
        except ImportError:
            # إذا لم يكن نموذج القوالب موجوداً، نحفظ في الكاش
            cache_key = f"user_templates_{request.user.id}"
            templates = cache.get(cache_key) or []
            templates.append({
                'id': len(templates) + 1,
                'name': template_name,
                'data': template_data
            })
            cache.set(cache_key, templates, 86400 * 30)  # 30 يوم
            
            return JsonResponse({
                'success': True,
                'message': 'تم حفظ القالب بنجاح (في الذاكرة المؤقتة)'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات غير صالحة'
        }, status=400)
    except Exception as e:
        logger.error(f"خطأ في حفظ القالب: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في الحفظ'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_tax_settings(request):
    """
    جلب إعدادات الضريبة
    
    يعيد نسبة الضريبة المفعلة في النظام
    """
    try:
        # محاولة جلب من إعدادات المحاسبة
        tax_rate = 0.15  # القيمة الافتراضية
        tax_enabled = True
        
        try:
            from accounting.models import AccountingSettings
            settings = AccountingSettings.get()
            tax_rate = float(settings.default_vat_rate) / 100 if settings.default_vat_rate else 0.15
            tax_enabled = settings.enable_vat
        except Exception:
            pass
        
        return JsonResponse({
            'success': True,
            'tax_rate': tax_rate,
            'tax_enabled': tax_enabled,
            'tax_percentage': tax_rate * 100
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب إعدادات الضريبة: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ في جلب الإعدادات'
        }, status=500)
