# Notification/email sending utility
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

def notify_user(user, message, email_subject=None, email_body=None):
    # Create notification in DB
    Notification.objects.create(user=user, message=message)
    # Optionally send email
    if email_subject and email_body and user.email:
        send_mail(
            email_subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_event_registration_email(participant, event):
    recipients = [participant.email] if participant.email else []
    if getattr(event, "user", None) and event.user.email:
        recipients.append(event.user.email)

    if not recipients:
        return False

    subject = f"Registration confirmed: {event.event}"
    message = (
        f"Hi {participant.username},\n\n"
        f"Your registration for {event.event} is confirmed.\n"
        f"Date: {event.date_of_event}\n"
        f"Time: {event.time_of_event}\n\n"
        "Thank you."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=True,
    )
    return True


def send_activity_registration_email(participant, activity):
    recipients = [participant.email] if participant.email else []
    if getattr(activity, "event", None) and activity.event.user.email:
        recipients.append(activity.event.user.email)

    if not recipients:
        return False

    subject = f"Activity registration confirmed: {activity.name}"
    message = (
        f"Hi {participant.username},\n\n"
        f"Your registration for {activity.name} is confirmed.\n"
        f"Event: {activity.event.event}\n\n"
        "Thank you."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=True,
    )
    return True


def send_sms_placeholder(phone_number, message):
    if not phone_number:
        return False

    logger.info("SMS placeholder to %s: %s", phone_number, message)
    return True
