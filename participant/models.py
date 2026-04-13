
import uuid
from django.conf import settings
from django.db import models
from event.models import Activity, Event
from django.contrib.auth.models import User


class Participant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.email


# class EventRegistration(models.Model):
# 	participant = models.ForeignKey(
# 		settings.AUTH_USER_MODEL,
# 		on_delete=models.CASCADE,
# 		related_name="event_registrations",
# 	)
# 	event = models.ForeignKey(
# 		Event,
# 		on_delete=models.CASCADE,
# 		related_name="event_registrations",
# 	)
# 	# Participation type: individual or team (kept for compatibility with older schema)
# 	PARTICIPATION_INDIVIDUAL = 'individual'
# 	PARTICIPATION_TEAM = 'team'
# 	PARTICIPATION_CHOICES = [
# 		(PARTICIPATION_INDIVIDUAL, 'Individual'),
# 		(PARTICIPATION_TEAM, 'Team'),
# 	]
# 	participation_type = models.CharField(max_length=32, choices=PARTICIPATION_CHOICES, default=PARTICIPATION_INDIVIDUAL)
# 	form_data = models.JSONField(blank=True, null=True)
# 	registered_at = models.DateTimeField(auto_now_add=True)

# 	class Meta:
# 		unique_together = ("participant", "event")
# 		ordering = ["-registered_at"]

# 	def __str__(self):
# 		return f"{self.participant.username} -> {self.event.event}"




class ActivityRegistration(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

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
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("participant", "activity")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.participant.username} -> {self.activity.name}"


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
    # Participation type: individual or team (kept for compatibility with older schema)
    PARTICIPATION_INDIVIDUAL = "individual"
    PARTICIPATION_TEAM = "team"
    PARTICIPATION_AUDIENCE = "audience"
    PARTICIPATION_CHOICES = [
        (PARTICIPATION_INDIVIDUAL, "Individual"),
        (PARTICIPATION_TEAM, "Team"),
        (PARTICIPATION_AUDIENCE, "Audience"),
    ]
    participation_type = models.CharField(
        max_length=32,
        choices=PARTICIPATION_CHOICES,
        default=PARTICIPATION_INDIVIDUAL,
    )
    form_data = models.JSONField(blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("participant", "event")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.participant.username} -> {self.event.event}"


class AttendanceRecord(models.Model):
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"

    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
    ]

    registration = models.OneToOneField(
        ActivityRegistration,
        on_delete=models.CASCADE,
        related_name="attendance",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_scans",
    )
    scanned_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attendance {self.registration_id} ({self.status})"


class LeaderboardEntry(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries",
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries",
    )
    score = models.IntegerField(default=0)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leaderboard_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("activity", "participant")

    def __str__(self):
        return f"{self.activity.name} - {self.participant.username}: {self.score}"


class Certificate(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("activity", "participant")

    def __str__(self):
        return f"Certificate {self.participant.username} -> {self.activity.name}"


class TeamRegistration(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="team_registrations",
    )
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_registrations",
    )
    team_name = models.CharField(max_length=200)
    member_names = models.TextField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("activity", "leader")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.team_name} ({self.activity.name})"
