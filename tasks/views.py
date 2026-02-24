"""
Views لنظام المهام
"""

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count

from .models import (
    Task, TaskList, TaskCategory, SubTask, TaskComment,
    TaskAttachment, Reminder, TaskHistory
)


@login_required
def dashboard(request):
    """لوحة المهام"""
    user = request.user
    
    # المهام
    my_tasks = Task.objects.filter(
        Q(assigned_to=user) | Q(created_by=user),
        is_archived=False
    )
    
    # إحصائيات
    stats = {
        'total': my_tasks.count(),
        'pending': my_tasks.filter(status='pending').count(),
        'in_progress': my_tasks.filter(status='in_progress').count(),
        'completed': my_tasks.filter(status='completed').count(),
        'overdue': my_tasks.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress']).count(),
    }
    
    # المهام القادمة
    upcoming = my_tasks.filter(
        due_date__gte=timezone.now(),
        status__in=['pending', 'in_progress']
    ).order_by('due_date')[:10]
    
    # المهام المتأخرة
    overdue = my_tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).order_by('due_date')[:5]
    
    # القوائم
    task_lists = TaskList.objects.filter(
        Q(owner=user) | Q(shared_with=user)
    ).distinct()
    
    # التذكيرات القادمة
    reminders = Reminder.objects.filter(
        user=user,
        is_dismissed=False,
        remind_at__gte=timezone.now()
    ).order_by('remind_at')[:5]
    
    return render(request, 'tasks/dashboard.html', {
        'stats': stats,
        'upcoming_tasks': upcoming,
        'overdue_tasks': overdue,
        'task_lists': task_lists,
        'reminders': reminders,
    })


@login_required
def task_list(request):
    """قائمة المهام"""
    user = request.user
    
    tasks = Task.objects.filter(
        Q(assigned_to=user) | Q(created_by=user),
        is_archived=False
    )
    
    # الفلترة
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    category = request.GET.get('category')
    list_id = request.GET.get('list')
    search = request.GET.get('q')
    
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if category:
        tasks = tasks.filter(category_id=category)
    if list_id:
        tasks = tasks.filter(task_list_id=list_id)
    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    tasks = tasks.order_by('-is_pinned', 'due_date', '-priority')
    
    categories = TaskCategory.objects.filter(is_active=True)
    task_lists = TaskList.objects.filter(Q(owner=user) | Q(shared_with=user)).distinct()
    
    return render(request, 'tasks/list.html', {
        'tasks': tasks,
        'categories': categories,
        'task_lists': task_lists,
    })


@login_required
def task_detail(request, task_id):
    """تفاصيل المهمة"""
    task = get_object_or_404(Task, id=task_id)
    
    # التحقق من الصلاحية
    if task.created_by != request.user and task.assigned_to != request.user:
        if not (task.task_list and request.user in task.task_list.shared_with.all()):
            messages.error(request, 'ليس لديك صلاحية لعرض هذه المهمة')
            return redirect('tasks:dashboard')
    
    subtasks = task.subtasks.all()
    comments = task.comments.select_related('user').all()
    attachments = task.attachments.all()
    history = task.history.select_related('user').all()[:10]
    
    return render(request, 'tasks/detail.html', {
        'task': task,
        'subtasks': subtasks,
        'comments': comments,
        'attachments': attachments,
        'history': history,
    })


@login_required
def task_create(request):
    """إنشاء مهمة"""
    if request.method == 'POST':
        task = Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            created_by=request.user,
            priority=request.POST.get('priority', 'medium'),
            status='pending'
        )
        
        # تاريخ الاستحقاق
        due_date = request.POST.get('due_date')
        if due_date:
            task.due_date = due_date
        
        # الفئة
        category_id = request.POST.get('category')
        if category_id:
            task.category_id = category_id
        
        # القائمة
        list_id = request.POST.get('task_list')
        if list_id:
            task.task_list_id = list_id
        
        # المُسند إليه
        assigned_to = request.POST.get('assigned_to')
        if assigned_to:
            task.assigned_to_id = assigned_to
        
        task.save()
        
        # المهام الفرعية
        subtasks = request.POST.getlist('subtasks[]')
        for i, title in enumerate(subtasks):
            if title.strip():
                SubTask.objects.create(task=task, title=title.strip(), order=i)
        
        messages.success(request, 'تم إنشاء المهمة بنجاح')
        return redirect('tasks:detail', task_id=task.id)
    
    categories = TaskCategory.objects.filter(is_active=True)
    task_lists = TaskList.objects.filter(
        Q(owner=request.user) | Q(shared_with=request.user)
    ).distinct()
    
    return render(request, 'tasks/form.html', {
        'categories': categories,
        'task_lists': task_lists,
    })


@login_required
@require_http_methods(['POST'])
def task_update_status(request, task_id):
    """تحديث حالة المهمة"""
    task = get_object_or_404(Task, id=task_id)
    
    try:
        data = json.loads(request.body)
        old_status = task.status
        new_status = data.get('status')
        
        task.status = new_status
        
        if new_status == 'completed':
            task.completed_at = timezone.now()
            task.progress = 100
        
        task.save()
        
        # سجل التغيير
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action='status_change',
            old_value=old_status,
            new_value=new_status
        )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def toggle_subtask(request, subtask_id):
    """تبديل حالة المهمة الفرعية"""
    subtask = get_object_or_404(SubTask, id=subtask_id)
    
    subtask.is_completed = not subtask.is_completed
    if subtask.is_completed:
        subtask.completed_at = timezone.now()
    else:
        subtask.completed_at = None
    subtask.save()
    
    # تحديث نسبة الإنجاز
    task = subtask.task
    total = task.subtasks.count()
    completed = task.subtasks.filter(is_completed=True).count()
    task.progress = int((completed / total) * 100) if total > 0 else 0
    task.save()
    
    return JsonResponse({
        'success': True,
        'is_completed': subtask.is_completed,
        'progress': task.progress
    })


@login_required
@require_http_methods(['POST'])
def add_comment(request, task_id):
    """إضافة تعليق"""
    task = get_object_or_404(Task, id=task_id)
    
    try:
        data = json.loads(request.body)
        
        comment = TaskComment.objects.create(
            task=task,
            user=request.user,
            content=data.get('content')
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': comment.user.get_full_name() or comment.user.username,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def reminders_list(request):
    """قائمة التذكيرات"""
    reminders = Reminder.objects.filter(
        user=request.user,
        is_dismissed=False
    ).order_by('remind_at')
    
    return render(request, 'tasks/reminders.html', {
        'reminders': reminders,
    })


@login_required
@require_http_methods(['POST'])
def create_reminder(request):
    """إنشاء تذكير"""
    try:
        data = json.loads(request.body)
        
        reminder = Reminder.objects.create(
            user=request.user,
            title=data.get('title'),
            description=data.get('description', ''),
            reminder_type=data.get('type', 'custom'),
            remind_at=data.get('remind_at'),
            task_id=data.get('task_id')
        )
        
        return JsonResponse({
            'success': True,
            'reminder_id': reminder.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def snooze_reminder(request, reminder_id):
    """تأجيل تذكير"""
    reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        minutes = data.get('minutes', 15)
        
        reminder.snoozed_until = timezone.now() + timezone.timedelta(minutes=minutes)
        reminder.is_sent = False
        reminder.save()
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(['POST'])
def dismiss_reminder(request, reminder_id):
    """تجاهل تذكير"""
    reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
    
    reminder.is_dismissed = True
    reminder.save()
    
    return JsonResponse({'success': True})


@login_required
def kanban_board(request):
    """لوحة كانبان"""
    user = request.user
    
    tasks = Task.objects.filter(
        Q(assigned_to=user) | Q(created_by=user),
        is_archived=False
    ).select_related('category', 'assigned_to')
    
    columns = {
        'pending': tasks.filter(status='pending'),
        'in_progress': tasks.filter(status='in_progress'),
        'completed': tasks.filter(status='completed'),
    }
    
    return render(request, 'tasks/kanban.html', {
        'columns': columns,
    })


@login_required
def calendar_view(request):
    """عرض التقويم"""
    user = request.user
    
    tasks = Task.objects.filter(
        Q(assigned_to=user) | Q(created_by=user),
        due_date__isnull=False,
        is_archived=False
    ).values('id', 'title', 'due_date', 'priority', 'status')
    
    events = [
        {
            'id': t['id'],
            'title': t['title'],
            'start': t['due_date'].isoformat(),
            'className': f"priority-{t['priority']} status-{t['status']}"
        }
        for t in tasks
    ]
    
    return render(request, 'tasks/calendar.html', {
        'events': json.dumps(events),
    })
