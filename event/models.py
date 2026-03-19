from django.db import models
from django.conf import settings

class Event(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=200)
    activity = models.CharField(max_length=200)
    registration = models.CharField(max_length=200)
    announcement = models.CharField(max_length=200)
 