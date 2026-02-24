"""
Signals لمزامنة البيانات بين Branch و Showroom
عند إنشاء/تعديل/حذف Branch، يتم تحديث Showroom تلقائياً
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Branch

# متغير لمنع الحلقة اللانهائية
_syncing_from_branch = False


@receiver(post_save, sender=Branch)
def sync_branch_to_showroom(sender, instance, created, **kwargs):
    """مزامنة Branch مع Showroom عند الإنشاء أو التعديل"""
    global _syncing_from_branch
    
    # إذا كان الـ sync قادم من showroom، لا تفعل شيء
    from showrooms.signals import _syncing_from_showroom
    if _syncing_from_showroom:
        return
    
    from showrooms.models import Showroom
    from inventory.models import Location
    
    # تحويل نوع الفرع لنوع المعرض
    type_mapping = {
        'showroom': 'showroom',
        'branch': 'branch',
        'warehouse': 'warehouse',
        'factory': 'factory',
    }
    showroom_type = type_mapping.get(instance.branch_type, 'showroom')
    
    # تحويل حالة النشاط
    is_active = instance.status == 'active'
    
    try:
        # منع الحلقة اللانهائية
        _syncing_from_branch = True
        
        # البحث عن معرض موجود
        showroom = Showroom.objects.filter(code=instance.code).first()
        
        if showroom:
            # تحديث المعرض الموجود
            showroom.name = instance.name
            showroom.name_ar = instance.name
            showroom.showroom_type = showroom_type
            showroom.is_active = is_active
            showroom.address = instance.address or ''
            showroom.save()
            print(f"[Sync] تم تحديث Showroom: {showroom.name} ({showroom.code})")
        else:
            # إنشاء موقع جديد للمعرض
            location, loc_created = Location.objects.get_or_create(
                code=f"LOC-{instance.code}",
                defaults={
                    'name': instance.name,
                    'type': 'showroom',
                    'is_active': True,
                }
            )
            
            # إنشاء معرض جديد
            showroom = Showroom.objects.create(
                code=instance.code,
                name=instance.name,
                name_ar=instance.name,
                showroom_type=showroom_type,
                is_active=is_active,
                address=instance.address or '',
                location=location,
            )
            print(f"[Sync] تم إنشاء Showroom جديد: {showroom.name} ({showroom.code})")
    except Exception as e:
        print(f"[Sync Error] خطأ في مزامنة Branch→Showroom: {e}")
    finally:
        _syncing_from_branch = False


@receiver(post_delete, sender=Branch)
def delete_showroom_on_branch_delete(sender, instance, **kwargs):
    """حذف Showroom المرتبط عند حذف Branch"""
    from showrooms.models import Showroom
    
    try:
        showroom = Showroom.objects.get(code=instance.code)
        showroom.delete()
        print(f"[Sync] تم حذف Showroom: {showroom.name} ({showroom.code})")
    except Showroom.DoesNotExist:
        pass
