from django.db import models, transaction
from django.db.models import F
from django.utils import timezone

class Sequence(models.Model):
    """Generic named sequence with integer value (per prefix or key)."""
    name = models.CharField(max_length=100, unique=True)
    value = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'

    def __str__(self):
        return f"{self.name}={self.value}"

@transaction.atomic
def next_sequence(name: str, initial: int = 1) -> int:
    seq = Sequence.objects.select_for_update().filter(name=name).first()
    if not seq:
        seq = Sequence.objects.create(name=name, value=initial)
        return initial
    seq.value = F('value') + 1
    seq.save(update_fields=['value'])
    seq.refresh_from_db(fields=['value'])
    return seq.value

def format_code(prefix: str, num: int, width: int = 6) -> str:
    return f"{prefix}-{str(num).zfill(width)}"
