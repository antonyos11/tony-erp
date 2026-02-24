"""
Views للمستندات التعاونية
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import (
    Document, DocumentFolder, DocumentCollaborator,
    DocumentVersion, DocumentComment, DocumentActivity
)

User = get_user_model()


@login_required
def dashboard(request):
    """لوحة المستندات"""
    # المستندات الأخيرة
    recent = Document.objects.filter(
        Q(owner=request.user) | Q(collaborators=request.user)
    ).distinct().order_by('-updated_at')[:10]
    
    # المستندات المفضلة
    starred = Document.objects.filter(
        owner=request.user,
        is_starred=True
    ).order_by('-updated_at')[:5]
    
    # المجلدات
    folders = DocumentFolder.objects.filter(
        owner=request.user,
        parent=None
    ).order_by('name')
    
    return render(request, 'collaborative_docs/dashboard.html', {
        'recent': recent,
        'starred': starred,
        'folders': folders,
    })


@login_required
def create_document(request):
    """إنشاء مستند جديد"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            doc = Document.objects.create(
                title=data.get('title', 'مستند جديد'),
                doc_type=data.get('doc_type', 'document'),
                owner=request.user,
                folder_id=data.get('folder_id'),
            )
            
            # تسجيل النشاط
            DocumentActivity.objects.create(
                document=doc,
                user=request.user,
                activity_type='created'
            )
            
            return JsonResponse({
                'success': True,
                'uuid': str(doc.uuid),
                'edit_url': doc.edit_url
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'collaborative_docs/create.html')


@login_required
def edit_document(request, doc_uuid):
    """تحرير المستند"""
    doc = get_object_or_404(Document, uuid=doc_uuid)
    
    # التحقق من الصلاحية
    is_owner = doc.owner == request.user
    collaborator = DocumentCollaborator.objects.filter(
        document=doc,
        user=request.user
    ).first()
    
    can_edit = is_owner or (collaborator and collaborator.permission in ['edit', 'admin'])
    can_comment = is_owner or (collaborator and collaborator.permission in ['comment', 'edit', 'admin'])
    
    if not is_owner and not collaborator and not doc.is_public:
        return render(request, 'collaborative_docs/no_access.html')
    
    # تسجيل المشاهدة
    doc.view_count += 1
    doc.save(update_fields=['view_count'])
    
    DocumentActivity.objects.create(
        document=doc,
        user=request.user,
        activity_type='viewed'
    )
    
    # الحصول على التعليقات
    comments = doc.comments.filter(parent=None).order_by('created_at')
    
    # المتعاونون
    collaborators = doc.documentcollaborator_set.select_related('user')
    
    return render(request, 'collaborative_docs/edit.html', {
        'document': doc,
        'is_owner': is_owner,
        'can_edit': can_edit,
        'can_comment': can_comment,
        'comments': comments,
        'collaborators': collaborators,
    })


@login_required
@require_http_methods(['POST'])
def save_document(request, doc_uuid):
    """حفظ المستند"""
    doc = get_object_or_404(Document, uuid=doc_uuid)
    
    try:
        data = json.loads(request.body)
        
        # حفظ نسخة سابقة
        version_count = doc.versions.count()
        DocumentVersion.objects.create(
            document=doc,
            version_number=version_count + 1,
            content=doc.content,
            content_json=doc.content_json,
            created_by=request.user
        )
        
        # تحديث المستند
        doc.title = data.get('title', doc.title)
        doc.content = data.get('content', '')
        doc.content_json = data.get('content_json', {})
        doc.last_edited_by = request.user
        doc.save()
        
        # تسجيل النشاط
        DocumentActivity.objects.create(
            document=doc,
            user=request.user,
            activity_type='edited'
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def share_document(request, doc_uuid):
    """مشاركة المستند"""
    doc = get_object_or_404(Document, uuid=doc_uuid, owner=request.user)
    
    try:
        data = json.loads(request.body)
        
        for user_id in data.get('users', []):
            user = User.objects.filter(id=user_id).first()
            if user and user != request.user:
                DocumentCollaborator.objects.update_or_create(
                    document=doc,
                    user=user,
                    defaults={
                        'permission': data.get('permission', 'view'),
                        'added_by': request.user
                    }
                )
        
        # تسجيل النشاط
        DocumentActivity.objects.create(
            document=doc,
            user=request.user,
            activity_type='shared'
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def add_comment(request, doc_uuid):
    """إضافة تعليق"""
    doc = get_object_or_404(Document, uuid=doc_uuid)
    
    try:
        data = json.loads(request.body)
        
        comment = DocumentComment.objects.create(
            document=doc,
            user=request.user,
            content=data.get('content', ''),
            position_start=data.get('position_start'),
            position_end=data.get('position_end'),
            selected_text=data.get('selected_text', ''),
            parent_id=data.get('parent_id')
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': request.user.get_full_name() or request.user.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_versions(request, doc_uuid):
    """الحصول على النسخ"""
    doc = get_object_or_404(Document, uuid=doc_uuid)
    
    versions = doc.versions.all()[:20]
    
    return JsonResponse({
        'versions': [{
            'id': v.id,
            'version_number': v.version_number,
            'created_by': v.created_by.get_full_name() if v.created_by else 'غير معروف',
            'created_at': v.created_at.isoformat()
        } for v in versions]
    })


@login_required
@require_http_methods(['POST'])
def restore_version(request, doc_uuid, version_id):
    """استعادة نسخة"""
    doc = get_object_or_404(Document, uuid=doc_uuid, owner=request.user)
    version = get_object_or_404(DocumentVersion, id=version_id, document=doc)
    
    # حفظ النسخة الحالية
    version_count = doc.versions.count()
    DocumentVersion.objects.create(
        document=doc,
        version_number=version_count + 1,
        content=doc.content,
        content_json=doc.content_json,
        created_by=request.user,
        description='قبل الاستعادة'
    )
    
    # استعادة النسخة
    doc.content = version.content
    doc.content_json = version.content_json
    doc.last_edited_by = request.user
    doc.save()
    
    DocumentActivity.objects.create(
        document=doc,
        user=request.user,
        activity_type='restored',
        description=f'استعادة النسخة {version.version_number}'
    )
    
    return JsonResponse({'success': True})


@login_required
def folder_contents(request, folder_id=None):
    """محتويات المجلد"""
    if folder_id:
        folder = get_object_or_404(DocumentFolder, id=folder_id)
        subfolders = folder.subfolders.filter(owner=request.user)
        documents = folder.documents.filter(
            Q(owner=request.user) | Q(collaborators=request.user)
        ).distinct()
    else:
        folder = None
        subfolders = DocumentFolder.objects.filter(owner=request.user, parent=None)
        documents = Document.objects.filter(
            Q(owner=request.user) | Q(collaborators=request.user),
            folder=None
        ).distinct()
    
    return JsonResponse({
        'folder': {'id': folder.id, 'name': folder.name} if folder else None,
        'subfolders': [{'id': f.id, 'name': f.name} for f in subfolders],
        'documents': [{
            'uuid': str(d.uuid),
            'title': d.title,
            'doc_type': d.doc_type,
            'updated_at': d.updated_at.isoformat()
        } for d in documents]
    })


@login_required
@require_http_methods(['POST'])
def create_folder(request):
    """إنشاء مجلد"""
    try:
        data = json.loads(request.body)
        
        folder = DocumentFolder.objects.create(
            name=data.get('name', 'مجلد جديد'),
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            owner=request.user
        )
        
        return JsonResponse({
            'success': True,
            'folder': {
                'id': folder.id,
                'name': folder.name
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
