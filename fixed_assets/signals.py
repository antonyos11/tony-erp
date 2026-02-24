# Signals for fixed assets
from django.db.models.signals import post_save
from django.dispatch import receiver

# Placeholder - can add signals for:
# - Auto-creating depreciation schedule when asset is created
# - Updating asset location when transfer is approved
# - Creating journal entries when depreciation is posted
