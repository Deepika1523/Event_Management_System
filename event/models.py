from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
import uuid
from .models_eventimage import EventImage


class Event(models.Model):
    CATEGORY_CHOICES = [
        ("concert", "Concert"),
        ("workshop", "Workshop"),
        ("fest", "Fest"),
        ("other", "Other"),
    ]

    TEMPLATE_CHOICES = [
        ("classic", "Classic"),
        ("bold", "Bold"),
        ("minimal", "Minimal"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=200)
    activity = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    schedule = models.TextField(blank=True)
    activities_overview = models.TextField(blank=True)
    rules = models.TextField(blank=True)
    date_of_event = models.DateField(null=True, blank=True)
    time_of_event = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Map URL or coordinates")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, blank=True)
    registration = models.CharField(max_length=200)
    last_registration_date = models.DateField(null=True, blank=True)
    announcement = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=200, blank=True)
    registration_form_fields = models.TextField(blank=True)
    past_event_history = models.TextField(blank=True)
    about_page = models.TextField(blank=True, help_text="Rich text for About page")
    schedule_page = models.TextField(blank=True, help_text="Rich text for Schedule page")
    activities_page = models.TextField(blank=True, help_text="Rich text for Activities page")
    contact_page = models.TextField(blank=True, help_text="Rich text for Contact page")
    template_choice = models.CharField(
        max_length=30,
        choices=TEMPLATE_CHOICES,
        default="classic",
    )
    image_url = models.CharField(max_length=500, blank=True, help_text="Event image URL")

    class Meta:
        ordering = ["-date_of_event"]

    def __str__(self):
        return self.event


class Activity(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    prize = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    rules = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    registration_fee = models.CharField(max_length=200, blank=True, default="Free")
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_team_event = models.BooleanField(default=False)
    team_size = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "name")
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.event.event} - {self.name}"


class Profile(models.Model):
    ROLE_CHOICES = [
        ("coordinator", "Coordinator"),
        ("organizer", "Organizer"),
        ("participant", "Participant"),
    ]

    COORDINATOR_ROLE_CHOICES = [
        ("activity", "Activity Coordinator"),
        ("event", "Event Coordinator"),
        ("head", "Head Coordinator"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    coordinator_role = models.CharField(
        max_length=20,
        choices=COORDINATOR_ROLE_CHOICES,
        blank=True,
        null=True,
    )

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
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="coordinators")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"{self.event.event} - {self.user.username}"


# Per-activity registration form field model
class ActivityRegistrationFormField(models.Model):
    FIELD_TYPES = [
        ("text", "Text"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("number", "Number"),
        ("textarea", "Textarea"),
        ("choice", "Choice"),
        ("date", "Date"),
        ("file", "File Upload"),
    ]
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, related_name="registration_fields")
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(default=True)
    choices = models.TextField(blank=True, help_text="Comma-separated options for 'choice' type.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("activity", "label")

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()}) for {self.activity.name}"


# Stores participant responses to custom registration forms
class ActivityRegistrationFormResponse(models.Model):
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, related_name="registration_responses")
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_responses")
    field = models.ForeignKey(ActivityRegistrationFormField, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="registration_uploads/", blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.participant} - {self.activity} - {self.field.label}"


# ActivityCoordinator model for per-activity coordinators
class ActivityCoordinator(models.Model):
    activity = models.ForeignKey('Activity', on_delete=models.CASCADE, related_name='activity_coordinators')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("activity", "user")

    def __str__(self):
        return f"{self.activity.name} - {self.user.username}"
