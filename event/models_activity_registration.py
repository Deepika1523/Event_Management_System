from django.db import models
from django.conf import settings
from participant.models import Participant
from .models import Activity

class ActivityRegistration(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('participant', 'activity')

    def __str__(self):
        return f"{self.participant} registered for {self.activity}"