from django.urls import path

# Register a namespace so templates can use the 'events:' URL namespace
app_name = 'events'
from . import views

urlpatterns = [
    path("", views.role_based_user_page, name="home"),
    path("dashboard/", views.participant_dashboard, name="dashboard"),
    path("login/", views.unified_login, name="unified_login"),
    path("manage-events/", views.manage_events, name="manage_events"),
    path("manage-events/edit/<int:event_id>/", views.edit_event, name="edit_event"),
    path(
        "manage-events/ai-generate/",
        views.ai_generate_event_content,
        name="ai_generate_event_content",
    ),
    path(
        "manage-events/ai-generate-banner/",
        views.ai_generate_event_banner,
        name="ai_generate_event_banner",
    ),
    path("manage-activities/", views.manage_activities, name="manage_activities"),
    path("events/<int:event_id>/dashboard/", views.event_dashboard, name="event_dashboard"),
    path(
        "events/<int:event_id>/register/",
        views.event_registration_form,
        name="event_registration_form",
    ),
    path(
        "events/<int:event_id>/export/",
        views.export_event_excel,
        name="export_event_excel",
    ),
    path("manage-events/delete/<int:event_id>/", views.delete_event, name="delete_event"),
    path(
        "invites/activities/accept/<uuid:token>/",
        views.accept_activity_invite,
        name="accept_activity_invite",
    ),
    path(
        "invites/events/accept/<uuid:token>/",
        views.accept_event_invite,
        name="accept_event_invite",
    ),
    path("coordinator/attendance/scan/", views.scan_attendance, name="scan_attendance"),
    path(
        "coordinator/leaderboard/update/",
        views.update_leaderboard,
        name="update_leaderboard",
    ),
    path(
        "coordinator/certificates/issue/",
        views.issue_certificate,
        name="issue_certificate",
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
    path(
        "activities/<int:activity_id>/register/",
        views.activity_registration_form,
        name="activity_registration_form",
    ),
    path("gate-pass/<int:registration_id>/", views.generate_gate_pass, name="generate_gate_pass"),
    path("organizer-dashboard/", views.organizer_dashboard, name="organizer_dashboard"),
    path("coordinator-dashboard/", views.coordinator_dashboard, name="coordinator_dashboard"),
    path("participant-dashboard/", views.participant_dashboard, name="participant_dashboard"),
]
