"""
Views للدردشة الداخلية
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max, OuterRef, Subquery
from django.utils import timezone
from django.core.paginator import Paginator

from .models import (
    ChatRoom, ChatParticipant, Message, MessageReaction,
    MessageRead, ChatSettings, OnlineStatus
)

User = get_user_model()


@login_required
def chat_home(request):
    """الصفحة الرئيسية للدردشة"""
    # الحصول على الغرف
    rooms = ChatRoom.objects.filter(
        participants=request.user,
        is_archived=False
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count(
            'messages',
            filter=Q(
                messages__created_at__gt=Subquery(
                    ChatParticipant.objects.filter(
                        room=OuterRef('pk'),
                        user=request.user
                    ).values('last_read_at')[:1]
                )
            ) & ~Q(messages__sender=request.user)
        )
    ).order_by('-last_message_time')
    
    # الموظفون المتاحون
    online_users = User.objects.filter(
        online_status__is_online=True
    ).exclude(id=request.user.id)[:20]
    
    return render(request, 'internal_chat/home.html', {
        'rooms': rooms,
        'online_users': online_users,
    })


@login_required
def chat_room(request, room_uuid):
    """غرفة الدردشة"""
    room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=request.user)
    
    # تحديث آخر قراءة
    participant = ChatParticipant.objects.get(room=room, user=request.user)
    participant.last_read_at = timezone.now()
    participant.save()
    
    # الرسائل
    messages = room.messages.filter(is_deleted=False).order_by('-created_at')[:50]
    messages = reversed(list(messages))
    
    return render(request, 'internal_chat/room.html', {
        'room': room,
        'messages': messages,
        'participant': participant,
    })


@login_required
def start_private_chat(request, user_id):
    """بدء محادثة خاصة"""
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        return redirect('internal_chat:home')
    
    # البحث عن محادثة موجودة
    existing_room = ChatRoom.objects.filter(
        room_type='private',
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_room:
        return redirect('internal_chat:room', room_uuid=existing_room.uuid)
    
    # إنشاء محادثة جديدة
    room = ChatRoom.objects.create(
        room_type='private',
        created_by=request.user
    )
    ChatParticipant.objects.create(room=room, user=request.user, role='owner')
    ChatParticipant.objects.create(room=room, user=other_user)
    
    return redirect('internal_chat:room', room_uuid=room.uuid)


@login_required
@require_http_methods(['POST'])
def create_group(request):
    """إنشاء مجموعة"""
    try:
        data = json.loads(request.body)
        
        room = ChatRoom.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            room_type='group',
            created_by=request.user
        )
        
        # إضافة المنشئ
        ChatParticipant.objects.create(room=room, user=request.user, role='owner')
        
        # إضافة المشاركين
        for user_id in data.get('participants', []):
            user = User.objects.filter(id=user_id).first()
            if user:
                ChatParticipant.objects.create(room=room, user=user)
        
        # رسالة نظام
        Message.objects.create(
            room=room,
            sender=request.user,
            message_type='system',
            content=f'أنشأ {request.user.get_full_name() or request.user.username} المجموعة'
        )
        
        return JsonResponse({
            'success': True,
            'room_uuid': str(room.uuid)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def send_message(request, room_uuid):
    """إرسال رسالة"""
    room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=request.user)
    
    try:
        content = request.POST.get('content', '')
        message_type = request.POST.get('type', 'text')
        reply_to_id = request.POST.get('reply_to')
        
        message = Message.objects.create(
            room=room,
            sender=request.user,
            message_type=message_type,
            content=content,
            reply_to_id=reply_to_id if reply_to_id else None
        )
        
        # المرفق
        if 'attachment' in request.FILES:
            file = request.FILES['attachment']
            message.attachment = file
            message.attachment_name = file.name
            message.attachment_size = file.size
            
            if file.content_type.startswith('image'):
                message.message_type = 'image'
            elif file.content_type.startswith('audio'):
                message.message_type = 'audio'
            elif file.content_type.startswith('video'):
                message.message_type = 'video'
            else:
                message.message_type = 'file'
            
            message.save()
        
        # تحديث الغرفة
        room.save()  # لتحديث updated_at
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': str(message.uuid),
                'content': message.content,
                'type': message.message_type,
                'sender': message.sender.get_full_name() or message.sender.username,
                'sender_id': message.sender.id,
                'created_at': message.created_at.isoformat(),
                'attachment': message.attachment.url if message.attachment else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_messages(request, room_uuid):
    """الحصول على الرسائل"""
    room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=request.user)
    
    before = request.GET.get('before')
    limit = int(request.GET.get('limit', 50))
    
    messages = room.messages.filter(is_deleted=False)
    
    if before:
        messages = messages.filter(created_at__lt=before)
    
    messages = messages.order_by('-created_at')[:limit]
    
    data = [{
        'id': str(m.uuid),
        'content': m.content,
        'type': m.message_type,
        'sender': m.sender.get_full_name() or m.sender.username if m.sender else 'النظام',
        'sender_id': m.sender.id if m.sender else None,
        'created_at': m.created_at.isoformat(),
        'is_edited': m.is_edited,
        'attachment': m.attachment.url if m.attachment else None,
        'attachment_name': m.attachment_name,
        'reactions': list(m.reactions.values('emoji').annotate(count=Count('id'))),
    } for m in reversed(list(messages))]
    
    return JsonResponse({'success': True, 'messages': data})


@login_required
@require_http_methods(['POST'])
def add_reaction(request, message_uuid):
    """إضافة تفاعل"""
    message = get_object_or_404(Message, uuid=message_uuid)
    
    # التحقق من أن المستخدم مشارك
    if not message.room.participants.filter(id=request.user.id).exists():
        return JsonResponse({'success': False, 'error': 'غير مصرح'})
    
    try:
        data = json.loads(request.body)
        emoji = data.get('emoji')
        
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji
        )
        
        if not created:
            reaction.delete()
            return JsonResponse({'success': True, 'action': 'removed'})
        
        return JsonResponse({'success': True, 'action': 'added'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['DELETE'])
def delete_message(request, message_uuid):
    """حذف رسالة"""
    message = get_object_or_404(Message, uuid=message_uuid, sender=request.user)
    
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.content = 'تم حذف هذه الرسالة'
    message.save()
    
    return JsonResponse({'success': True})


@login_required
def search_users(request):
    """البحث عن مستخدمين"""
    q = request.GET.get('q', '')
    
    if len(q) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=q) |
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(email__icontains=q)
    ).exclude(id=request.user.id)[:10]
    
    data = [{
        'id': u.id,
        'name': u.get_full_name() or u.username,
        'email': u.email,
        'is_online': hasattr(u, 'online_status') and u.online_status.is_online
    } for u in users]
    
    return JsonResponse({'users': data})


@login_required
@require_http_methods(['POST'])
def update_online_status(request):
    """تحديث حالة الاتصال"""
    try:
        data = json.loads(request.body)
        is_online = data.get('is_online', True)
        
        status, _ = OnlineStatus.objects.get_or_create(user=request.user)
        status.is_online = is_online
        status.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
