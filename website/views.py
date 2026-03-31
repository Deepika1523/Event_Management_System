
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login
def unified_login(request):
    error_message = None
    selected_role = request.GET.get("role", "")
    username = ""
    if request.method == "POST":
        selected_role = request.POST.get("role", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect based on role
            if selected_role == "organizer":
                return redirect("organizer_dashboard")
            elif selected_role == "coordinator":
                return redirect("coordinator_dashboard")
            elif selected_role == "participant":
                return redirect("participant_dashboard")
            else:
                return redirect("website-index")
        else:
            error_message = "Invalid username or password."
    return render(request, "registration/unified_login.html", {
        "error_message": error_message,
        "selected_role": selected_role,
        "username": username,
    })

from event.models import Event



# Simple static pages for About, Activities, Schedule, Gallery, Contact
from django.views.generic import TemplateView

def index(request):
    """Homepage showing all events"""
    events = Event.objects.all().order_by('-date_of_event')
    context = {
        'events': events,
    }
    return render(request, "index.html", context)

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
    coordinator_login_url = reverse('events:coordinator_login')
    participant_login_url = reverse('events:participant_login')
    can_create_activity = (
        request.user.is_authenticated
        and (request.user.is_superuser or event.user_id == request.user.id)
    )
    admin_activity_url = reverse("events:event_dashboard", args=[event.id])
    organizer_activity_url = f"{reverse('events:manage_activities')}?event_id={event.id}"

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
