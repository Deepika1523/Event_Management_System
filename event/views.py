from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Activity,
    ActivityCoordinator,
    Event,
    EventCoordinator,
    EventCoordinatorInvite,
    Profile,
)
from participant.models import ActivityRegistration, EventRegistration
from payment.models import PaymentCheck


def _can_manage_event(user, event):
    return user.is_superuser or user.is_staff or event.user_id == user.id


def _is_organizer(user):
    if not user.is_authenticated:
        return False
    return Profile.objects.filter(user=user, role="organizer").exists()


def _is_coordinator(user):
    if not user.is_authenticated:
        return False
    return Profile.objects.filter(user=user, role="coordinator").exists()


def _is_participant(user):
    if not user.is_authenticated:
        return False
    return Profile.objects.filter(user=user, role="participant").exists()


def _can_check_payment_for_registration(user, registration):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if _is_organizer(user):
        return True
    if not _is_coordinator(user):
        return False
    return ActivityCoordinator.objects.filter(
        activity=registration.activity,
        user=user,
    ).exists()


def _authenticate_for_role(request, username, password, expected_role):
    user = authenticate(request, username=username, password=password)
    if user is None:
        return None, "Invalid username or password. Please try again."

    if user.is_superuser:
        return user, None

    profile_role = (
        Profile.objects.filter(user=user).values_list("role", flat=True).first()
    )
    if profile_role != expected_role:
        return (
            None,
            f"This account is not registered as {expected_role.title()}.",
        )

    return user, None


def _extract_event_payload(request):
    data = {
        "event": request.POST.get("event") or request.GET.get("event"),
        "activity": request.POST.get("activity") or request.GET.get("activity"),
        "date_of_event": request.POST.get("date_of_event")
        or request.GET.get("date_of_event"),
        "time_of_event": request.POST.get("time_of_event")
        or request.GET.get("time_of_event"),
        "registration": request.POST.get("registration_fees")
        or request.GET.get("registration_fees")
        or request.POST.get("registration")
        or request.GET.get("registration"),
        "announcement": request.POST.get("announcement")
        or request.GET.get("announcement"),
        "coordinator_emails": request.POST.get("coordinator_emails")
        or request.GET.get("coordinator_emails"),
    }

    # For JSON API calls where request.POST is empty.
    if (
        request.content_type
        and "application/json" in request.content_type
        and not any(data.values())
    ):
        try:
            import json

            body = json.loads(request.body.decode("utf-8") or "{}")
            data = {
                "event": body.get("event"),
                "activity": body.get("activity"),
                "date_of_event": body.get("date_of_event"),
                "time_of_event": body.get("time_of_event"),
                "registration": body.get("registration_fees")
                or body.get("registration"),
                "announcement": body.get("announcement"),
                "coordinator_emails": body.get("coordinator_emails"),
            }
        except (ValueError, UnicodeDecodeError):
            return None

    return data


def _parse_coordinator_emails(raw_emails):
    if not raw_emails:
        return [], []

    emails = []
    invalid = []

    for entry in raw_emails.split(","):
        email = entry.strip()
        if not email:
            continue
        try:
            validate_email(email)
        except ValidationError:
            invalid.append(email)
            continue
        emails.append(email.lower())

    return sorted(set(emails)), invalid


def _send_coordinator_invite(request, invite):
    accept_path = reverse("accept_coordinator_invite", args=[str(invite.token)])
    accept_url = request.build_absolute_uri(accept_path)
    signup_url = request.build_absolute_uri(
        f"{reverse('signup')}?role=coordinator&next={accept_path}"
    )

    subject = f"Coordinator invite for {invite.event.event}"
    message = (
        f"You have been invited to coordinate the event: {invite.event.event}.\n\n"
        f"Accept invite: {accept_url}\n"
        f"If you need an account, sign up here: {signup_url}\n\n"
        "This invite is tied to this email address."
    )

    from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [invite.email], fail_silently=False)


def _send_activity_assignment_email(request, activity, coordinator_user):
    subject = f"Activity assignment: {activity.name}"
    dashboard_url = request.build_absolute_uri(reverse("dashboard"))
    message = (
        f"You have been assigned to coordinate the activity: {activity.name}.\n"
        f"Event: {activity.event.event}.\n\n"
        f"Open dashboard: {dashboard_url}\n"
    )
    from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [coordinator_user.email], fail_silently=False)


@csrf_exempt
@login_required
def event_list(request):
    if request.method == "GET":
        if request.user.is_superuser or request.user.is_staff:
            queryset = Event.objects.select_related("user").all().order_by("id")
        else:
            queryset = (
                Event.objects.select_related("user")
                .filter(user=request.user)
                .order_by("id")
            )

        data = [
            {
                "id": item.id,
                "user": item.user.username,
                "event": item.event,
                "activity": item.activity,
                "date_of_event": item.date_of_event,
                "time_of_event": item.time_of_event,
                "registration": item.registration,
                "registration_fees": item.registration,
                "announcement": item.announcement,
            }
            for item in queryset
        ]
        return JsonResponse({"events": data}, status=200)

    if request.method == "POST":
        if not _is_organizer(request.user):
            return JsonResponse(
                {"error": "Only organizers can create events."},
                status=403,
            )

        payload = _extract_event_payload(request)
        if payload is None:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        missing = [key for key, value in payload.items() if not value]
        missing = [key for key in missing if key not in {"announcement", "coordinator_emails"}]
        if missing:
            return JsonResponse(
                {"error": f"Missing required fields: {', '.join(missing)}."},
                status=400,
            )

        coordinator_emails_raw = payload.pop("coordinator_emails", None)
        coordinator_emails, invalid_emails = _parse_coordinator_emails(
            coordinator_emails_raw
        )
        if invalid_emails:
            return JsonResponse(
                {
                    "error": "Invalid coordinator emails.",
                    "invalid_emails": invalid_emails,
                },
                status=400,
            )

        created = Event.objects.create(user=request.user, **payload)
        invite_errors = []
        invites_sent = []
        for email in coordinator_emails:
            invite, created_invite = EventCoordinatorInvite.objects.get_or_create(
                event=created,
                email=email,
                status=EventCoordinatorInvite.STATUS_PENDING,
                defaults={"invited_by": request.user},
            )
            if not created_invite:
                invite_errors.append(f"Already invited: {email}")
                continue

            _send_coordinator_invite(request, invite)
            invites_sent.append(email)

        return JsonResponse(
            {
                "id": created.id,
                "event": created.event,
                "activity": created.activity,
                "date_of_event": created.date_of_event,
                "time_of_event": created.time_of_event,
                "registration": created.registration,
                "registration_fees": created.registration,
                "announcement": created.announcement,
                "invites_sent": invites_sent,
                "invite_errors": invite_errors,
            },
            status=201,
        )

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not _can_manage_event(request.user, event):
        return JsonResponse(
            {"error": "You do not have permission to access this event."}, status=403
        )

    if request.method == "GET":
        return JsonResponse(
            {
                "id": event.id,
                "user": event.user.username,
                "event": event.event,
                "activity": event.activity,
                "date_of_event": event.date_of_event,
                "time_of_event": event.time_of_event,
                "registration": event.registration,
                "registration_fees": event.registration,
                "announcement": event.announcement,
            },
            status=200,
        )

    if request.method in {"PUT", "PATCH"}:
        payload = _extract_event_payload(request)
        if payload is None:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        payload.pop("coordinator_emails", None)
        for key, value in payload.items():
            if value:
                setattr(event, key, value)
        event.save()

        return JsonResponse(
            {
                "id": event.id,
                "event": event.event,
                "activity": event.activity,
                "date_of_event": event.date_of_event,
                "time_of_event": event.time_of_event,
                "registration": event.registration,
                "announcement": event.announcement,
            },
            status=200,
        )

    if request.method == "DELETE":
        event.delete()
        return JsonResponse({"message": "Event deleted successfully."}, status=200)

    return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])


def role_based_user_page(request):
    if request.user.is_authenticated and request.user.is_superuser:
        role = "Admin"
        message = "You have full administrative control over the platform."
    elif request.user.is_authenticated:
        profile_role = (
            Profile.objects.filter(user=request.user)
            .values_list("role", flat=True)
            .first()
        )
        if profile_role == "coordinator":
            role = "Coordinator"
            message = "You can coordinate schedules, activities, and registrations."
        elif profile_role == "organizer":
            role = "Organizer"
            message = "You can manage events, announcements, and platform operations."
        elif profile_role == "participant":
            role = "Participant"
            message = "You can browse, register, and track your event participation."
        elif request.user.is_staff:
            role = "Staff"
            message = "You can manage event operations and participant updates."
        else:
            role = "User"
            message = "You can browse, register, and track your event participation."
    else:
        role = "Guest"
        message = "Sign up to create events and manage your registrations."

    return render(
        request,
        "index.html",
        {
            "role": role,
            "message": message,
        },
    )


def signup(request):
    user_model = get_user_model()
    valid_roles = {key for key, _ in Profile.ROLE_CHOICES}
    selected_role = request.GET.get("role")
    if selected_role not in valid_roles:
        selected_role = "participant"

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        role = request.POST.get("role") or ""
        errors = []

        if not username:
            errors.append("Username is required.")
        if not email:
            errors.append("Email is required.")
        if not password1:
            errors.append("Password is required.")
        if password1 != password2:
            errors.append("Passwords do not match.")
        if role not in valid_roles:
            errors.append("Please select a valid role.")
        if username and user_model.objects.filter(username=username).exists():
            errors.append("Username is already taken.")
        if email and user_model.objects.filter(email=email).exists():
            errors.append("Email is already registered.")

        if not errors:
            user = user_model.objects.create_user(
                username=username,
                email=email,
                password=password1,
            )
            Profile.objects.create(user=user, role=role)
            login(request, user)
            return redirect("user")

        return render(
            request,
            "registration/signup.html",
            {
                "errors": errors,
                "username": username,
                "email": email,
                "selected_role": role,
                "roles": Profile.ROLE_CHOICES,
            },
        )

    return render(
        request,
        "registration/signup.html",
        {
            "selected_role": selected_role,
            "roles": Profile.ROLE_CHOICES,
        },
    )


def unified_login(request):
    """Unified login page for all user roles."""
    selected_role = request.GET.get("role", "coordinator")
    context = {
        "selected_role": selected_role,
        "username": "",
        "error_message": None,
    }

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        role = request.POST.get("role") or "coordinator"

        if not username or not password:
            context["error_message"] = "Username and password are required."
            context["username"] = username
            context["selected_role"] = role
        else:
            user, error_message = _authenticate_for_role(
                request,
                username,
                password,
                role,
            )
            if user is not None:
                login(request, user)
                return redirect("user")
            else:
                context["error_message"] = error_message
                context["username"] = username
                context["selected_role"] = role

    return render(request, "registration/unified_login.html", context)


def role_login(request, expected_role, template_name):
    context = {
        "username": "",
        "error_message": None,
    }

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        context["username"] = username

        if not username or not password:
            context["error_message"] = "Username and password are required."
            return render(request, template_name, context)

        user, error_message = _authenticate_for_role(
            request,
            username,
            password,
            expected_role,
        )
        if user is None:
            context["error_message"] = error_message
            return render(request, template_name, context)

        login(request, user)
        return redirect("user")

    return render(request, template_name, context)


@login_required
def manage_events(request):
    can_create_event = _is_organizer(request.user)

    if request.method == "POST":
        if not can_create_event:
            messages.error(request, "Only organizers can create events.")
            return redirect("manage_events")

        event_name = (request.POST.get("event") or "").strip()
        activity = (request.POST.get("activity") or "").strip()
        date_of_event = (request.POST.get("date_of_event") or "").strip()
        time_of_event = (request.POST.get("time_of_event") or "").strip()
        registration_fees = (request.POST.get("registration_fees") or "").strip()
        coordinator_emails_raw = (
            request.POST.get("coordinator_emails") or ""
        ).strip()

        if not all(
            [
                event_name,
                activity,
                date_of_event,
                time_of_event,
                registration_fees,
            ]
        ):
            messages.error(request, "All fields are required to create an event.")
        else:
            coordinator_emails, invalid_emails = _parse_coordinator_emails(
                coordinator_emails_raw
            )
            if invalid_emails:
                messages.error(
                    request,
                    "Invalid coordinator emails: " + ", ".join(invalid_emails),
                )
                return redirect("manage_events")

            created_event = Event.objects.create(
                user=request.user,
                event=event_name,
                activity=activity,
                date_of_event=date_of_event,
                time_of_event=time_of_event,
                registration=registration_fees,
                announcement="",
            )

            invites_sent = []
            already_invited = []
            for email in coordinator_emails:
                invite, created_invite = EventCoordinatorInvite.objects.get_or_create(
                    event=created_event,
                    email=email,
                    status=EventCoordinatorInvite.STATUS_PENDING,
                    defaults={"invited_by": request.user},
                )
                if not created_invite:
                    already_invited.append(email)
                    continue

                _send_coordinator_invite(request, invite)
                invites_sent.append(email)

            if invites_sent:
                messages.success(
                    request,
                    "Coordinator invites sent to: " + ", ".join(invites_sent),
                )
            if already_invited:
                messages.info(
                    request,
                    "Already invited: " + ", ".join(already_invited),
                )

            messages.success(request, "Event created successfully.")
            return redirect("manage_events")

    if request.user.is_superuser or request.user.is_staff:
        events = Event.objects.select_related("user").all().order_by("-id")
    else:
        events = (
            Event.objects.select_related("user")
            .filter(user=request.user)
            .order_by("-id")
        )

    return render(
        request,
        "events/manage_events.html",
        {"events": events, "can_create_event": can_create_event},
    )


@login_required
def manage_activities(request):
    can_manage = _is_organizer(request.user) or request.user.is_staff or request.user.is_superuser

    if request.method == "POST":
        if not can_manage:
            messages.error(request, "Only organizers can create activities.")
            return redirect("manage_activities")

        event_id = request.POST.get("event_id")
        activity_name = (request.POST.get("activity_name") or "").strip()
        registration_fee = (request.POST.get("registration_fee") or "").strip()
        coordinator_email = (request.POST.get("coordinator_email") or "").strip().lower()

        if not event_id or not activity_name or not registration_fee:
            messages.error(request, "Event, activity name, and fee are required.")
            return redirect("manage_activities")

        event = get_object_or_404(Event, id=event_id)
        if not _can_manage_event(request.user, event):
            messages.error(request, "You do not have permission to add activities for this event.")
            return redirect("manage_activities")

        activity, created = Activity.objects.get_or_create(
            event=event,
            name=activity_name,
            defaults={"registration_fee": registration_fee},
        )
        if not created:
            messages.info(request, "This activity already exists for the event.")
            return redirect("manage_activities")

        if coordinator_email:
            coordinator_user = get_user_model().objects.filter(email=coordinator_email).first()
            if not coordinator_user:
                messages.error(request, "Coordinator email does not match any user account.")
            elif not Profile.objects.filter(user=coordinator_user, role="coordinator").exists():
                messages.error(request, "This user is not registered as a coordinator.")
            elif not EventCoordinator.objects.filter(event=event, user=coordinator_user).exists():
                messages.error(request, "Coordinator must accept the event invite before assignment.")
            else:
                ActivityCoordinator.objects.get_or_create(
                    activity=activity,
                    user=coordinator_user,
                )
                _send_activity_assignment_email(request, activity, coordinator_user)

        messages.success(request, "Activity created successfully.")
        return redirect("manage_activities")

    if request.user.is_superuser or request.user.is_staff:
        events = Event.objects.all().order_by("-id")
        activities = Activity.objects.select_related("event").order_by("-id")
    else:
        events = Event.objects.filter(user=request.user).order_by("-id")
        activities = Activity.objects.select_related("event").filter(
            event__user=request.user
        ).order_by("-id")

    activity_coordinators = ActivityCoordinator.objects.select_related("user", "activity")
    activity_coordinator_map = {}
    for row in activity_coordinators:
        activity_coordinator_map.setdefault(row.activity_id, []).append(row.user)

    activity_rows = []
    for activity in activities:
        coordinators = activity_coordinator_map.get(activity.id, [])
        coordinator_names = ", ".join(user.username for user in coordinators) or "-"
        activity_rows.append(
            {
                "activity": activity,
                "coordinator_names": coordinator_names,
            }
        )

    return render(
        request,
        "events/manage_activities.html",
        {
            "events": events,
            "activities": activity_rows,
            "can_manage": can_manage,
        },
    )


@login_required
def delete_event(request, event_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    event = get_object_or_404(Event, id=event_id)

    if not _can_manage_event(request.user, event):
        messages.error(request, "You do not have permission to delete this event.")
        return redirect("manage_events")

    event.delete()
    messages.success(request, "Event deleted successfully.")
    return redirect("manage_events")


@login_required
def accept_coordinator_invite(request, token):
    invite = get_object_or_404(EventCoordinatorInvite, token=token)

    if invite.status == EventCoordinatorInvite.STATUS_ACCEPTED:
        messages.info(request, "This invite has already been accepted.")
        return redirect("dashboard")

    if not request.user.email:
        messages.error(request, "Your account must have an email to accept invites.")
        return redirect("dashboard")

    if request.user.email.lower() != invite.email.lower():
        messages.error(request, "This invite is for a different email address.")
        return redirect("dashboard")

    if not Profile.objects.filter(user=request.user, role="coordinator").exists():
        messages.error(request, "Only coordinator accounts can accept this invite.")
        return redirect("dashboard")

    EventCoordinator.objects.get_or_create(event=invite.event, user=request.user)
    invite.mark_accepted()
    messages.success(request, "You are now a coordinator for this event.")
    return redirect("dashboard")


@login_required
def dashboard(request):
    can_view_participant_map = _is_organizer(request.user)
    can_register = _is_participant(request.user)
    can_check_payments = (
        _is_coordinator(request.user)
        or can_view_participant_map
        or request.user.is_staff
        or request.user.is_superuser
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "register_event":
            if not can_register:
                messages.error(request, "Only participants can register for events.")
                return redirect("dashboard")

            event_id = request.POST.get("event_id")
            event = get_object_or_404(Event, id=event_id)
            _, created = EventRegistration.objects.get_or_create(
                participant=request.user,
                event=event,
            )

            if created:
                messages.success(request, "You are registered for this event.")
            else:
                messages.info(request, "You are already registered for this event.")

            return redirect("dashboard")

        if action == "register_activity":
            if not can_register:
                messages.error(request, "Only participants can register for activities.")
                return redirect("dashboard")

            activity_id = request.POST.get("activity_id")
            activity = get_object_or_404(Activity, id=activity_id)
            _, created = ActivityRegistration.objects.get_or_create(
                participant=request.user,
                activity=activity,
            )

            if created:
                messages.success(request, "You are registered for this activity.")
            else:
                messages.info(request, "You are already registered for this activity.")

            return redirect("dashboard")

        if action == "check_payment":
            if not can_check_payments:
                messages.error(request, "You do not have permission to check payments.")
                return redirect("dashboard")

            registration_id = request.POST.get("registration_id")
            registration = get_object_or_404(
                ActivityRegistration.objects.select_related("activity"),
                id=registration_id,
            )
            if not _can_check_payment_for_registration(request.user, registration):
                messages.error(
                    request,
                    "You do not have permission to check payment for this activity.",
                )
                return redirect("dashboard")
            payment, _ = PaymentCheck.objects.get_or_create(registration=registration)
            payment.mark_confirmed(request.user)
            messages.success(request, "Payment marked as confirmed.")
            return redirect("dashboard")

    events = Event.objects.select_related("user").all().order_by("-id")
    activities = Activity.objects.select_related("event").all().order_by("-id")

    if can_view_participant_map:
        registered_events = EventRegistration.objects.select_related(
            "participant", "event"
        ).all()
    else:
        registered_events = EventRegistration.objects.select_related("event").filter(
            participant=request.user
        )

    participant_registered_event_ids = set()
    if can_register:
        participant_registered_event_ids = set(
            EventRegistration.objects.filter(participant=request.user).values_list(
                "event_id", flat=True
            )
        )

    participant_registered_activity_ids = set()
    if can_register:
        participant_registered_activity_ids = set(
            ActivityRegistration.objects.filter(participant=request.user).values_list(
                "activity_id", flat=True
            )
        )

    activity_registrations = ActivityRegistration.objects.select_related(
        "participant", "activity", "activity__event"
    ).order_by("-registered_at")
    if request.user.is_staff or request.user.is_superuser:
        activity_registrations = activity_registrations.all()
    elif can_view_participant_map:
        activity_registrations = activity_registrations.filter(
            activity__event__user=request.user
        )
    elif _is_coordinator(request.user):
        activity_registrations = activity_registrations.filter(
            activity__activitycoordinator__user=request.user
        )
    else:
        activity_registrations = activity_registrations.none()

    payment_checks = PaymentCheck.objects.select_related("registration", "checked_by")
    payment_status_map = {row.registration_id: row for row in payment_checks}

    activity_registration_rows = []
    for row in activity_registrations:
        payment_check = payment_status_map.get(row.id)
        activity_registration_rows.append(
            {
                "registration": row,
                "payment_status": payment_check.status if payment_check else "pending",
                "checked_by": payment_check.checked_by if payment_check else None,
                "checked_at": payment_check.checked_at if payment_check else None,
            }
        )

    return render(
        request,
        "dashboard.html",
        {
            "events": events,
            "activities": activities,
            "registered_events": registered_events,
            "activity_registrations": activity_registration_rows,
            "can_view_participant_map": can_view_participant_map,
            "can_register": can_register,
            "can_check_payments": can_check_payments,
            "participant_registered_event_ids": participant_registered_event_ids,
            "participant_registered_activity_ids": participant_registered_activity_ids,
        },
    )
