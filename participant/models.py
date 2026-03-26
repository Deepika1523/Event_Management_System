from django.conf import settings
from django.db import models

from event.models import Activity, Event


class EventRegistration(models.Model):
	participant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="event_registrations",
	)
	event = models.ForeignKey(
		Event,
		on_delete=models.CASCADE,
		related_name="event_registrations",
	)
	registered_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ("participant", "event")
		ordering = ["-registered_at"]

	def __str__(self):
		return f"{self.participant.username} -> {self.event.event}"


class ActivityRegistration(models.Model):
	participant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="activity_registrations",
	)
	activity = models.ForeignKey(
		Activity,
		on_delete=models.CASCADE,
		related_name="activity_registrations",
	)
	registered_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ("participant", "activity")
		ordering = ["-registered_at"]

	def __str__(self):
		return f"{self.participant.username} -> {self.activity.name}"
