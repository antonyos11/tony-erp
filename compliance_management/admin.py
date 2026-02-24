from django.contrib import admin
from .models import ComplianceStandard, ComplianceChecklist, Audit, AuditFinding, ComplianceReport

@admin.register(ComplianceStandard)
class ComplianceStandardAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'standard_type', 'issuing_body', 'version', 
                    'is_mandatory', 'is_active']
    list_filter = ['standard_type', 'is_mandatory', 'is_active']
    search_fields = ['code', 'name', 'issuing_body']

@admin.register(ComplianceChecklist)
class ComplianceChecklistAdmin(admin.ModelAdmin):
    list_display = ['title', 'standard', 'frequency', 'assigned_to', 'is_active']
    list_filter = ['frequency', 'is_active']
    search_fields = ['title', 'standard__name']

@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['audit_number', 'title', 'audit_type', 'status', 'scheduled_date',
                    'lead_auditor', 'overall_compliance_score']
    list_filter = ['audit_type', 'status', 'scheduled_date']
    search_fields = ['audit_number', 'title']
    filter_horizontal = ['audit_team']

@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = ['finding_number', 'audit', 'severity', 'category', 'status',
                    'responsible_person', 'corrective_action_deadline']
    list_filter = ['severity', 'category', 'status']
    search_fields = ['finding_number', 'description', 'audit__audit_number']

@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_period_start', 'report_period_end', 
                    'overall_compliance_status', 'compliance_percentage', 'prepared_by']
    list_filter = ['overall_compliance_status', 'report_period_end']
    search_fields = ['title', 'executive_summary']
    filter_horizontal = ['standards_covered']
