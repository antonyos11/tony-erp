"""
Views لمكالمات الفيديو
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import VideoRoom, VideoParticipant, VideoRecording, VideoMessage

User = get_user_model()


@login_required
def dashboard(request):
    """لوحة مكالمات الفيديو"""
    my_rooms = VideoRoom.objects.filter(host=request.user).order_by('-created_at')[:10]
    upcoming = VideoRoom.objects.filter(
        participants=request.user,
        scheduled_at__gte=timezone.now()
    ).order_by('scheduled_at')[:5]
    
    return render(request, 'video_calls/dashboard.html', {
        'my_rooms': my_rooms,
        'upcoming': upcoming,
    })


@login_required
def create_room(request):
    """إنشاء غرفة"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            room = VideoRoom.objects.create(
                name=data.get('name', f"اجتماع {timezone.now().strftime('%Y/%m/%d')}"),
                description=data.get('description', ''),
                room_type=data.get('room_type', 'instant'),
                host=request.user,
                max_participants=data.get('max_participants', 10),
                is_recording_enabled=data.get('recording', False),
                scheduled_at=data.get('scheduled_at'),
                duration_minutes=data.get('duration', 60),
                password=data.get('password', ''),
            )
            
            # إضافة المضيف كمشارك
            VideoParticipant.objects.create(
                room=room,
                user=request.user,
                role='host'
            )
            
            # إضافة المشاركين
            for user_id in data.get('participants', []):
                user = User.objects.filter(id=user_id).first()
                if user:
                    VideoParticipant.objects.create(room=room, user=user)
            
            return JsonResponse({
                'success': True,
                'room_uuid': str(room.uuid),
                'join_url': room.join_url
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    users = User.objects.exclude(id=request.user.id)[:50]
    
    return render(request, 'video_calls/create.html', {
        'users': users,
    })


@login_required
def join_room(request, room_uuid):
    """الانضمام لغرفة"""
    room = get_object_or_404(VideoRoom, uuid=room_uuid)
    
    # التحقق من كلمة المرور
    if room.password:
        if request.method == 'POST':
            password = request.POST.get('password')
            if password != room.password:
                return render(request, 'video_calls/password.html', {
                    'room': room,
                    'error': 'كلمة المرور غير صحيحة'
                })
        else:
            # إذا لم يكن مشاركاً، طلب كلمة المرور
            if not room.participants.filter(id=request.user.id).exists():
                return render(request, 'video_calls/password.html', {
                    'room': room,
                })
    
    # إضافة أو تحديث المشارك
    participant, created = VideoParticipant.objects.get_or_create(
        room=room,
        user=request.user,
        defaults={'role': 'participant'}
    )
    participant.is_connected = True
    participant.joined_at = timezone.now()
    participant.save()
    
    # تفعيل الغرفة
    if not room.started_at:
        room.started_at = timezone.now()
        room.save()
    
    return render(request, 'video_calls/room.html', {
        'room': room,
        'participant': participant,
        'is_host': room.host == request.user,
    })


@login_required
@require_http_methods(['POST'])
def leave_room(request, room_uuid):
    """مغادرة الغرفة"""
    room = get_object_or_404(VideoRoom, uuid=room_uuid)
    
    participant = VideoParticipant.objects.filter(
        room=room,
        user=request.user
    ).first()
    
    if participant:
        participant.is_connected = False
        participant.left_at = timezone.now()
        participant.save()
    
    # إنهاء الغرفة إذا كان المضيف
    if room.host == request.user:
        room.is_active = False
        room.ended_at = timezone.now()
        room.save()
    
    return JsonResponse({'success': True})


@login_required
@require_http_methods(['POST'])
def toggle_media(request, room_uuid):
    """تبديل الصوت/الفيديو"""
    room = get_object_or_404(VideoRoom, uuid=room_uuid)
    
    try:
        data = json.loads(request.body)
        
        participant = VideoParticipant.objects.get(room=room, user=request.user)
        
        if 'muted' in data:
            participant.is_muted = data['muted']
        if 'video_on' in data:
            participant.is_video_on = data['video_on']
        if 'screen_sharing' in data:
            participant.is_screen_sharing = data['screen_sharing']
        
        participant.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def send_message(request, room_uuid):
    """إرسال رسالة"""
    room = get_object_or_404(VideoRoom, uuid=room_uuid)
    
    if not room.is_chat_enabled:
        return JsonResponse({'success': False, 'error': 'الدردشة معطلة'})
    
    try:
        data = json.loads(request.body)
        
        message = VideoMessage.objects.create(
            room=room,
            sender=request.user,
            content=data.get('content', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'sender': request.user.get_full_name() or request.user.username,
                'content': message.content,
                'created_at': message.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_room_status(request, room_uuid):
    """حالة الغرفة"""
    room = get_object_or_404(VideoRoom, uuid=room_uuid)
    
    participants = room.videoparticipant_set.filter(is_connected=True)
    
    return JsonResponse({
        'is_active': room.is_active,
        'participants': [{
            'id': p.user.id,
            'name': p.user.get_full_name() or p.user.username,
            'role': p.role,
            'is_muted': p.is_muted,
            'is_video_on': p.is_video_on,
            'is_screen_sharing': p.is_screen_sharing,
        } for p in participants]
    })
