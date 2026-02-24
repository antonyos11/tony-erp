"""
Admin للمهام
"""

from django.contrib import admin
from .models import (
    TaskCategory, TaskList, Task, SubTask,
    TaskComment, TaskAttachment, Reminder, TaskHistory
)


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'icon', 'is_system', 'is_active']
    list_filter = ['is_system', 'is_active']
    search_fields = ['name']


@admin.register(TaskList)
class TaskListAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active']
    search_fields = ['name', 'owner__username']
    raw_id_fields = ['owner']


class SubTaskInline(admin.TabularInline):
    model = SubTask
    extra = 0


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'assigned_to', 'due_date', 'created_by']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['title', 'description']
    raw_id_fields = ['created_by', 'assigned_to', 'task_list', 'category']
    date_hierarchy = 'created_at'
    inlines = [SubTaskInline, TaskCommentInline]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'reminder_type', 'remind_at', 'is_sent', 'is_dismissed']
    list_filter = ['reminder_type', 'is_sent', 'is_dismissed']
    search_fields = ['title', 'user__username']
    raw_id_fields = ['user', 'task']


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['task__title']
    readonly_fields = ['task', 'user', 'action', 'old_value', 'new_value', 'created_at']
