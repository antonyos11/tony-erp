"""
Views للوحة التحكم المخصصة
"""

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import DashboardLayout, Widget, DashboardWidget, QuickActionWidget
from .services import DashboardService, WidgetDataService


@login_required
def dashboard(request):
    """لوحة التحكم الرئيسية"""
    layout = DashboardService.get_user_dashboard(request.user)
    available_widgets = DashboardService.get_available_widgets(request.user)
    quick_actions = QuickActionWidget.objects.filter(user=request.user, is_active=True)
    
    # جلب بيانات الويدجتس
    widgets_data = []
    for dw in layout.widgets.filter(is_visible=True).select_related('widget'):
        data = WidgetDataService.get_widget_data(dw.widget, request.user)
        widgets_data.append({
            'dashboard_widget': dw,
            'widget': dw.widget,
            'data': data
        })
    
    return render(request, 'custom_dashboard/dashboard.html', {
        'layout': layout,
        'widgets_data': widgets_data,
        'available_widgets': available_widgets,
        'quick_actions': quick_actions,
    })


@login_required
def layouts_list(request):
    """قائمة التخطيطات"""
    layouts = DashboardLayout.objects.filter(user=request.user)
    
    return render(request, 'custom_dashboard/layouts.html', {
        'layouts': layouts,
    })


@login_required
@require_http_methods(['POST'])
def create_layout(request):
    """إنشاء تخطيط جديد"""
    try:
        data = json.loads(request.body)
        
        layout = DashboardLayout.objects.create(
            user=request.user,
            name=data.get('name', 'تخطيط جديد'),
            description=data.get('description', ''),
            columns=data.get('columns', 3)
        )
        
        return JsonResponse({
            'success': True,
            'layout_id': layout.id
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['POST'])
def update_layout(request, layout_id):
    """تحديث تخطيط"""
    layout = get_object_or_404(DashboardLayout, id=layout_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        
        layout.name = data.get('name', layout.name)
        layout.columns = data.get('columns', layout.columns)
        layout.layout_config = data.get('layout_config', layout.layout_config)
        layout.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['POST'])
def set_default_layout(request, layout_id):
    """تعيين التخطيط كافتراضي"""
    layout = get_object_or_404(DashboardLayout, id=layout_id, user=request.user)
    layout.is_default = True
    layout.save()
    
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['DELETE'])
def delete_layout(request, layout_id):
    """حذف تخطيط"""
    layout = get_object_or_404(DashboardLayout, id=layout_id, user=request.user)
    
    if layout.is_default:
        return JsonResponse({
            'success': False,
            'error': 'لا يمكن حذف التخطيط الافتراضي'
        })
    
    layout.delete()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def add_widget(request, layout_id):
    """إضافة ويدجت للتخطيط"""
    layout = get_object_or_404(DashboardLayout, id=layout_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        widget = get_object_or_404(Widget, id=data.get('widget_id'))
        
        dw = DashboardWidget.objects.create(
            layout=layout,
            widget=widget,
            position_x=data.get('position_x', 0),
            position_y=data.get('position_y', 0),
            width=data.get('width', widget.min_width),
            height=data.get('height', widget.min_height)
        )
        
        return JsonResponse({
            'success': True,
            'dashboard_widget_id': dw.id
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['POST'])
def update_widget_position(request, widget_id):
    """تحديث موقع ويدجت"""
    dw = get_object_or_404(
        DashboardWidget,
        id=widget_id,
        layout__user=request.user
    )
    
    try:
        data = json.loads(request.body)
        
        dw.position_x = data.get('position_x', dw.position_x)
        dw.position_y = data.get('position_y', dw.position_y)
        dw.width = data.get('width', dw.width)
        dw.height = data.get('height', dw.height)
        dw.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['POST'])
def toggle_widget(request, widget_id):
    """إظهار/إخفاء ويدجت"""
    dw = get_object_or_404(
        DashboardWidget,
        id=widget_id,
        layout__user=request.user
    )
    
    dw.is_visible = not dw.is_visible
    dw.save()
    
    return JsonResponse({
        'success': True,
        'is_visible': dw.is_visible
    })


@login_required
@require_http_methods(['DELETE'])
def remove_widget(request, widget_id):
    """إزالة ويدجت من التخطيط"""
    dw = get_object_or_404(
        DashboardWidget,
        id=widget_id,
        layout__user=request.user
    )
    
    dw.delete()
    return JsonResponse({'success': True})


@login_required
def get_widget_data(request, widget_id):
    """الحصول على بيانات ويدجت"""
    dw = get_object_or_404(
        DashboardWidget,
        id=widget_id,
        layout__user=request.user
    )
    
    data = WidgetDataService.get_widget_data(dw.widget, request.user)
    
    return JsonResponse({
        'success': True,
        'data': data
    })


@login_required
def available_widgets(request):
    """الويدجتس المتاحة"""
    widgets = DashboardService.get_available_widgets(request.user)
    
    return JsonResponse({
        'widgets': [
            {
                'id': w.id,
                'name': w.name,
                'type': w.widget_type,
                'icon': w.icon,
                'color': w.color,
                'description': w.description,
                'default_size': w.default_size
            }
            for w in widgets
        ]
    })


@login_required
@require_http_methods(['POST'])
def save_layout_positions(request, layout_id):
    """حفظ مواقع الويدجتس"""
    layout = get_object_or_404(DashboardLayout, id=layout_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        positions = data.get('positions', [])
        
        for pos in positions:
            DashboardWidget.objects.filter(
                id=pos['id'],
                layout=layout
            ).update(
                position_x=pos.get('x', 0),
                position_y=pos.get('y', 0),
                width=pos.get('width', 1),
                height=pos.get('height', 1)
            )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# Quick Actions

@login_required
def quick_actions_list(request):
    """قائمة الإجراءات السريعة"""
    actions = QuickActionWidget.objects.filter(user=request.user)
    
    return render(request, 'custom_dashboard/quick_actions.html', {
        'actions': actions,
    })


@login_required
@require_http_methods(['POST'])
def create_quick_action(request):
    """إنشاء إجراء سريع"""
    try:
        data = json.loads(request.body)
        
        action = QuickActionWidget.objects.create(
            user=request.user,
            name=data.get('name'),
            icon=data.get('icon', 'fas fa-star'),
            color=data.get('color', 'primary'),
            url=data.get('url'),
            description=data.get('description', '')
        )
        
        return JsonResponse({
            'success': True,
            'action_id': action.id
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(['DELETE'])
def delete_quick_action(request, action_id):
    """حذف إجراء سريع"""
    action = get_object_or_404(QuickActionWidget, id=action_id, user=request.user)
    action.delete()
    
    return JsonResponse({'success': True})
