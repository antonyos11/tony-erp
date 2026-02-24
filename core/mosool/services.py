# -*- coding: utf-8 -*-
"""
خدمات موصول التحضير والاستماد
Services for Preparation and Approval Documents
"""

from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from typing import Optional, Tuple, List, Dict, Any

from .models import (
    PreparationRequest, PreparationItem, PreparationApproval,
    ApprovalDocument, ApprovalDocumentItem, DocumentApproval,
    ApprovalWorkflow
)


class PreparationService:
    """خدمات موصول التحضير"""
    
    @staticmethod
    def create_preparation(
        user: User,
        request_type: str,
        title: str,
        items: List[Dict[str, Any]],
        department=None,
        cost_center=None,
        project=None,
        required_date=None,
        priority: str = 'normal',
        notes: str = '',
        auto_submit: bool = False
    ) -> PreparationRequest:
        """
        إنشاء طلب تحضير جديد
        
        Args:
            user: المستخدم مقدم الطلب
            request_type: نوع الطلب (purchase, material_issue, etc.)
            title: عنوان الطلب
            items: قائمة البنود [{product_id, description, quantity, unit, estimated_price}]
            department: القسم الطالب
            cost_center: مركز التكلفة
            project: المشروع
            required_date: تاريخ الاحتياج
            priority: الأولوية
            notes: ملاحظات
            auto_submit: تقديم تلقائي للمراجعة
        
        Returns:
            PreparationRequest: طلب التحضير المنشأ
        """
        with transaction.atomic():
            preparation = PreparationRequest.objects.create(
                request_type=request_type,
                title=title,
                requested_by=user,
                department=department,
                cost_center=cost_center,
                project=project,
                required_date=required_date,
                priority=priority,
                notes=notes,
                status=PreparationRequest.Status.DRAFT
            )
            
            total = Decimal('0')
            for item_data in items:
                item = PreparationItem.objects.create(
                    preparation=preparation,
                    product_id=item_data.get('product_id'),
                    description=item_data.get('description', ''),
                    quantity_requested=Decimal(str(item_data.get('quantity', 1))),
                    unit=item_data.get('unit', 'قطعة'),
                    estimated_unit_price=Decimal(str(item_data.get('estimated_price', 0))),
                    notes=item_data.get('notes', '')
                )
                total += item.estimated_amount
            
            preparation.estimated_total = total
            preparation.save(update_fields=['estimated_total'])
            
            if auto_submit:
                preparation.submit()
            
            return preparation
    
    @staticmethod
    def approve_item(
        preparation: PreparationRequest,
        item_id: int,
        user: User,
        approved_quantity: Decimal,
        notes: str = ''
    ) -> bool:
        """اعتماد بند في طلب التحضير"""
        try:
            item = preparation.items.get(id=item_id)
            item.is_approved = True
            item.quantity_approved = approved_quantity
            item.notes = notes if notes else item.notes
            item.save()
            
            PreparationApproval.objects.create(
                preparation=preparation,
                approved_by=user,
                action='approve',
                notes=f"اعتماد البند: {item.description} - الكمية: {approved_quantity}"
            )
            return True
        except PreparationItem.DoesNotExist:
            return False
    
    @staticmethod
    def get_pending_preparations(user: User = None, department=None) -> List[PreparationRequest]:
        """الحصول على طلبات التحضير المعلقة"""
        qs = PreparationRequest.objects.filter(status=PreparationRequest.Status.PENDING)
        if department:
            qs = qs.filter(department=department)
        return list(qs.select_related('requested_by', 'department').prefetch_related('items'))
    
    @staticmethod
    def get_user_preparations(user: User, status: str = None) -> List[PreparationRequest]:
        """الحصول على طلبات التحضير للمستخدم"""
        qs = PreparationRequest.objects.filter(
            Q(requested_by=user) | Q(assigned_to=user)
        )
        if status:
            qs = qs.filter(status=status)
        return list(qs.order_by('-created_at'))
    
    @staticmethod
    def convert_to_approval_document(
        preparation: PreparationRequest,
        user: User,
        document_type: str = 'pr'
    ) -> Optional[ApprovalDocument]:
        """
        تحويل طلب التحضير إلى مستند استماد
        """
        if preparation.status != PreparationRequest.Status.COMPLETED:
            return None
        
        with transaction.atomic():
            doc = ApprovalDocument.objects.create(
                document_type=document_type,
                title=preparation.title,
                description=preparation.description,
                preparation_request=preparation,
                document_date=timezone.now().date(),
                total_amount=preparation.estimated_total,
                department=preparation.department,
                cost_center=preparation.cost_center,
                created_by=user,
                notes=preparation.notes
            )
            
            for item in preparation.items.filter(is_approved=True):
                ApprovalDocumentItem.objects.create(
                    document=doc,
                    description=item.description,
                    product=item.product,
                    quantity=item.quantity_approved,
                    unit=item.unit,
                    unit_price=item.estimated_unit_price
                )
            
            # تحديث المبلغ الإجمالي
            doc.total_amount = sum(i.total_amount for i in doc.items.all())
            doc.save(update_fields=['total_amount'])
            
            return doc
    
    @staticmethod
    def get_statistics(date_from=None, date_to=None) -> Dict[str, Any]:
        """إحصائيات طلبات التحضير"""
        qs = PreparationRequest.objects.all()
        
        if date_from:
            qs = qs.filter(request_date__gte=date_from)
        if date_to:
            qs = qs.filter(request_date__lte=date_to)
        
        return {
            'total_count': qs.count(),
            'draft_count': qs.filter(status=PreparationRequest.Status.DRAFT).count(),
            'pending_count': qs.filter(status=PreparationRequest.Status.PENDING).count(),
            'in_progress_count': qs.filter(status=PreparationRequest.Status.IN_PROGRESS).count(),
            'completed_count': qs.filter(status=PreparationRequest.Status.COMPLETED).count(),
            'cancelled_count': qs.filter(status=PreparationRequest.Status.CANCELLED).count(),
            'total_estimated': qs.aggregate(total=Sum('estimated_total'))['total'] or Decimal('0'),
            'by_type': dict(qs.values('request_type').annotate(count=Count('id')).values_list('request_type', 'count')),
            'by_priority': dict(qs.values('priority').annotate(count=Count('id')).values_list('priority', 'count')),
        }


class ApprovalDocumentService:
    """خدمات موصول الاستماد"""
    
    @staticmethod
    def create_approval_document(
        user: User,
        document_type: str,
        title: str,
        items: List[Dict[str, Any]],
        department=None,
        cost_center=None,
        supplier=None,
        employee=None,
        due_date=None,
        notes: str = '',
        auto_submit: bool = False
    ) -> ApprovalDocument:
        """
        إنشاء مستند استماد جديد
        """
        with transaction.atomic():
            doc = ApprovalDocument.objects.create(
                document_type=document_type,
                title=title,
                created_by=user,
                department=department,
                cost_center=cost_center,
                supplier=supplier,
                employee=employee,
                due_date=due_date,
                notes=notes,
                status=ApprovalDocument.Status.DRAFT
            )
            
            total = Decimal('0')
            for item_data in items:
                item = ApprovalDocumentItem.objects.create(
                    document=doc,
                    description=item_data.get('description', ''),
                    product_id=item_data.get('product_id'),
                    account_id=item_data.get('account_id'),
                    quantity=Decimal(str(item_data.get('quantity', 1))),
                    unit=item_data.get('unit', 'قطعة'),
                    unit_price=Decimal(str(item_data.get('unit_price', 0))),
                    notes=item_data.get('notes', '')
                )
                total += item.total_amount
            
            doc.total_amount = total
            doc.save(update_fields=['total_amount'])
            
            if auto_submit:
                doc.submit_for_approval()
            
            return doc
    
    @staticmethod
    def get_pending_for_user(user: User) -> List[ApprovalDocument]:
        """
        الحصول على المستندات المعلقة التي يمكن للمستخدم اعتمادها
        """
        # البحث عن الدور والصلاحيات
        profile = getattr(user, 'profile', None)
        if not profile:
            return []
        
        user_approval_level = getattr(profile.role, 'approval_level', 0) if profile.role else 0
        
        # المستندات في انتظار الاعتماد على مستوى يمكن للمستخدم اعتماده
        qs = ApprovalDocument.objects.filter(
            status__in=[ApprovalDocument.Status.PENDING_APPROVAL, ApprovalDocument.Status.PARTIALLY_APPROVED],
            current_approval_level__lte=user_approval_level
        )
        
        # فلترة حسب القسم إن وجد
        if hasattr(profile, 'employee') and profile.employee and profile.employee.department:
            dept = profile.employee.department
            qs = qs.filter(Q(department=dept) | Q(department__isnull=True))
        
        return list(qs.select_related('created_by', 'department', 'supplier').prefetch_related('items'))
    
    @staticmethod
    def approve_document(
        document: ApprovalDocument,
        user: User,
        notes: str = '',
        approved_amount: Decimal = None
    ) -> Tuple[bool, str]:
        """
        اعتماد مستند
        """
        # التحقق من صلاحية المستخدم
        profile = getattr(user, 'profile', None)
        if not profile or not profile.role:
            return False, "لا توجد صلاحيات للاعتماد"
        
        user_level = getattr(profile.role, 'approval_level', 0)
        if user_level < document.current_approval_level:
            return False, "مستوى الصلاحية غير كافٍ"
        
        return document.approve(user, document.current_approval_level, notes, approved_amount)
    
    @staticmethod
    def reject_document(
        document: ApprovalDocument,
        user: User,
        reason: str
    ) -> Tuple[bool, str]:
        """
        رفض مستند
        """
        if not reason:
            return False, "يجب تحديد سبب الرفض"
        
        return document.reject(user, reason)
    
    @staticmethod
    def get_approval_history(document: ApprovalDocument) -> List[DocumentApproval]:
        """الحصول على سجل الاعتمادات"""
        return list(document.approvals.select_related('approved_by').order_by('created_at'))
    
    @staticmethod
    def get_user_documents(user: User, status: str = None) -> List[ApprovalDocument]:
        """الحصول على مستندات المستخدم"""
        qs = ApprovalDocument.objects.filter(created_by=user)
        if status:
            qs = qs.filter(status=status)
        return list(qs.order_by('-created_at'))
    
    @staticmethod
    def get_statistics(date_from=None, date_to=None) -> Dict[str, Any]:
        """إحصائيات مستندات الاستماد"""
        qs = ApprovalDocument.objects.all()
        
        if date_from:
            qs = qs.filter(document_date__gte=date_from)
        if date_to:
            qs = qs.filter(document_date__lte=date_to)
        
        return {
            'total_count': qs.count(),
            'draft_count': qs.filter(status=ApprovalDocument.Status.DRAFT).count(),
            'pending_count': qs.filter(status=ApprovalDocument.Status.PENDING_APPROVAL).count(),
            'partial_count': qs.filter(status=ApprovalDocument.Status.PARTIALLY_APPROVED).count(),
            'approved_count': qs.filter(status=ApprovalDocument.Status.APPROVED).count(),
            'rejected_count': qs.filter(status=ApprovalDocument.Status.REJECTED).count(),
            'total_amount': qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
            'approved_amount': qs.filter(status=ApprovalDocument.Status.APPROVED).aggregate(total=Sum('approved_amount'))['total'] or Decimal('0'),
            'by_type': dict(qs.values('document_type').annotate(count=Count('id')).values_list('document_type', 'count')),
            'by_department': list(qs.values('department__name').annotate(
                count=Count('id'),
                total=Sum('total_amount')
            )),
        }
    
    @staticmethod
    def get_workflow_approvers(
        document_type: str,
        level: int,
        amount: Decimal = None,
        department=None
    ) -> List[User]:
        """
        الحصول على المعتمدين المناسبين لمستند معين
        """
        qs = ApprovalWorkflow.objects.filter(
            document_type=document_type,
            approval_level=level,
            is_active=True
        )
        
        if amount:
            qs = qs.filter(
                Q(max_amount__gte=amount) | Q(max_amount__isnull=True),
                min_amount__lte=amount
            )
        
        if department:
            qs = qs.filter(Q(department=department) | Q(department__isnull=True))
        
        approvers = []
        for workflow in qs:
            if workflow.approver:
                approvers.append(workflow.approver)
            elif workflow.approver_role:
                # الحصول على المستخدمين بهذا الدور
                from users.models import UserProfile
                profiles = UserProfile.objects.filter(role=workflow.approver_role)
                approvers.extend([p.user for p in profiles if p.user])
        
        return list(set(approvers))


class DashboardService:
    """خدمات لوحة التحكم"""
    
    @staticmethod
    def get_preparation_summary(user: User = None) -> Dict[str, Any]:
        """ملخص طلبات التحضير"""
        qs = PreparationRequest.objects.all()
        if user:
            qs = qs.filter(Q(requested_by=user) | Q(assigned_to=user))
        
        today = timezone.now().date()
        
        return {
            'total': qs.count(),
            'pending': qs.filter(status=PreparationRequest.Status.PENDING).count(),
            'in_progress': qs.filter(status=PreparationRequest.Status.IN_PROGRESS).count(),
            'overdue': qs.filter(
                required_date__lt=today,
                status__in=[PreparationRequest.Status.PENDING, PreparationRequest.Status.IN_PROGRESS]
            ).count(),
            'recent': list(qs.order_by('-created_at')[:5].values(
                'id', 'number', 'title', 'status', 'priority', 'created_at'
            )),
        }
    
    @staticmethod
    def get_approval_summary(user: User = None) -> Dict[str, Any]:
        """ملخص مستندات الاستماد"""
        qs = ApprovalDocument.objects.all()
        
        profile = getattr(user, 'profile', None) if user else None
        user_level = getattr(profile.role, 'approval_level', 0) if profile and profile.role else 0
        
        pending_for_me = 0
        if user_level > 0:
            pending_for_me = qs.filter(
                status__in=[ApprovalDocument.Status.PENDING_APPROVAL, ApprovalDocument.Status.PARTIALLY_APPROVED],
                current_approval_level__lte=user_level
            ).count()
        
        today = timezone.now().date()
        
        return {
            'total': qs.count(),
            'pending_for_me': pending_for_me,
            'pending_total': qs.filter(status=ApprovalDocument.Status.PENDING_APPROVAL).count(),
            'approved_today': qs.filter(
                status=ApprovalDocument.Status.APPROVED,
                approved_at__date=today
            ).count(),
            'total_pending_amount': qs.filter(
                status__in=[ApprovalDocument.Status.PENDING_APPROVAL, ApprovalDocument.Status.PARTIALLY_APPROVED]
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0'),
            'recent': list(qs.order_by('-created_at')[:5].values(
                'id', 'number', 'title', 'status', 'document_type', 'total_amount', 'created_at'
            )),
        }
    
    @staticmethod
    def get_combined_dashboard(user: User = None) -> Dict[str, Any]:
        """لوحة تحكم شاملة"""
        return {
            'preparations': DashboardService.get_preparation_summary(user),
            'approvals': DashboardService.get_approval_summary(user),
            'updated_at': timezone.now().isoformat(),
        }
