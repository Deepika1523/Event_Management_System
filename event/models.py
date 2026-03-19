from django.db import models
from django.conf import settings


class Event(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=200)
    activity = models.CharField(max_length=200)
    registration = models.CharField(max_length=200)
    announcement = models.CharField(max_length=200)


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
 