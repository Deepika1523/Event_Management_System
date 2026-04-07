from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from event.models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    """Ensure a Profile exists for each user. Default role is 'participant'."""
    if created:
        # Create profile only when missing
        Profile.objects.get_or_create(user=instance, defaults={"role": "participant"})
*** End Patch