from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

import uuid


class Event(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=200)
    activity = models.CharField(max_length=200)
    date_of_event = models.DateField(null=True, blank=True)
    time_of_event = models.TimeField(null=True, blank=True)
    registration = models.CharField(max_length=200)
    announcement = models.CharField(max_length=200)


class Activity(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    registration_fee = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "name")

    def __str__(self):
        return f"{self.event.event} - {self.name}"


class Profile(models.Model):
    ROLE_CHOICES = [
        ("coordinator", "Coordinator"),
        ("organizer", "Organizer"),
        ("participant", "Participant"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class EventCoordinatorInvite(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_coordinator_invites",
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "email"],
                condition=Q(status="pending"),
                name="unique_pending_invite",
            )
        ]

    def mark_accepted(self):
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_at"])

    def __str__(self):
        return f"Invite {self.email} for {self.event}"


class EventCoordinator(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"{self.user.username} -> {self.event}"


class ActivityCoordinator(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("activity", "user")

    def __str__(self):
        return f"{self.user.username} -> {self.activity}"
