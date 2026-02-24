"""Lightweight signals for accounts app.

This module stays safe for import during app startup/tests by avoiding DB work
and only logging on relevant events. Extend with real 2FA/user lifecycle hooks
when needed.
"""
from __future__ import annotations
import logging
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=get_user_model())
def _log_user_created(sender, instance, created, **kwargs):
    """Placeholder hook; ensures signals module imports cleanly."""
    if created:
        logger.debug("accounts.signals: user created id=%s", instance.pk)
