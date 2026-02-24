# branches/context_processors.py
from .models import Branch, BranchType


def current_location(request):
    """Context processor للفرع الحالي"""
    
    current_location = None
    all_locations = []
    
    try:
        # الحصول على الفرع الحالي من الجلسة
        location_id = request.session.get('current_location_id')
        if location_id:
            current_location = Branch.objects.filter(pk=location_id, is_active=True).first()
        
        # إذا لم يكن هناك فرع محدد، نختار الفرع الرئيسي
        if not current_location:
            current_location = Branch.objects.filter(is_main=True, is_active=True).first()
        
        # إذا لم يوجد فرع رئيسي، نختار أول فرع نشط
        if not current_location:
            current_location = Branch.objects.filter(is_active=True).first()
        
        # جميع المواقع النشطة للـ dropdown
        all_locations = Branch.objects.filter(is_active=True).order_by('branch_type', 'name')
    except:
        pass
    
    return {
        'current_location': current_location,
        'all_locations': all_locations,
        'branch_types': BranchType.choices,
    }


def location_permissions(request):
    """Context processor لصلاحيات الموقع"""
    
    permissions = {
        'can_switch_location': True,
        'can_manage_locations': request.user.is_staff if hasattr(request, 'user') else False,
        'can_add_location': request.user.is_staff if hasattr(request, 'user') else False,
    }
    
    return {'location_permissions': permissions}
