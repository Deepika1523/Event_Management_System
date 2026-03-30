from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="participant-index"),
    path("gate-pass/<int:event_id>/", views.gate_pass_pdf, name="participant_gate_pass"),
    path(
        "certificate/<int:activity_id>/",
        views.certificate_pdf,
        name="participant_certificate",
    ),
    path(
        "event/<int:event_id>/activities/",
        views.activity_selection,
        name="activity_selection",
    ),
]
