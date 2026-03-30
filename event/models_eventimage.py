from django.db import models

class EventImage(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='events/images/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.event.event} ({self.id})"