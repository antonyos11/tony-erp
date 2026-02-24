from django.db import models
from django.conf import settings
from django.utils import timezone
from .models import Showroom, ShowroomEmployee

class AttendanceRecord(models.Model):
    showroom = models.ForeignKey(Showroom, on_delete=models.CASCADE, related_name='attendance_records')
    employee = models.ForeignKey(ShowroomEmployee, on_delete=models.CASCADE, related_name='attendance_records')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='showroom_attendance')
    date = models.DateField(default=timezone.now)
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    device_identifier = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('showroom','employee','date')
        indexes = [models.Index(fields=['showroom','date']), models.Index(fields=['employee','date'])]

    def punch_in(self, device_id=None):
        if self.in_time:
            return False
        self.in_time = timezone.now()
        if device_id and not self.device_identifier:
            self.device_identifier = device_id
        self.save(update_fields=['in_time','device_identifier'])
        return True

    def punch_out(self, device_id=None):
        if self.out_time:
            return False
        self.out_time = timezone.now()
        self.save(update_fields=['out_time'])
        return True

    @property
    def worked_seconds(self):
        if self.in_time and self.out_time:
            return int((self.out_time - self.in_time).total_seconds())
        return 0
