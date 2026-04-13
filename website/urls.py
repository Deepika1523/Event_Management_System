
from django.urls import path
from event import views as event_views
from . import views

urlpatterns = [
    path("login/organizer/", views.organizer_login, name="organizer_login"),
    path("login/coordinator/", views.coordinator_login, name="coordinator_login"),
    path("", views.index, name="website-index"),
    path("about/", views.about, name="about"),
    path("activities/", views.activities, name="activities"),
    path("schedule/", views.schedule, name="schedule"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
    path("event/<int:event_id>/", views.event_site, name="event_site"),

    # Dashboard and login routes are managed in the events namespace
]