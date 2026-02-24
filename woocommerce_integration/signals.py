# Placeholder for Django signals
# Will be used to trigger sync when products/invoices change

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# Import when ready
# from inventory.models import Product, Stock
# from sales.models import Invoice
