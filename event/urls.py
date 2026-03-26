from django.urls import path
from . import views

urlpatterns = [
    path("", views.role_based_user_page, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("login/", views.unified_login, name="unified_login"),
    path("manage-events/", views.manage_events, name="manage_events"),
    path("manage-activities/", views.manage_activities, name="manage_activities"),
    path("manage-events/delete/<int:event_id>/", views.delete_event, name="delete_event"),
    path(
        "invites/accept/<uuid:token>/",
        views.accept_coordinator_invite,
        name="accept_coordinator_invite",
    ),
    path("events/", views.event_list, name="event_create_or_list"),
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("user/", views.role_based_user_page, name="user"),
    path(
        "login/coordinator/",
        views.role_login,
        {"expected_role": "coordinator", "template_name": "registration/coordinator_login.html"},
        name="coordinator_login",
    ),
    path(
        "login/organizer/",
        views.role_login,
        {"expected_role": "organizer", "template_name": "registration/organizer_login.html"},
        name="organizer_login",
    ),
    path(
        "login/participant/",
        views.role_login,
        {"expected_role": "participant", "template_name": "registration/participant_login.html"},
        name="participant_login",
    ),
    path("signup/", views.signup, name="signup"),
]
