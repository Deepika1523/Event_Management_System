from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from event.models import Event



# Simple static pages for About, Activities, Schedule, Gallery, Contact
from django.views.generic import TemplateView

def index(request):
    return render(request, "index.html")

def about(request):
    return render(request, "about.html")

def activities(request):
    return render(request, "activities.html")

def schedule(request):
    return render(request, "schedule.html")

def gallery(request):
    return render(request, "gallery.html")

def contact(request):
    return render(request, "contact.html")


def event_site(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    template_map = {
        "classic": "website/event_template_classic.html",
        "bold": "website/event_template_bold.html",
        "minimal": "website/event_template_minimal.html",
    }
    template_name = template_map.get(event.template_choice, template_map["classic"])
    coordinator_login_url = f"{reverse('unified_login')}?role=coordinator"
    participant_login_url = f"{reverse('unified_login')}?role=participant"
    can_create_activity = (
        request.user.is_authenticated
        and (request.user.is_superuser or event.user_id == request.user.id)
    )
    admin_activity_url = reverse("event_dashboard", args=[event.id])
    organizer_activity_url = f"{reverse('manage_activities')}?event_id={event.id}"

    return render(
        request,
        template_name,
        {
            "event": event,
            "coordinator_login_url": coordinator_login_url,
            "participant_login_url": participant_login_url,
            "can_create_activity": can_create_activity,
            "admin_activity_url": admin_activity_url,
            "organizer_activity_url": organizer_activity_url,
        },
    )
