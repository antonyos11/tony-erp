"""
Views لإدارة معاملات التحويل
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from inventory.conversion_factors import ConversionFactor, load_common_conversions


@login_required
def conversion_factors_list(request):
    """قائمة معاملات التحويل"""
    factors = ConversionFactor.objects.all().order_by('material_type', 'from_unit', 'to_unit')
    
    context = {
        'title': 'معاملات التحويل',
        'factors': factors,
    }
    return render(request, 'inventory/conversion_factors_list.html', context)


@login_required
def conversion_factor_create(request):
    """إضافة معامل تحويل جديد"""
    if request.method == 'POST':
        from_unit = request.POST.get('from_unit', '').strip()
        to_unit = request.POST.get('to_unit', '').strip()
        factor = request.POST.get('factor', '').strip()
        material_type = request.POST.get('material_type', 'general')
        description = request.POST.get('description', '').strip()
        
        try:
            ConversionFactor.objects.create(
                from_unit=from_unit,
                to_unit=to_unit,
                factor=Decimal(factor),
                material_type=material_type,
                description=description,
                is_active=True
            )
            messages.success(request, 'تم إضافة معامل التحويل بنجاح')
            return redirect('inventory:conversion_factors_list')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': 'إضافة معامل تحويل',
        'material_types': ConversionFactor.MATERIAL_TYPE_CHOICES,
    }
    return render(request, 'inventory/conversion_factor_form.html', context)


@login_required
def conversion_factor_edit(request, pk):
    """تعديل معامل تحويل"""
    cf = get_object_or_404(ConversionFactor, pk=pk)
    
    if request.method == 'POST':
        cf.from_unit = request.POST.get('from_unit', '').strip()
        cf.to_unit = request.POST.get('to_unit', '').strip()
        cf.factor = Decimal(request.POST.get('factor', '1'))
        cf.material_type = request.POST.get('material_type', 'general')
        cf.description = request.POST.get('description', '').strip()
        cf.is_active = request.POST.get('is_active') == 'on'
        
        try:
            cf.save()
            messages.success(request, 'تم تحديث معامل التحويل بنجاح')
            return redirect('inventory:conversion_factors_list')
        except Exception as e:
            messages.error(request, f'خطأ: {str(e)}')
    
    context = {
        'title': 'تعديل معامل تحويل',
        'cf': cf,
        'material_types': ConversionFactor.MATERIAL_TYPE_CHOICES,
    }
    return render(request, 'inventory/conversion_factor_form.html', context)


@login_required
def conversion_factor_delete(request, pk):
    """حذف معامل تحويل"""
    cf = get_object_or_404(ConversionFactor, pk=pk)
    cf.delete()
    messages.success(request, 'تم حذف معامل التحويل')
    return redirect('inventory:conversion_factors_list')


@login_required
def load_default_conversions(request):
    """تحميل معاملات التحويل الافتراضية"""
    count = load_common_conversions()
    messages.success(request, f'تم تحميل {count} معامل تحويل افتراضي')
    return redirect('inventory:conversion_factors_list')


# API Endpoints
@login_required
def api_get_conversion_factor(request):
    """API: الحصول على معامل التحويل"""
    from_unit = request.GET.get('from_unit', '')
    to_unit = request.GET.get('to_unit', '')
    material_type = request.GET.get('material_type', 'general')
    
    factor = ConversionFactor.get_factor(from_unit, to_unit, material_type)
    
    return JsonResponse({
        'success': factor is not None,
        'factor': float(factor) if factor else None,
        'from_unit': from_unit,
        'to_unit': to_unit,
        'material_type': material_type
    })


@login_required
def api_convert_value(request):
    """API: تحويل قيمة من وحدة لأخرى"""
    value = request.GET.get('value', '0')
    from_unit = request.GET.get('from_unit', '')
    to_unit = request.GET.get('to_unit', '')
    material_type = request.GET.get('material_type', 'general')
    
    try:
        result = ConversionFactor.convert(
            Decimal(value),
            from_unit,
            to_unit,
            material_type
        )
        
        return JsonResponse({
            'success': result is not None,
            'result': float(result) if result else None,
            'value': float(value),
            'from_unit': from_unit,
            'to_unit': to_unit
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_get_available_conversions(request):
    """API: الحصول على جميع التحويلات المتاحة لوحدة معينة"""
    from_unit = request.GET.get('from_unit', '')
    material_type = request.GET.get('material_type', 'general')
    
    # البحث عن معاملات خاصة بنوع المادة
    specific_factors = ConversionFactor.objects.filter(
        from_unit=from_unit,
        material_type=material_type,
        is_active=True
    ).values('to_unit', 'factor', 'description')
    
    # البحث عن معاملات عامة
    general_factors = ConversionFactor.objects.filter(
        from_unit=from_unit,
        material_type='general',
        is_active=True
    ).values('to_unit', 'factor', 'description')
    
    conversions = []
    for f in specific_factors:
        conversions.append({
            'to_unit': f['to_unit'],
            'factor': float(f['factor']),
            'description': f['description'],
            'type': 'specific'
        })
    
    for f in general_factors:
        # تجنب التكرار
        if not any(c['to_unit'] == f['to_unit'] for c in conversions):
            conversions.append({
                'to_unit': f['to_unit'],
                'factor': float(f['factor']),
                'description': f['description'],
                'type': 'general'
            })
    
    return JsonResponse({
        'success': True,
        'from_unit': from_unit,
        'material_type': material_type,
        'conversions': conversions
    })
