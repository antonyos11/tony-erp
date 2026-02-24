"""
API توليد الأكواد التلقائية - Universal Code Generator
يعمل مع جميع الموديلات في النظام التي تحتوي على حقل كود
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.apps import apps
import re
import logging

logger = logging.getLogger(__name__)

# تعريف جميع الموديلات والأكواد المتاحة
CODE_CONFIG = {
    # الفروع
    'branches.Branch': {'field': 'code', 'prefix': 'BR', 'width': 4},
    
    # المحاسبة
    'accounting.CostCenter': {'field': 'code', 'prefix': 'CC', 'width': 4},
    'accounting.Account': {'field': 'code', 'prefix': 'ACC', 'width': 4},
    'accounting.Bank': {'field': 'code', 'prefix': 'BNK', 'width': 4},
    'accounting.ElectronicAccount': {'field': 'code', 'prefix': 'EA', 'width': 4},
    'accounting.Treasury': {'field': 'code', 'prefix': 'TRS', 'width': 4},
    'accounting.FawryMachine': {'field': 'code', 'prefix': 'FWR', 'width': 4},
    'accounting.VisaMachine': {'field': 'code', 'prefix': 'VSM', 'width': 4},
    'accounting.CostDriver': {'field': 'code', 'prefix': 'CD', 'width': 4},
    'accounting.CostPool': {'field': 'code', 'prefix': 'CP', 'width': 4},
    'accounting.FinancialAnalysis1': {'field': 'code', 'prefix': 'FA1', 'width': 4},
    'accounting.FinancialAnalysis2': {'field': 'code', 'prefix': 'FA2', 'width': 4},
    'accounting.FixedAsset': {'field': 'code', 'prefix': 'AST', 'width': 4},
    
    # المخزون
    'inventory.Product': {'field': 'internal_code', 'prefix': 'PRD', 'width': 5},
    'inventory.Location': {'field': 'code', 'prefix': 'LOC', 'width': 4},
    
    # العملاء
    'crm.Customer': {'field': 'customer_code', 'prefix': 'CUS', 'width': 5},
    'crm.Region': {'field': 'code', 'prefix': 'RGN', 'width': 4},
    
    # الموارد البشرية
    'hr.Department': {'field': 'code', 'prefix': 'DEP', 'width': 4},
    'hr.JobPosition': {'field': 'code', 'prefix': 'JOB', 'width': 4},
    'hr.AllowanceType': {'field': 'code', 'prefix': 'ALW', 'width': 4},
    'hr.DeductionType': {'field': 'code', 'prefix': 'DED', 'width': 4},
    
    # المشاريع
    'projects.ProjectType': {'field': 'code', 'prefix': 'PT', 'width': 4},
    'projects.ProjectCategory': {'field': 'code', 'prefix': 'PCAT', 'width': 4},
    'projects.Project': {'field': 'code', 'prefix': 'PRJ', 'width': 5},
    'projects.Contractor': {'field': 'code', 'prefix': 'CON', 'width': 4},
    
    # المقاولات
    'contracting.ContractingProject': {'field': 'code', 'prefix': 'CPRJ', 'width': 5},
    'contracting.ContractingMaterial': {'field': 'code', 'prefix': 'CMAT', 'width': 4},
    'contracting.ContractingEquipment': {'field': 'code', 'prefix': 'CEQP', 'width': 4},
    
    # الضرائب
    'taxes.TaxCategory': {'field': 'code', 'prefix': 'TAX', 'width': 4},
    'tax_system.TaxType': {'field': 'code', 'prefix': 'TXT', 'width': 4},
    
    # الأصول الثابتة
    'fixed_assets.AssetCategory': {'field': 'code', 'prefix': 'ACAT', 'width': 4},
    
    # التجارة الإلكترونية
    'ecommerce.Coupon': {'field': 'code', 'prefix': 'CPN', 'width': 5},
    
    # الإنتاج
    'production.ProductionWorkCenter': {'field': 'code', 'prefix': 'WC', 'width': 4},
    'production.ProductionStage': {'field': 'code', 'prefix': 'STG', 'width': 4},
    
    # الصيانة
    'maintenance.MachineCategory': {'field': 'code', 'prefix': 'MCAT', 'width': 4},
    'maintenance.Machine': {'field': 'code', 'prefix': 'MCH', 'width': 4},
    'maintenance.MaintenanceType': {'field': 'code', 'prefix': 'MT', 'width': 4},
    'maintenance.SparePart': {'field': 'code', 'prefix': 'SP', 'width': 5},
    
    # الجودة
    'quality_control.QualityStandard': {'field': 'code', 'prefix': 'QS', 'width': 4},
    'quality_control.InspectionType': {'field': 'code', 'prefix': 'INS', 'width': 4},
    'quality_control.QualityInspection': {'field': 'code', 'prefix': 'QI', 'width': 5},
    'quality_control.QualityIssue': {'field': 'code', 'prefix': 'QIS', 'width': 5},
    
    # خدمات المنزل
    'home_services.ServiceType': {'field': 'code', 'prefix': 'SVC', 'width': 4},
    'home_services.MaintenanceCategory': {'field': 'code', 'prefix': 'HMNT', 'width': 4},
    'home_services.CleaningPackage': {'field': 'code', 'prefix': 'CLN', 'width': 4},
    
    # الشحن
    'shipping.ShippingCompany': {'field': 'code', 'prefix': 'SHP', 'width': 4},
    'shipping.ShippingZone': {'field': 'code', 'prefix': 'SHZ', 'width': 4},
    
    # الولاء
    'loyalty.LoyaltyProgram': {'field': 'code', 'prefix': 'LYL', 'width': 4},
    
    # الموردين
    'partners.Supplier': {'field': 'code', 'prefix': 'SUP', 'width': 5},
    
    # الاشتراكات
    'subscriptions.SubscriptionPlan': {'field': 'code', 'prefix': 'SUB', 'width': 4},
    
    # الميزانية
    'budgeting.FiscalYear': {'field': 'code', 'prefix': 'FY', 'width': 4},
    
    # الامتثال
    'compliance_management.ComplianceStandard': {'field': 'code', 'prefix': 'CMP', 'width': 4},
    
    # الحضور
    'attendance.WorkLocation': {'field': 'code', 'prefix': 'WLO', 'width': 4},
    
    # المعارض
    'showrooms.Showroom': {'field': 'code', 'prefix': 'SHR', 'width': 4},
    
    # Core
    'core.Branch': {'field': 'code', 'prefix': 'BR', 'width': 4},
    'core.Page': {'field': 'code', 'prefix': 'PG', 'width': 4},
}


def _get_next_code(model_class, field_name, prefix, width):
    """
    يحسب الكود التالي بناءً على آخر كود موجود في قاعدة البيانات
    """
    # البحث عن آخر كود يبدأ بنفس البريفكس
    pattern = f'^{re.escape(prefix)}-?\\d'
    
    try:
        last_obj = model_class.objects.filter(
            **{f'{field_name}__regex': pattern}
        ).order_by(f'-{field_name}').first()
    except Exception:
        last_obj = None
    
    if last_obj:
        last_code = getattr(last_obj, field_name, '')
        # استخراج الرقم من آخر كود
        match = re.search(r'(\d+)$', last_code)
        if match:
            next_num = int(match.group(1)) + 1
        else:
            next_num = 1
    else:
        # لا يوجد أكواد سابقة، نبحث عن عدد العناصر
        count = model_class.objects.count()
        next_num = count + 1
    
    # توليد الكود الجديد
    new_code = f"{prefix}-{str(next_num).zfill(width)}"
    
    # التأكد من عدم التكرار
    while model_class.objects.filter(**{field_name: new_code}).exists():
        next_num += 1
        new_code = f"{prefix}-{str(next_num).zfill(width)}"
    
    return new_code


@login_required
def generate_code(request):
    """
    API لتوليد كود فريد تلقائياً
    GET /api/generate-code/?model=branches.Branch
    GET /api/generate-code/?model=branches.Branch&prefix=BR&field=code
    """
    model_key = request.GET.get('model', '')
    custom_prefix = request.GET.get('prefix', '')
    custom_field = request.GET.get('field', '')
    
    if not model_key:
        return JsonResponse({
            'success': False,
            'error': 'يجب تحديد الموديل (model parameter)'
        }, status=400)
    
    # البحث عن إعدادات الموديل
    config = CODE_CONFIG.get(model_key)
    
    if not config:
        # محاولة البحث بدون حساسية لحالة الأحرف
        for key, val in CODE_CONFIG.items():
            if key.lower() == model_key.lower():
                config = val
                model_key = key
                break
    
    if not config and not (custom_prefix and custom_field):
        # محاولة اكتشاف الموديل تلقائياً
        try:
            app_label, model_name = model_key.split('.')
            model_class = apps.get_model(app_label, model_name)
            # البحث عن حقل كود
            code_field = None
            for f in model_class._meta.get_fields():
                if hasattr(f, 'name') and f.name == 'code':
                    code_field = 'code'
                    break
            if code_field:
                config = {'field': code_field, 'prefix': model_name[:3].upper(), 'width': 4}
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'الموديل "{model_key}" غير مدعوم. تأكد من الاسم.'
                }, status=400)
        except Exception:
            return JsonResponse({
                'success': False,
                'error': f'الموديل "{model_key}" غير موجود.'
            }, status=400)
    
    # استخدام الإعدادات المخصصة إذا وجدت
    field_name = custom_field or config['field']
    prefix = custom_prefix or config['prefix']
    width = config.get('width', 4)
    
    try:
        app_label, model_name = model_key.split('.')
        model_class = apps.get_model(app_label, model_name)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'خطأ في تحميل الموديل: {str(e)}'
        }, status=400)
    
    try:
        new_code = _get_next_code(model_class, field_name, prefix, width)
        
        return JsonResponse({
            'success': True,
            'code': new_code,
            'model': model_key,
            'prefix': prefix,
            'field': field_name,
        })
    except Exception as e:
        logger.error(f"Error generating code for {model_key}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطأ في توليد الكود: {str(e)}'
        }, status=500)


@login_required
def get_available_models(request):
    """
    API لإرجاع قائمة بجميع الموديلات المتاحة للتوليد التلقائي
    GET /api/generate-code/models/
    """
    models_list = []
    for key, config in CODE_CONFIG.items():
        try:
            app_label, model_name = key.split('.')
            model_class = apps.get_model(app_label, model_name)
            verbose_name = model_class._meta.verbose_name
            models_list.append({
                'key': key,
                'app': app_label,
                'model': model_name,
                'field': config['field'],
                'prefix': config['prefix'],
                'verbose_name': str(verbose_name),
            })
        except Exception:
            pass  # تخطي الموديلات غير المتوفرة
    
    return JsonResponse({
        'success': True,
        'models': models_list,
        'total': len(models_list),
    })
