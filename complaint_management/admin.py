from django.contrib import admin
from .models import Complaint, ImprovementInitiative

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['complaint_number', 'customer', 'category', 'priority', 'status', 
                    'assigned_to', 'customer_satisfaction_rating', 'received_at']
    list_filter = ['status', 'priority', 'category', 'channel']
    search_fields = ['complaint_number', 'customer__name', 'title', 'description']

@admin.register(ImprovementInitiative)
class ImprovementInitiativeAdmin(admin.ModelAdmin):
    list_display = ['title', 'initiative_type', 'status', 'owner', 'target_completion_date', 'created_at']
    list_filter = ['status', 'initiative_type']
    search_fields = ['title', 'description']
    filter_horizontal = ['team_members']
