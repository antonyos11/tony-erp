"""
Signals لمزامنة البيانات بين Showroom و Branch
عند إنشاء/تعديل/حذف Showroom، يتم تحديث Branch تلقائياً
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Showroom

# متغير لمنع الحلقة اللانهائية
_syncing_from_showroom = False


@receiver(post_save, sender=Showroom)
def sync_showroom_to_branch(sender, instance, created, **kwargs):
    """مزامنة Showroom مع Branch عند الإنشاء أو التعديل"""
    global _syncing_from_showroom
    
    # إذا كان الـ sync قادم من branch، لا تفعل شيء
    from branches.signals import _syncing_from_branch
    if _syncing_from_branch:
        return
    
    from branches.models import Branch
    
    # تحويل نوع المعرض لنوع الفرع
    type_mapping = {
        'showroom': 'showroom',
        'branch': 'branch',
        'warehouse': 'warehouse',
        'factory': 'factory',
    }
    branch_type = type_mapping.get(instance.showroom_type, 'branch')
    
    # تحويل حالة النشاط
    status = 'active' if instance.is_active else 'inactive'
    
    try:
        # منع الحلقة اللانهائية
        _syncing_from_showroom = True
        
        # البحث عن الفرع المرتبط أو إنشاء جديد
        branch, branch_created = Branch.objects.update_or_create(
            code=instance.code,
            defaults={
                'name': instance.name_ar or instance.name,
                'branch_type': branch_type,
                'status': status,
                'phone': getattr(instance, 'phone', '') or '',
                'address': getattr(instance, 'address', '') or '',
            }
        )
        
        if branch_created:
            print(f"[Sync] تم إنشاء Branch جديد: {branch.name} ({branch.code})")
        else:
            print(f"[Sync] تم تحديث Branch: {branch.name} ({branch.code})")
    except Exception as e:
        print(f"[Sync Error] خطأ في مزامنة Showroom→Branch: {e}")
    finally:
        _syncing_from_showroom = False


@receiver(post_delete, sender=Showroom)
def delete_branch_on_showroom_delete(sender, instance, **kwargs):
    """حذف Branch المرتبط عند حذف Showroom"""
    from branches.models import Branch
    
    try:
        branch = Branch.objects.get(code=instance.code)
        branch.delete()
        print(f"[Sync] تم حذف Branch: {branch.name} ({branch.code})")
    except Branch.DoesNotExist:
        pass
