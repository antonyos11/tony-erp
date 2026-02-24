"""
نظام الموافقات الجماعية المحسّن
Bulk Approval System
"""

from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)


class BulkApprovalHandler:
    """معالج الموافقات الجماعية"""
    
    BATCH_SIZE = 50  # حجم الدفعة
    
    @staticmethod
    def approve_entries_bulk(user, entry_ids, comment=None):
        """
        موافقة جماعية على القيود المحاسبية
        
        Args:
            user: المستخدم المعتمد
            entry_ids: قائمة معرفات القيود
            comment: تعليق اختياري
        
        Returns:
            dict مع نتيجة العملية
        """
        from accounting.models import JournalEntry
        
        total_count = len(entry_ids)
        approved_count = 0
        failed_count = 0
        errors = []
        
        try:
            # معالجة على دفعات
            for i in range(0, total_count, BulkApprovalHandler.BATCH_SIZE):
                batch = entry_ids[i:i + BulkApprovalHandler.BATCH_SIZE]
                
                with transaction.atomic():
                    # الحصول على القيود للموافقة
                    entries = JournalEntry.objects.filter(
                        id__in=batch,
                        status='pending'
                    ).select_for_update()
                    
                    # الموافقة
                    for entry in entries:
                        try:
                            entry.status = 'approved'
                            entry.approved_by = user
                            entry.approved_at = timezone.now()
                            if comment:
                                entry.approval_comment = comment
                            entry.save()
                            
                            approved_count += 1
                            
                        except Exception as e:
                            failed_count += 1
                            errors.append({
                                'entry_id': entry.id,
                                'error': str(e)
                            })
                            logger.error(f"فشلت الموافقة على القيد {entry.id}: {str(e)}")
            
            return {
                'success': True,
                'total': total_count,
                'approved': approved_count,
                'failed': failed_count,
                'errors': errors,
                'message': f'تمت الموافقة على {approved_count} من {total_count} قيد'
            }
            
        except Exception as e:
            logger.error(f"خطأ في الموافقة الجماعية: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'فشلت عملية الموافقة الجماعية'
            }
    
    @staticmethod
    def reject_entries_bulk(user, entry_ids, reason):
        """
        رفض جماعي للقيود
        
        Args:
            user: المستخدم
            entry_ids: قائمة معرفات القيود
            reason: سبب الرفض
        
        Returns:
            dict مع نتيجة العملية
        """
        from accounting.models import JournalEntry
        
        total_count = len(entry_ids)
        rejected_count = 0
        
        try:
            for i in range(0, total_count, BulkApprovalHandler.BATCH_SIZE):
                batch = entry_ids[i:i + BulkApprovalHandler.BATCH_SIZE]
                
                with transaction.atomic():
                    entries = JournalEntry.objects.filter(
                        id__in=batch,
                        status='pending'
                    ).select_for_update()
                    
                    for entry in entries:
                        entry.status = 'rejected'
                        entry.rejected_by = user
                        entry.rejected_at = timezone.now()
                        entry.rejection_reason = reason
                        entry.save()
                        
                        rejected_count += 1
            
            return {
                'success': True,
                'total': total_count,
                'rejected': rejected_count,
                'message': f'تم رفض {rejected_count} قيد'
            }
            
        except Exception as e:
            logger.error(f"خطأ في الرفض الجماعي: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def approve_invoices_bulk(user, invoice_ids, comment=None):
        """
        موافقة جماعية على الفواتير
        
        Args:
            user: المستخدم
            invoice_ids: قائمة معرفات الفواتير
            comment: تعليق
        
        Returns:
            dict مع النتيجة
        """
        from sales.models import Invoice
        
        total_count = len(invoice_ids)
        approved_count = 0
        
        try:
            for i in range(0, total_count, BulkApprovalHandler.BATCH_SIZE):
                batch = invoice_ids[i:i + BulkApprovalHandler.BATCH_SIZE]
                
                with transaction.atomic():
                    invoices = Invoice.objects.filter(
                        id__in=batch,
                        status='pending'
                    ).select_for_update()
                    
                    for invoice in invoices:
                        invoice.status = 'approved'
                        invoice.approved_by = user
                        invoice.approved_at = timezone.now()
                        if comment:
                            invoice.approval_comment = comment
                        invoice.save()
                        
                        # تحديث المخزون
                        invoice.update_inventory()
                        
                        approved_count += 1
            
            return {
                'success': True,
                'total': total_count,
                'approved': approved_count,
                'message': f'تمت الموافقة على {approved_count} فاتورة'
            }
            
        except Exception as e:
            logger.error(f"خطأ في موافقة الفواتير: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Views للموافقات الجماعية

@login_required
@require_POST
def bulk_approve_entries(request):
    """
    View للموافقة الجماعية على القيود
    """
    try:
        entry_ids = request.POST.getlist('entry_ids[]')
        comment = request.POST.get('comment', '')
        
        if not entry_ids:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم تحديد أي قيود'
            }, status=400)
        
        # تحويل إلى integers
        entry_ids = [int(id) for id in entry_ids]
        
        # تنفيذ الموافقة
        result = BulkApprovalHandler.approve_entries_bulk(
            user=request.user,
            entry_ids=entry_ids,
            comment=comment
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"خطأ في bulk_approve_entries: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_reject_entries(request):
    """
    View للرفض الجماعي للقيود
    """
    try:
        entry_ids = request.POST.getlist('entry_ids[]')
        reason = request.POST.get('reason', '')
        
        if not entry_ids:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم تحديد أي قيود'
            }, status=400)
        
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'يجب إدخال سبب الرفض'
            }, status=400)
        
        entry_ids = [int(id) for id in entry_ids]
        
        result = BulkApprovalHandler.reject_entries_bulk(
            user=request.user,
            entry_ids=entry_ids,
            reason=reason
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"خطأ في bulk_reject_entries: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def bulk_approve_invoices(request):
    """
    View للموافقة الجماعية على الفواتير
    """
    try:
        invoice_ids = request.POST.getlist('invoice_ids[]')
        comment = request.POST.get('comment', '')
        
        if not invoice_ids:
            return JsonResponse({
                'success': False,
                'message': 'لم يتم تحديد أي فواتير'
            }, status=400)
        
        invoice_ids = [int(id) for id in invoice_ids]
        
        result = BulkApprovalHandler.approve_invoices_bulk(
            user=request.user,
            invoice_ids=invoice_ids,
            comment=comment
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"خطأ في bulk_approve_invoices: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
