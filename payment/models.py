from django.conf import settings
from django.db import models
from django.utils import timezone

from participant.models import ActivityRegistration


class PaymentCheck(models.Model):
	STATUS_PENDING = "pending"
	STATUS_CONFIRMED = "confirmed"

	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_CONFIRMED, "Confirmed"),
	]

	registration = models.OneToOneField(
		ActivityRegistration,
		on_delete=models.CASCADE,
		related_name="payment_check",
	)
	status = models.CharField(
		max_length=20,
		choices=STATUS_CHOICES,
		default=STATUS_PENDING,
	)
	checked_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	checked_at = models.DateTimeField(null=True, blank=True)
	payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
	qr_code = models.ImageField(upload_to='payment_qrs/', blank=True, null=True)

	def mark_confirmed(self, user):
		self.status = self.STATUS_CONFIRMED
		self.checked_by = user
		self.checked_at = timezone.now()
		self.save(update_fields=["status", "checked_by", "checked_at"])
