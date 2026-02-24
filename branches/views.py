# branches/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from utils import handle_json_request
from .models import Branch, BranchType


def unified_dashboard(request):
    """لوحة تحكم موحدة للفروع والمعارض"""
    
    # إحصائيات حسب النوع
    stats = {
        'total': Branch.objects.filter(is_active=True).count(),
        'branches': Branch.objects.filter(branch_type=BranchType.BRANCH, is_active=True).count(),
        'showrooms': Branch.objects.filter(branch_type=BranchType.SHOWROOM, is_active=True).count(),
        'warehouses': Branch.objects.filter(branch_type=BranchType.WAREHOUSE, is_active=True).count(),
        'outlets': Branch.objects.filter(branch_type=BranchType.OUTLET, is_active=True).count(),
    }
    
    # آخر المواقع المضافة
    recent_locations = Branch.objects.order_by('-created_at')[:5]
    
    # المواقع حسب المدينة
    by_city = Branch.objects.filter(is_active=True).values('city').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'recent_locations': recent_locations,
        'by_city': by_city,
        'branch_types': BranchType.choices,
    }
    return render(request, 'branches/unified_dashboard.html', context)


def unified_list(request):
    """قائمة جميع الفروع والمعارض"""
    
    queryset = Branch.objects.all()
    
    # تصفية حسب النوع
    branch_type = request.GET.get('type')
    if branch_type:
        queryset = queryset.filter(branch_type=branch_type)
    
    # تصفية حسب الحالة
    status = request.GET.get('status')
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)
    
    # البحث
    search = request.GET.get('q')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(city__icontains=search)
        )
    
    # ترتيب
    order = request.GET.get('order', 'name')
    queryset = queryset.order_by(order)
    
    # pagination
    paginator = Paginator(queryset, 12)
    page = request.GET.get('page', 1)
    locations = paginator.get_page(page)
    
    context = {
        'locations': locations,
        'branch_types': BranchType.choices,
        'current_type': branch_type,
        'current_status': status,
        'search_query': search or '',
    }
    return render(request, 'branches/unified_list.html', context)


@handle_json_request
def create_location(request):
    """إنشاء فرع أو معرض جديد"""
    
    if request.method == 'POST':
        try:
            branch = Branch(
                name=request.POST.get('name'),
                code=request.POST.get('code'),
                branch_type=request.POST.get('branch_type', 'branch'),
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                region=request.POST.get('region', ''),
                phone=request.POST.get('phone', ''),
                mobile=request.POST.get('mobile', ''),
                email=request.POST.get('email', ''),
                is_active=request.POST.get('is_active') == 'on',
                is_main=request.POST.get('is_main') == 'on',
                can_sell=request.POST.get('can_sell') == 'on',
                can_purchase=request.POST.get('can_purchase') == 'on',
                has_inventory=request.POST.get('has_inventory') == 'on',
                notes=request.POST.get('notes', ''),
            )
            
            parent_id = request.POST.get('parent_branch')
            if parent_id:
                branch.parent_branch_id = parent_id
            
            branch.save()
            messages.success(request, f'تم إنشاء {branch.get_branch_type_display()} "{branch.name}" بنجاح')
            return redirect('branches:location_detail', pk=branch.pk)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'branch_types': BranchType.choices,
        'parent_branches': Branch.objects.filter(is_active=True),
    }
    return render(request, 'branches/create_location.html', context)


def location_detail(request, pk):
    """عرض تفاصيل فرع أو معرض"""
    
    location = get_object_or_404(Branch, pk=pk)
    sub_locations = location.get_all_children()
    
    context = {
        'location': location,
        'sub_locations': sub_locations,
    }
    return render(request, 'branches/location_detail.html', context)


def edit_location(request, pk):
    """تعديل فرع أو معرض"""
    
    location = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        try:
            location.name = request.POST.get('name')
            location.code = request.POST.get('code')
            location.branch_type = request.POST.get('branch_type')
            location.address = request.POST.get('address', '')
            location.city = request.POST.get('city', '')
            location.region = request.POST.get('region', '')
            location.phone = request.POST.get('phone', '')
            location.mobile = request.POST.get('mobile', '')
            location.email = request.POST.get('email', '')
            location.is_active = request.POST.get('is_active') == 'on'
            location.is_main = request.POST.get('is_main') == 'on'
            location.can_sell = request.POST.get('can_sell') == 'on'
            location.can_purchase = request.POST.get('can_purchase') == 'on'
            location.has_inventory = request.POST.get('has_inventory') == 'on'
            location.notes = request.POST.get('notes', '')
            
            parent_id = request.POST.get('parent_branch')
            location.parent_branch_id = parent_id if parent_id else None
            
            location.save()
            messages.success(request, f'تم تحديث "{location.name}" بنجاح')
            return redirect('branches:location_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
    
    context = {
        'location': location,
        'branch_types': BranchType.choices,
        'parent_branches': Branch.objects.filter(is_active=True).exclude(pk=pk),
    }
    return render(request, 'branches/edit_location.html', context)


def toggle_status(request, pk):
    """تفعيل/تعطيل فرع أو معرض"""
    
    if request.method == 'POST':
        location = get_object_or_404(Branch, pk=pk)
        location.is_active = not location.is_active
        location.save()
        
        status = 'تفعيل' if location.is_active else 'تعطيل'
        messages.success(request, f'تم {status} "{location.name}"')
        
    return redirect('branches:unified_list')


def set_current_location(request):
    """تعيين الفرع الحالي للمستخدم"""
    
    if request.method == 'POST':
        location_id = request.POST.get('location_id')
        if location_id:
            request.session['current_location_id'] = int(location_id)
            location = get_object_or_404(Branch, pk=location_id)
            messages.success(request, f'تم التبديل إلى {location.name}')
    
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
    return redirect(next_url)


# API Views
def api_locations_list(request):
    """API: قائمة المواقع"""
    
    branch_type = request.GET.get('type')
    queryset = Branch.objects.filter(is_active=True)
    
    if branch_type:
        queryset = queryset.filter(branch_type=branch_type)
    
    data = list(queryset.values('id', 'name', 'code', 'branch_type', 'city'))
    return JsonResponse({'locations': data})


def api_location_detail(request, pk):
    """API: تفاصيل موقع"""
    
    location = get_object_or_404(Branch, pk=pk)
    data = {
        'id': location.id,
        'name': location.name,
        'code': location.code,
        'branch_type': location.branch_type,
        'city': location.city,
        'address': location.address,
        'phone': location.phone,
        'is_active': location.is_active,
    }
    return JsonResponse(data)
