from django.urls import path

# Register a namespace so templates can use the 'events:' URL namespace
app_name = 'events'
from participant import views as participant_views
from . import views, event_pdf_views, pure_views

urlpatterns = [
    path("create/step2/", views.step2_activities, name="step2_activities"),
    path("create/step3/", views.step3_registration_form, name="step3_registration_form"),
    path("create/step4/", views.step4_coordinators, name="step4_coordinators"),
    path("create/step5/", views.step5_website_setup, name="step5_website_setup"),
    path("create/complete/", views.event_creation_complete, name="event_creation_complete"),
    # ...existing code...
    path("", views.role_based_user_page, name="home"),
    path("dashboard/", views.participant_dashboard, name="dashboard"),
    path("login/", views.unified_login, name="unified_login"),
    path("signup/participant/", views.participant_signup, name="participant_signup"),
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
    path("activities/<int:activity_id>/edit/", views.edit_activity, name="edit_activity"),
    path("activities/<int:activity_id>/delete/", views.delete_activity, name="delete_activity"),
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
    path("events/<int:event_id>/report.pdf", views.event_report_pdf, name="event_report_pdf"),
    path("registrations/<int:registration_id>/summary.pdf", views.registration_summary_pdf, name="registration_summary_pdf"),
    path("reports/export/", views.export_role_reports_excel, name="export_role_reports_excel"),
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
    # Public website views
    path("event/<int:event_id>/", views.event_website_home, name="event_website_home"),
    path("event/<int:event_id>/activities/", views.event_website_activities, name="event_website_activities"),
    path("event/<int:event_id>/schedule/", views.event_website_schedule, name="event_website_schedule"),
    path("event/<int:event_id>/gallery/", views.event_website_gallery, name="event_website_gallery"),
    path("event/<int:event_id>/contact/", views.event_website_contact, name="event_website_contact"),
    path(
        "event/<int:event_id>/participant-registration/",
        participant_views.participant_signup_for_event,
        name="event_participant_signup",
    ),
    path("activity/<int:activity_id>/register/", views.activity_register, name="activity_register"),
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
    path("login/participant/", views.participant_login, name="participant_login"),
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
    path("events/<int:event_id>/activities.pdf/", event_pdf_views.event_activities_pdf, name="event_activities_pdf"),
    path("invite-coordinator/", views.invite_coordinator, name="invite_coordinator"),
    # Coordinator: approve/reject registrations
    path("registrations/<int:registration_id>/approve/", views.approve_registration, name="approve_registration"),
    path("registrations/<int:registration_id>/reject/", views.reject_registration, name="reject_registration"),
    # Coordinator: QR scanner page (camera UI)
    path("coordinator/scanner/", views.qr_scanner_page, name="qr_scanner_page"),
    # Coordinator: participant list per activity
    path("activities/<int:activity_id>/participants/", views.activity_participants, name="activity_participants"),
    # Participant: download certificate PDF
    path("certificate/<uuid:certificate_id>/download/", views.download_certificate, name="download_certificate"),
    # Participant: activity gate pass PDF (approved only)
    path("activity-gate-pass/<int:registration_id>/", views.generate_activity_gate_pass, name="generate_activity_gate_pass"),


    path("create/step1/", views.create_event_step1, name="create_event_step1"),
    path("create/step2/", views.step2_activities, name="step2_activities"),
    path("create/step3/", views.step3_registration_form, name="step3_registration_form"),
    path("create/step4/", views.step4_coordinators, name="step4_coordinators"),
    path("create/step5/", views.step5_website_setup, name="step5_website_setup"),
    path("create/complete/", views.event_creation_complete, name="event_creation_complete"),

    # Pure EMS (No JS) routes
    path("pure/dashboard/", pure_views.OrganizerLandingView.as_view(), name="pure_dashboard"),
    path("pure/create/step1/", pure_views.Step1DetailsView.as_view(), name="pure_step1_details"),
    path("pure/create/step1/<int:event_id>/", pure_views.Step1DetailsView.as_view(), name="pure_step1_details_edit"),
    path("pure/create/step2/<int:event_id>/", pure_views.Step2ActivitiesView.as_view(), name="pure_step2_activities"),
]
