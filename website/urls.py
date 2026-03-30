from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="website-index"),
    path("about/", views.about, name="about"),
    path("activities/", views.activities, name="activities"),
    path("schedule/", views.schedule, name="schedule"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
    path("event/<int:event_id>/", views.event_site, name="event_site"),
]
