from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='partners.Partner')
def create_supplier_for_partner(sender, instance, created, **kwargs):
    """Auto-create a Supplier record when a Partner of type supplier/both is saved."""
    from .models import Supplier

    if instance.partner_type in ('supplier', 'both'):
        if not hasattr(instance, 'supplier_profile') or not Supplier.objects.filter(partner=instance).exists():
            Supplier.objects.create(
                partner=instance,
                name=instance.name,
                email=instance.email,
                phone=instance.phone,
                address=instance.address,
                is_active=instance.is_active,
            )
        else:
            # Sync name/contact info
            supp = instance.supplier_profile
            changed = False
            for field in ('name', 'email', 'phone', 'address', 'is_active'):
                if getattr(supp, field) != getattr(instance, field):
                    setattr(supp, field, getattr(instance, field))
                    changed = True
            if changed:
                supp.save()
