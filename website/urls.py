from django.urls import path
from event import views as event_views
from . import views

urlpatterns = [
    path("", views.index, name="website-index"),
    path("about/", views.about, name="about"),
    path("activities/", views.activities, name="activities"),
    path("schedule/", views.schedule, name="schedule"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
    path("event/<int:event_id>/", views.event_site, name="event_site"),
    # Organizer dashboard and event management
    path("organizer-dashboard/", event_views.organizer_dashboard, name="organizer_dashboard"),
    path("coordinator-dashboard/", event_views.coordinator_dashboard, name="coordinator_dashboard"),
    path("participant-dashboard/", event_views.participant_dashboard, name="participant_dashboard"),
]
