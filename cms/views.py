"""
Views لنظام إدارة المحتوى
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from .models import (
    Page, PageCategory, ContentBlock, Menu, MenuItem,
    MediaFile, PageComment
)


@login_required
def dashboard(request):
    """لوحة إدارة المحتوى"""
    pages = Page.objects.all()[:10]
    categories = PageCategory.objects.filter(parent=None)
    menus = Menu.objects.filter(is_active=True)
    media_count = MediaFile.objects.count()
    
    stats = {
        'pages': Page.objects.count(),
        'published': Page.objects.filter(status='published').count(),
        'draft': Page.objects.filter(status='draft').count(),
        'views': sum(p.view_count for p in Page.objects.all()),
    }
    
    return render(request, 'cms/dashboard.html', {
        'pages': pages,
        'categories': categories,
        'menus': menus,
        'media_count': media_count,
        'stats': stats,
    })


@staff_member_required
def page_list(request):
    """قائمة الصفحات"""
    pages = Page.objects.select_related('category', 'author').order_by('-created_at')
    
    # الفلترة
    status = request.GET.get('status')
    if status:
        pages = pages.filter(status=status)
    
    category = request.GET.get('category')
    if category:
        pages = pages.filter(category_id=category)
    
    search = request.GET.get('q')
    if search:
        pages = pages.filter(Q(title__icontains=search) | Q(content__icontains=search))
    
    categories = PageCategory.objects.all()
    
    return render(request, 'cms/page_list.html', {
        'pages': pages,
        'categories': categories,
    })


@staff_member_required
def page_create(request):
    """إنشاء صفحة"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            page = Page.objects.create(
                title=data.get('title', 'صفحة جديدة'),
                slug=data.get('slug', ''),
                category_id=data.get('category_id'),
                excerpt=data.get('excerpt', ''),
                content=data.get('content', ''),
                content_blocks=data.get('content_blocks', []),
                meta_title=data.get('meta_title', ''),
                meta_description=data.get('meta_description', ''),
                status=data.get('status', 'draft'),
                template=data.get('template', 'default'),
                author=request.user,
            )
            
            if data.get('status') == 'published':
                page.published_at = timezone.now()
                page.save()
            
            return JsonResponse({
                'success': True,
                'page_id': page.id,
                'slug': page.slug
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    categories = PageCategory.objects.all()
    blocks = ContentBlock.objects.filter(is_global=True)
    
    return render(request, 'cms/page_edit.html', {
        'categories': categories,
        'blocks': blocks,
        'page': None,
    })


@staff_member_required
def page_edit(request, page_id):
    """تحرير صفحة"""
    page = get_object_or_404(Page, id=page_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            page.title = data.get('title', page.title)
            page.slug = data.get('slug', page.slug)
            page.category_id = data.get('category_id')
            page.excerpt = data.get('excerpt', '')
            page.content = data.get('content', '')
            page.content_blocks = data.get('content_blocks', [])
            page.meta_title = data.get('meta_title', '')
            page.meta_description = data.get('meta_description', '')
            page.status = data.get('status', page.status)
            page.template = data.get('template', 'default')
            
            if data.get('status') == 'published' and not page.published_at:
                page.published_at = timezone.now()
            
            page.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    categories = PageCategory.objects.all()
    blocks = ContentBlock.objects.filter(is_global=True)
    
    return render(request, 'cms/page_edit.html', {
        'page': page,
        'categories': categories,
        'blocks': blocks,
    })


@staff_member_required
@require_http_methods(['POST'])
def page_delete(request, page_id):
    """حذف صفحة"""
    page = get_object_or_404(Page, id=page_id)
    page.delete()
    
    return JsonResponse({'success': True})


def page_view(request, slug):
    """عرض صفحة"""
    page = get_object_or_404(Page, slug=slug, status='published')
    
    # زيادة عدد المشاهدات
    page.view_count += 1
    page.save(update_fields=['view_count'])
    
    # التعليقات
    comments = page.page_comments.filter(is_approved=True, parent=None)
    
    return render(request, f'cms/templates/{page.template}.html', {
        'page': page,
        'comments': comments,
    })


@staff_member_required
def media_library(request):
    """مكتبة الوسائط"""
    if request.method == 'POST' and request.FILES:
        file = request.FILES.get('file')
        
        if file:
            # تحديد نوع الملف
            ext = file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                file_type = 'image'
            elif ext in ['mp4', 'webm', 'mov']:
                file_type = 'video'
            elif ext in ['mp3', 'wav', 'ogg']:
                file_type = 'audio'
            elif ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx']:
                file_type = 'document'
            else:
                file_type = 'other'
            
            media = MediaFile.objects.create(
                title=file.name,
                file=file,
                file_type=file_type,
                file_size=file.size,
                uploaded_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'media': {
                    'id': media.id,
                    'title': media.title,
                    'url': media.file.url,
                    'file_type': media.file_type
                }
            })
    
    media_files = MediaFile.objects.all()
    
    file_type = request.GET.get('type')
    if file_type:
        media_files = media_files.filter(file_type=file_type)
    
    return render(request, 'cms/media_library.html', {
        'media_files': media_files,
    })


@staff_member_required
def menu_manager(request):
    """إدارة القوائم"""
    menus = Menu.objects.all()
    
    return render(request, 'cms/menu_manager.html', {
        'menus': menus,
    })


@staff_member_required
@require_http_methods(['POST'])
def menu_save(request, menu_id=None):
    """حفظ القائمة"""
    try:
        data = json.loads(request.body)
        
        if menu_id:
            menu = get_object_or_404(Menu, id=menu_id)
        else:
            menu = Menu()
        
        menu.name = data.get('name')
        menu.slug = data.get('slug', '')
        menu.location = data.get('location', '')
        menu.save()
        
        # حذف العناصر القديمة
        menu.items.all().delete()
        
        # إضافة العناصر الجديدة
        for idx, item_data in enumerate(data.get('items', [])):
            MenuItem.objects.create(
                menu=menu,
                title=item_data.get('title'),
                link_type=item_data.get('link_type', 'url'),
                url=item_data.get('url', ''),
                page_id=item_data.get('page_id'),
                icon=item_data.get('icon', ''),
                order=idx,
            )
        
        return JsonResponse({'success': True, 'menu_id': menu.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def category_manager(request):
    """إدارة التصنيفات"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            cat = PageCategory.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
                icon=data.get('icon', ''),
                color=data.get('color', 'primary'),
                parent_id=data.get('parent_id'),
            )
            
            return JsonResponse({
                'success': True,
                'category': {
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    categories = PageCategory.objects.filter(parent=None)
    
    return render(request, 'cms/category_manager.html', {
        'categories': categories,
    })


@require_http_methods(['POST'])
def add_comment(request, page_id):
    """إضافة تعليق"""
    page = get_object_or_404(Page, id=page_id, allow_comments=True)
    
    try:
        data = json.loads(request.body)
        
        comment = PageComment.objects.create(
            page=page,
            user=request.user if request.user.is_authenticated else None,
            name=data.get('name', ''),
            email=data.get('email', ''),
            content=data.get('content', ''),
            parent_id=data.get('parent_id'),
            is_approved=request.user.is_authenticated
        )
        
        return JsonResponse({
            'success': True,
            'comment_id': comment.id,
            'is_approved': comment.is_approved
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
