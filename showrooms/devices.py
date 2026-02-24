from django.db import models
from django.conf import settings
from django.utils import timezone
from .models import Showroom

class POSDevice(models.Model):
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='devices')
    name = models.CharField(max_length=100)
    identifier = models.CharField(max_length=120, unique=True, help_text='Serial / MAC / Generated UUID')
    api_key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['showroom','is_active']), models.Index(fields=['identifier'])]

    def touch(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])

    def __str__(self):
        return f"{self.name} ({self.identifier})"

class DeviceAuthToken(models.Model):
    device = models.ForeignKey(POSDevice, on_delete=models.CASCADE, related_name='tokens')
    token = models.CharField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)

    def is_valid(self):
        if self.revoked:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
