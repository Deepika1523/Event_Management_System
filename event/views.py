
# Activity Registration Form View
from participant.models import ActivityRegistration
from django.contrib.auth.decorators import login_required

@login_required
def activity_registration_form(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    if not _is_participant(request.user):
        messages.error(request, "Only participants can register for activities.")
        return redirect("events:dashboard")

    # If you have custom fields for activities, parse them here
    fields = []
    if hasattr(activity, "registration_fields"):
        fields = activity.registration_fields.all().order_by("order", "id")

    if request.method == "POST":
        form_data = {}
        missing = []
        for field in fields:
            value = (request.POST.get(field.label) or "").strip()
            if field.required and not value:
                missing.append(field.label)
            form_data[field.label] = value

        if missing:
            messages.error(request, f"Please provide required fields: {', '.join(missing)}.")
        else:
            registration, created = ActivityRegistration.objects.get_or_create(
                participant=request.user,
                activity=activity,
                defaults={"form_data": form_data},
            )
            if not created:
                registration.form_data = form_data
                registration.save(update_fields=["form_data"])
                messages.info(request, "Registration updated.")
            else:
                messages.success(request, "You are registered for this activity.")
            return redirect("events:dashboard")

    return render(
        request,
        "events/activity_registration.html",
        {
            "activity": activity,
            "fields": fields,
        },
    )
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

@login_required
@require_GET
def generate_gate_pass(request, registration_id):
    from participant.models import EventRegistration
    registration = get_object_or_404(EventRegistration, id=registration_id, participant=request.user)
    event = registration.event
    # Generate QR code (contains registration ID and user info)
    qr_data = f"REG-{registration.id}|USER-{request.user.id}|EVENT-{event.id}"
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    # Generate PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, height - 40 * mm, f"Gate Pass for {event.event}")
    c.setFont("Helvetica", 12)
    c.drawString(30 * mm, height - 55 * mm, f"Participant: {request.user.get_full_name() or request.user.username}")
    c.drawString(30 * mm, height - 65 * mm, f"Event Date: {event.date_of_event}")
    c.drawString(30 * mm, height - 75 * mm, f"Venue: {event.venue}")
    # Draw QR code
    c.drawInlineImage(qr_buffer, 30 * mm, height - 120 * mm, 50 * mm, 50 * mm)
    c.setFont("Helvetica", 10)
    c.drawString(30 * mm, height - 130 * mm, f"Registration ID: {registration.id}")
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename=gate_pass_{registration.id}.pdf'
    return response
import base64
import json
import os
import uuid
import urllib.error
import urllib.request
from io import BytesIO

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook

from .models import (
    Activity,
    Event,
    EventCoordinator,
    EventCoordinatorInvite,
    Profile,
    ActivityRegistrationFormField,
    ActivityRegistrationFormResponse,
    ActivityCoordinator,
)
from participant.models import (
    ActivityRegistration,
    AttendanceRecord,
    Certificate,
    EventRegistration,
    LeaderboardEntry,
    TeamRegistration,
)
from payment.models import PaymentCheck
from notification.services import (
    send_activity_registration_email,
    send_event_registration_email,
)


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


def _get_coordinator_role(user):
    if not user.is_authenticated:
        return None
    role = (
        Profile.objects.filter(user=user, role="coordinator")
        .values_list("coordinator_role", flat=True)
        .first()
    )
    if role is None and _is_coordinator(user):
        return "activity"
    return role


def _is_head_coordinator(user):
    return _get_coordinator_role(user) == "head"


def _is_event_coordinator(user):
    return _get_coordinator_role(user) == "event"


def _is_activity_coordinator(user):
    return _get_coordinator_role(user) == "activity"


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
    if _is_head_coordinator(user):
        return True
    if _is_event_coordinator(user):
        return EventCoordinator.objects.filter(
            event=registration.activity.event,
            user=user,
        ).exists()
    if not _is_coordinator(user):
        return False
    return ActivityCoordinator.objects.filter(
        activity=registration.activity,
        user=user,
    ).exists()


def _is_event_coordinator_for_event(user, event):
    if not user.is_authenticated:
        return False
    if _is_head_coordinator(user):
        return True
    if not _is_event_coordinator(user):
        return False
    return EventCoordinator.objects.filter(event=event, user=user).exists()


def _is_activity_coordinator_for_activity(user, activity):
    if not user.is_authenticated:
        return False
    if _is_head_coordinator(user):
        return True
    if _is_event_coordinator(user):
        return EventCoordinator.objects.filter(event=activity.event, user=user).exists()
    if not _is_activity_coordinator(user):
        return False
    return ActivityCoordinator.objects.filter(activity=activity, user=user).exists()


def _is_activity_coordinator_for_event(user, event):
    if not user.is_authenticated:
        return False
    if _is_head_coordinator(user):
        return True
    if _is_event_coordinator(user):
        return EventCoordinator.objects.filter(event=event, user=user).exists()
    if not _is_activity_coordinator(user):
        return False
    return ActivityCoordinator.objects.filter(activity__event=event, user=user).exists()


def _can_manage_event_activities(user, event):
    return (
        user.is_superuser
        or user.is_staff
        or (event.user_id == user.id)
        or _is_event_coordinator_for_event(user, event)
    )


def _can_view_event_participants(user, event):
    return (
        user.is_superuser
        or user.is_staff
        or event.user_id == user.id
        or _is_event_coordinator_for_event(user, event)
    )


def _can_manage_activity(user, activity):
    if user.is_superuser or user.is_staff:
        return True
    if _is_organizer(user) and activity.event.user_id == user.id:
        return True
    return _is_activity_coordinator_for_activity(user, activity)


def _can_view_event_dashboard(user, event):
    if not user.is_authenticated:
        return False
    return _can_manage_event_activities(user, event) or _is_activity_coordinator_for_event(
        user,
        event,
    )


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


def _get_openai_key():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return api_key


def _openai_post(endpoint, payload):
    api_key = _get_openai_key()
    url = f"https://api.openai.com/v1/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    request_obj = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI API error: {exc.code} {body}") from exc


def _extract_response_text(data):
    output = data.get("output", []) if isinstance(data, dict) else []
    parts = []
    for item in output:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    return "\n".join([part for part in parts if part]).strip()


def _parse_json_object(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _parse_registration_fields(text):
    fields = []
    if not text:
        return fields

    for line in text.splitlines():
        label = line.strip()
        if not label:
            continue
        required = label.endswith("*")
        if required:
            label = label[:-1].strip()
        if not label:
            continue
        fields.append(
            {
                "key": f"field_{len(fields) + 1}",
                "label": label,
                "required": required,
            }
        )
    return fields


def _normalize_registration_fields(raw_text):
    if not raw_text:
        return "", None

    cleaned = []
    seen = set()
    for line in raw_text.splitlines():
        label = line.strip()
        if not label:
            continue
        if label.endswith("*"):
            label = label[:-1].strip() + "*"
        if not label or label == "*":
            return None, "Registration field labels cannot be empty."
        lower_label = label.lower()
        if lower_label in seen:
            return None, "Duplicate registration field labels are not allowed."
        seen.add(lower_label)
        cleaned.append(label)

    return "\n".join(cleaned), None


def _extract_event_payload(request):
    data = {
        "event": request.POST.get("event") or request.GET.get("event"),
        "activity": request.POST.get("activity") or request.GET.get("activity"),
        "description": request.POST.get("description") or request.GET.get("description"),
        "tagline": request.POST.get("tagline") or request.GET.get("tagline"),
        "schedule": request.POST.get("schedule") or request.GET.get("schedule"),
        "activities_overview": request.POST.get("activities_overview")
        or request.GET.get("activities_overview"),
        "rules": request.POST.get("rules") or request.GET.get("rules"),
        "date_of_event": request.POST.get("date_of_event")
        or request.GET.get("date_of_event"),
        "time_of_event": request.POST.get("time_of_event")
        or request.GET.get("time_of_event"),
        "venue": request.POST.get("venue") or request.GET.get("venue"),
        "category": request.POST.get("category") or request.GET.get("category"),
        "registration": request.POST.get("registration_fees")
        or request.GET.get("registration_fees")
        or request.POST.get("registration")
        or request.GET.get("registration"),
        "announcement": request.POST.get("announcement")
        or request.GET.get("announcement"),
        "contact_info": request.POST.get("contact_info")
        or request.GET.get("contact_info"),
        "image_url": request.POST.get("image_url") or request.GET.get("image_url"),
        "template_choice": request.POST.get("template_choice")
        or request.GET.get("template_choice"),
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
                "description": body.get("description"),
                "tagline": body.get("tagline"),
                "schedule": body.get("schedule"),
                "activities_overview": body.get("activities_overview"),
                "rules": body.get("rules"),
                "date_of_event": body.get("date_of_event"),
                "time_of_event": body.get("time_of_event"),
                "venue": body.get("venue"),
                "category": body.get("category"),
                "registration": body.get("registration_fees")
                or body.get("registration"),
                "announcement": body.get("announcement"),
                "contact_info": body.get("contact_info"),
                "image_url": body.get("image_url"),
                "template_choice": body.get("template_choice"),
            }
        except (ValueError, UnicodeDecodeError):
            return None

    return data


def _send_activity_invite_email(request, invite):
    accept_path = reverse("accept_activity_invite", args=[str(invite.token)])
    accept_url = request.build_absolute_uri(accept_path)
    signup_url = request.build_absolute_uri(
        f"{reverse('signup')}?role=coordinator&next={accept_path}"
    )

    subject = f"Activity invite for {invite.activity.name}"
    message = (
        f"You have been invited to coordinate the activity: {invite.activity.name}.\n"
        f"Event: {invite.activity.event.event}.\n\n"
        f"Accept invite: {accept_url}\n"
        f"If you need an account, sign up here: {signup_url}\n\n"
        "This invite is tied to this email address."
    )

    from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [invite.email], fail_silently=False)


def _send_event_invite_email(request, invite):
    accept_path = reverse("accept_event_invite", args=[str(invite.token)])
    accept_url = request.build_absolute_uri(accept_path)
    signup_url = request.build_absolute_uri(
        f"{reverse('signup')}?role=coordinator&next={accept_path}"
    )

    subject = f"Event coordinator invite for {invite.event.event}"
    message = (
        f"You have been invited to coordinate the event: {invite.event.event}.\n\n"
        f"Accept invite: {accept_url}\n"
        f"If you need an account, sign up here: {signup_url}\n\n"
        "This invite is tied to this email address."
    )

    from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [invite.email], fail_silently=False)


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
                "description": item.description,
                "tagline": item.tagline,
                "schedule": item.schedule,
                "activities_overview": item.activities_overview,
                "rules": item.rules,
                "date_of_event": item.date_of_event,
                "time_of_event": item.time_of_event,
                "venue": item.venue,
                "category": item.category,
                "registration": item.registration,
                "registration_fees": item.registration,
                "announcement": item.announcement,
                "contact_info": item.contact_info,
                "image_url": item.image_url,
                "template_choice": item.template_choice,
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
        missing = [
            key
            for key in missing
            if key
            not in {
                "announcement",
                "tagline",
                "schedule",
                "activities_overview",
                "rules",
            }
        ]
        if missing:
            return JsonResponse(
                {"error": f"Missing required fields: {', '.join(missing)}."},
                status=400,
            )

        created = Event.objects.create(user=request.user, **payload)

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
                "description": event.description,
                "tagline": event.tagline,
                "schedule": event.schedule,
                "activities_overview": event.activities_overview,
                "rules": event.rules,
                "date_of_event": event.date_of_event,
                "time_of_event": event.time_of_event,
                "venue": event.venue,
                "category": event.category,
                "registration": event.registration,
                "registration_fees": event.registration,
                "announcement": event.announcement,
                "contact_info": event.contact_info,
                "image_url": event.image_url,
                "template_choice": event.template_choice,
            },
            status=200,
        )

    if request.method in {"PUT", "PATCH"}:
        payload = _extract_event_payload(request)
        if payload is None:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        for key, value in payload.items():
            if value:
                setattr(event, key, value)
        event.save()

        return JsonResponse(
            {
                "id": event.id,
                "event": event.event,
                "activity": event.activity,
                "description": event.description,
                "tagline": event.tagline,
                "schedule": event.schedule,
                "activities_overview": event.activities_overview,
                "rules": event.rules,
                "date_of_event": event.date_of_event,
                "time_of_event": event.time_of_event,
                "registration": event.registration,
                "announcement": event.announcement,
                "venue": event.venue,
                "category": event.category,
                "contact_info": event.contact_info,
                "image_url": event.image_url,
                "template_choice": event.template_choice,
            },
            status=200,
        )

    if request.method == "DELETE":
        event.delete()
        return JsonResponse({"message": "Event deleted successfully."}, status=200)

    return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])


@login_required
def ai_generate_event_content(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not _is_organizer(request.user):
        return JsonResponse({"error": "Only organizers can generate content."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = {}

    title = (payload.get("event") or payload.get("title") or "").strip()
    category = (payload.get("category") or payload.get("type") or "").strip()
    venue = (payload.get("venue") or "").strip()
    date_of_event = (payload.get("date_of_event") or "").strip()

    if not title or not category:
        return JsonResponse(
            {"error": "Event title and category are required."},
            status=400,
        )

    prompt = (
        "You are an assistant for an event organizer. Generate event content as JSON.\n"
        "Return ONLY valid JSON with this shape:\n"
        "{\n"
        "  \"tagline\": string,\n"
        "  \"description\": string,\n"
        "  \"schedule\": [string],\n"
        "  \"activities\": [string],\n"
        "  \"rules\": [string]\n"
        "}\n"
        "Keep it concise and upbeat. Avoid placeholders.\n"
        f"Event title: {title}\n"
        f"Event category/type: {category}\n"
        f"Venue (if known): {venue or 'Unknown'}\n"
        f"Date (if known): {date_of_event or 'Unknown'}\n"
    )

    try:
        response = _openai_post(
            "responses",
            {
                "model": "gpt-4.1-mini",
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                ],
                "temperature": 0.7,
            },
        )
        text = _extract_response_text(response)
        if not text:
            raise RuntimeError("Empty response from OpenAI.")
        data = _parse_json_object(text)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse(
        {
            "tagline": data.get("tagline", ""),
            "description": data.get("description", ""),
            "schedule": data.get("schedule", []),
            "activities": data.get("activities", []),
            "rules": data.get("rules", []),
        }
    )


@login_required
def ai_generate_event_banner(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not _is_organizer(request.user):
        return JsonResponse({"error": "Only organizers can generate banners."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        payload = {}

    title = (payload.get("event") or payload.get("title") or "").strip()
    category = (payload.get("category") or payload.get("type") or "").strip()

    if not title or not category:
        return JsonResponse(
            {"error": "Event title and category are required."},
            status=400,
        )

    prompt = (
        "Create a premium event banner image with a clean, modern look. "
        "No text, no logos, no watermarks. "
        f"Theme: {category}. Event: {title}. "
        "Use a cinematic atmosphere with soft lighting and rich detail."
    )

    try:
        response = _openai_post(
            "images",
            {
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": "1024x1024",
                "response_format": "b64_json",
            },
        )
        data_list = response.get("data", []) if isinstance(response, dict) else []
        if not data_list:
            raise RuntimeError("Empty image response from OpenAI.")
        image_b64 = data_list[0].get("b64_json")
        if not image_b64:
            raise RuntimeError("Image data missing from OpenAI response.")

        image_bytes = base64.b64decode(image_b64)
        filename = f"events/ai/banner_{uuid.uuid4().hex}.png"
        saved_path = default_storage.save(filename, ContentFile(image_bytes))
        image_url = default_storage.url(saved_path)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"image_url": image_url})


def role_based_user_page(request):
    organizer_exists = Profile.objects.filter(role="organizer").exists()
    if request.user.is_authenticated and request.user.is_superuser:
        role = "Super Admin (Platform Owner)"
        message = "You can manage organizers, templates, and all events across the platform."
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
            "organizer_exists": organizer_exists,
        },
    )


def signup(request):
    user_model = get_user_model()
    valid_roles = {key for key, _ in Profile.ROLE_CHOICES}
    valid_coordinator_roles = {key for key, _ in Profile.COORDINATOR_ROLE_CHOICES}
    selected_role = request.GET.get("role")
    if selected_role not in valid_roles:
        selected_role = "participant"

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        role = request.POST.get("role") or ""
        coordinator_role = request.POST.get("coordinator_role") or ""
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
        if role == "coordinator" and coordinator_role not in valid_coordinator_roles:
            errors.append("Please select a valid coordinator role.")
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
            Profile.objects.create(
                user=user,
                role=role,
                coordinator_role=coordinator_role if role == "coordinator" else None,
            )
            login(request, user)
            return redirect("events:user")

        return render(
            request,
            "registration/signup.html",
            {
                "errors": errors,
                "username": username,
                "email": email,
                "selected_role": role,
                "selected_coordinator_role": coordinator_role,
                "roles": Profile.ROLE_CHOICES,
                "coordinator_roles": Profile.COORDINATOR_ROLE_CHOICES,
            },
        )

    return render(
        request,
        "registration/signup.html",
        {
            "selected_role": selected_role,
            "roles": Profile.ROLE_CHOICES,
            "coordinator_roles": Profile.COORDINATOR_ROLE_CHOICES,
        },
    )


def unified_login(request):
    """Unified login page for all user roles."""
    selected_role = request.GET.get("role", "coordinator")
    signup_selected_role = request.GET.get("signup_role", "organizer")
    context = {
        "selected_role": selected_role,
        "signup_selected_role": signup_selected_role,
        "roles": Profile.ROLE_CHOICES,
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
                return redirect("events:user")
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
        return redirect("events:user")

    return render(request, template_name, context)


@login_required
def manage_events(request):
    can_create_event = _is_organizer(request.user)

    if request.method == "POST":
        if not can_create_event:
            messages.error(request, "Only organizers can create events.")
            return redirect("events:manage_events")

        event_name = (request.POST.get("event") or "").strip()
        description = (request.POST.get("description") or "").strip()
        tagline = (request.POST.get("tagline") or "").strip()
        schedule = (request.POST.get("schedule") or "").strip()
        activities_overview = (request.POST.get("activities_overview") or "").strip()
        rules = (request.POST.get("rules") or "").strip()
        date_of_event = (request.POST.get("date_of_event") or "").strip()
        time_of_event = (request.POST.get("time_of_event") or "").strip()
        venue = (request.POST.get("venue") or "").strip()
        category = (request.POST.get("category") or "").strip()
        registration_fees = (request.POST.get("registration_fees") or "").strip()
        contact_info = (request.POST.get("contact_info") or "").strip()
        location = (request.POST.get("location") or "").strip()
        past_event_history = (request.POST.get("past_event_history") or "").strip()
        last_registration_date = (request.POST.get("last_registration_date") or "").strip()
        image_url = (request.POST.get("image_url") or "").strip()
        template_choice = (request.POST.get("template_choice") or "").strip()
        images = request.FILES.getlist("images")
        registration_form_fields = (
            request.POST.get("registration_form_fields") or ""
        ).strip()
        registration_form_fields, fields_error = _normalize_registration_fields(
            registration_form_fields
        )

        # Custom registration fields are optional, so do not require them
        if not all(
            [
                event_name,
                description,
                date_of_event,
                time_of_event,
                venue,
                location,
                category,
                registration_fees,
                contact_info,
                template_choice,
                last_registration_date,
            ]
        ):
            messages.error(request, "Please fill out all required event details.")
        elif fields_error:
            messages.error(request, fields_error)
        elif not images and not image_url:
            messages.error(request, "Please provide at least one event image file or image URL.")
        elif category not in dict(Event.CATEGORY_CHOICES):
            messages.error(request, "Please select a valid category.")
        elif template_choice not in dict(Event.TEMPLATE_CHOICES):
            messages.error(request, "Please select a valid website template.")
        else:
            created_event = Event.objects.create(
                user=request.user,
                event=event_name,
                activity="",
                description=description,
                tagline=tagline,
                schedule=schedule,
                activities_overview=activities_overview,
                rules=rules,
                date_of_event=date_of_event,
                time_of_event=time_of_event,
                venue=venue,
                location=location,
                category=category,
                registration=registration_fees,
                announcement="",
                contact_info=contact_info,
                registration_form_fields=registration_form_fields,
                past_event_history=past_event_history,
                image_url=image_url,
                template_choice=template_choice,
                last_registration_date=last_registration_date,
            )
            # Save multiple images
            from .models_eventimage import EventImage
            for img in images:
                EventImage.objects.create(event=created_event, image=img)

            messages.success(request, "Event created successfully.")
            return redirect("event_site", event_id=created_event.id)

    if request.user.is_superuser or request.user.is_staff:
        events = Event.objects.all().order_by("-id")
    elif _is_organizer(request.user):
        events = Event.objects.filter(user=request.user).order_by("-id")
    else:
        events = Event.objects.none()

    return render(
        request,
        "events/manage_events.html",
        {
            "can_create_event": can_create_event,
            "category_choices": Event.CATEGORY_CHOICES,
            "template_choices": Event.TEMPLATE_CHOICES,
            "events": events,
        },
    )


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    can_edit = request.user.is_superuser or request.user.is_staff or (
        _is_organizer(request.user) and event.user_id == request.user.id
    )
    if not can_edit:
        messages.error(request, "You do not have permission to edit this event.")
        return redirect("events:manage_events")

    if request.method == "POST":
        event_name = (request.POST.get("event") or "").strip()
        description = (request.POST.get("description") or "").strip()
        tagline = (request.POST.get("tagline") or "").strip()
        schedule = (request.POST.get("schedule") or "").strip()
        activities_overview = (request.POST.get("activities_overview") or "").strip()
        rules = (request.POST.get("rules") or "").strip()
        date_of_event = (request.POST.get("date_of_event") or "").strip()
        time_of_event = (request.POST.get("time_of_event") or "").strip()
        venue = (request.POST.get("venue") or "").strip()
        category = (request.POST.get("category") or "").strip()
        registration_fees = (request.POST.get("registration_fees") or "").strip()
        contact_info = (request.POST.get("contact_info") or "").strip()
        image_url = (request.POST.get("image_url") or "").strip()
        template_choice = (request.POST.get("template_choice") or "").strip()
        location = (request.POST.get("location") or "").strip()
        last_registration_date = (request.POST.get("last_registration_date") or "").strip()
        image_file = request.FILES.get("image")
        registration_form_fields = (
            request.POST.get("registration_form_fields") or ""
        ).strip()
        registration_form_fields, fields_error = _normalize_registration_fields(
            registration_form_fields
        )

        if not all(
            [
                event_name,
                description,
                date_of_event,
                time_of_event,
                venue,
                location,
                category,
                registration_fees,
                contact_info,
                template_choice,
                last_registration_date,
            ]
        ):
            messages.error(request, "Please fill out all required event details.")
        elif fields_error:
            messages.error(request, fields_error)
        elif category not in dict(Event.CATEGORY_CHOICES):
            messages.error(request, "Please select a valid category.")
        elif template_choice not in dict(Event.TEMPLATE_CHOICES):
            messages.error(request, "Please select a valid website template.")
        else:
            event.event = event_name
            event.description = description
            event.tagline = tagline
            event.schedule = schedule
            event.activities_overview = activities_overview
            event.rules = rules
            event.date_of_event = date_of_event
            event.time_of_event = time_of_event
            event.venue = venue
            event.location = location
            event.category = category
            event.registration = registration_fees
            event.contact_info = contact_info
            event.image_url = image_url
            event.template_choice = template_choice
            event.registration_form_fields = registration_form_fields
            event.last_registration_date = last_registration_date
            if image_file:
                event.image = image_file
            event.save()

            messages.success(request, "Event updated successfully.")
            return redirect("events:edit_event", event_id=event.id)

    return render(
        request,
        "events/edit_event.html",
        {
            "event": event,
            "category_choices": Event.CATEGORY_CHOICES,
            "template_choices": Event.TEMPLATE_CHOICES,
        },
    )


@login_required
def event_registration_form(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not _is_participant(request.user):
        messages.error(request, "Only participants can register for events.")
        return redirect("events:dashboard")

    fields = _parse_registration_fields(event.registration_form_fields)

    if request.method == "POST":
        form_data = {}
        missing = []
        for field in fields:
            value = (request.POST.get(field["key"]) or "").strip()
            if field["required"] and not value:
                missing.append(field["label"])
            form_data[field["label"]] = value

        if missing:
            messages.error(
                request,
                f"Please provide required fields: {', '.join(missing)}.",
            )
        else:
            registration, created = EventRegistration.objects.get_or_create(
                participant=request.user,
                event=event,
                defaults={"form_data": form_data},
            )
            if not created:
                registration.form_data = form_data
                registration.save(update_fields=["form_data"])
                messages.info(request, "Registration updated.")
            else:
                messages.success(request, "You are registered for this event.")
                send_event_registration_email(request.user, event)
            return redirect("events:dashboard")

    return render(
        request,
        "events/event_registration.html",
        {
            "event": event,
            "fields": fields,
        },
    )


@login_required
def export_event_excel(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    can_export = request.user.is_superuser or request.user.is_staff
    if not can_export:
        can_export = _is_organizer(request.user) and event.user_id == request.user.id
    # Allow activity coordinators to export if they coordinate any activity in this event
    if not can_export:
        is_activity_coordinator = ActivityCoordinator.objects.filter(
            user=request.user, activity__event=event
        ).exists()
        can_export = is_activity_coordinator
    if not can_export:
        return HttpResponse("You do not have permission to export this event.", status=403)

    activity_coordinators = ActivityCoordinator.objects.select_related("user")
    activity_coordinator_map = {}
    for row in activity_coordinators:
        activity_coordinator_map.setdefault(row.activity_id, []).append(row.user)

    activity_registration_counts = {
        row["activity_id"]: row["count"]
        for row in ActivityRegistration.objects.filter(activity__event=event)
        .values("activity_id")
        .annotate(count=models.Count("id"))
    }
    team_registration_counts = {
        row["activity_id"]: row["count"]
        for row in TeamRegistration.objects.filter(activity__event=event)
        .values("activity_id")
        .annotate(count=models.Count("id"))
    }

    wb = Workbook()
    # Add a new sheet for Activity Participants
    ws5 = wb.create_sheet("Activity Participants")
    ws5.append([
        "Activity Name",
        "Participant Username",
        "Participant Email",
        "Registered At",
        "Event Name",
        "Event Date",
        "Start Time",
        "End Time",
        "Registration Fee",
        "Team Event",
        "Team Size",
    ])
    activities = Activity.objects.select_related("event").filter(event=event).order_by("id")
    for activity in activities:
        # Ensure registrations are filtered by both activity and event
        registrations = ActivityRegistration.objects.select_related("participant", "activity").filter(activity=activity, activity__event=event)
        for reg in registrations:
            ws5.append([
                activity.name,
                reg.participant.username,
                reg.participant.email,
                reg.registered_at.isoformat(),
                activity.event.event,
                activity.event.date_of_event.isoformat() if activity.event.date_of_event else "",
                activity.start_time.isoformat() if activity.start_time else "",
                activity.end_time.isoformat() if activity.end_time else "",
                activity.registration_fee,
                "Yes" if activity.is_team_event else "No",
                activity.team_size or "",
            ])
        if not registrations.exists():
            ws5.append([
                activity.name,
                "No participants yet.", "", "", activity.event.event,
                activity.event.date_of_event.isoformat() if activity.event.date_of_event else "",
                activity.start_time.isoformat() if activity.start_time else "",
                activity.end_time.isoformat() if activity.end_time else "",
                activity.registration_fee,
                "Yes" if activity.is_team_event else "No",
                activity.team_size or "",
            ])

    # Fix event registrations export to ensure correct event
    ws = wb.active
    ws.title = "Event Registrations"
    ws.append(["Participant", "Email", "Event", "Registered At", "Form Data"])
    event_registrations = EventRegistration.objects.select_related("participant", "event").filter(event=event)
    if event_registrations.exists():
        for reg in event_registrations:
            ws.append([
                reg.participant.username,
                reg.participant.email,
                reg.event.event,
                reg.registered_at.isoformat(),
                json.dumps(reg.form_data or {}, ensure_ascii=False),
            ])
    else:
        ws.append(["No event registrations yet.", "", "", "", ""])
        if registrations.exists():
            for reg in registrations:
                ws5.append([
                    activity.name,
                    reg.participant.username,
                    reg.participant.email,
                    reg.registered_at.isoformat(),
                    activity.event.event,
                    activity.event.date_of_event.isoformat() if activity.event.date_of_event else "",
                    activity.start_time.isoformat() if activity.start_time else "",
                    activity.end_time.isoformat() if activity.end_time else "",
                    activity.registration_fee,
                    "Yes" if activity.is_team_event else "No",
                    activity.team_size or "",
                ])
        else:
            ws5.append([
                activity.name,
                "No participants yet.", "", "", activity.event.event,
                activity.event.date_of_event.isoformat() if activity.event.date_of_event else "",
                activity.start_time.isoformat() if activity.start_time else "",
                activity.end_time.isoformat() if activity.end_time else "",
                activity.registration_fee,
                "Yes" if activity.is_team_event else "No",
                activity.team_size or "",
            ])
    ws = wb.active
    ws.title = "Event Registrations"
    ws.append(["Participant", "Email", "Event", "Registered At", "Form Data"])
    event_registrations = EventRegistration.objects.select_related("participant").filter(
        event=event
    )
    if event_registrations.exists():
        for reg in event_registrations:
            ws.append(
                [
                    reg.participant.username,
                    reg.participant.email,
                    event.event,
                    reg.registered_at.isoformat(),
                    json.dumps(reg.form_data or {}, ensure_ascii=False),
                ]
            )
    else:
        ws.append(["No event registrations yet.", "", "", "", ""]) 

    ws2 = wb.create_sheet("Activities")
    ws2.append(
        [
            "Activity",
            "Event",
            "Event Date",
            "Start Time",
            "End Time",
            "Registration Fee",
            "Team Event",
            "Team Size",
            "Coordinators",
            "Registrations",
            "Teams",
        ]
    )
    activities = Activity.objects.select_related("event").filter(event=event).order_by("id")
    if activities.exists():
        for activity in activities:
            coordinators = activity_coordinator_map.get(activity.id, [])
            coordinator_names = ", ".join(user.username for user in coordinators) or "-"
            ws2.append(
                [
                    activity.name,
                    event.event,
                    event.date_of_event.isoformat() if event.date_of_event else "",
                    activity.start_time.isoformat() if activity.start_time else "",
                    activity.end_time.isoformat() if activity.end_time else "",
                    activity.registration_fee,
                    "Yes" if activity.is_team_event else "No",
                    activity.team_size or "",
                    coordinator_names,
                    activity_registration_counts.get(activity.id, 0),
                    team_registration_counts.get(activity.id, 0),
                ]
            )
    else:
        ws2.append(["No activities created yet.", "", "", "", "", "", "", "", "", "", ""]) 

    ws3 = wb.create_sheet("Activity Registrations")
    ws3.append(
        [
            "Participant",
            "Email",
            "Activity",
            "Event",
            "Event Date",
            "Time",
            "Coordinators",
            "Registered At",
            "Payment Status",
        ]
    )
    payment_map = {
        row.registration_id: row
        for row in PaymentCheck.objects.select_related("registration")
    }
    for reg in ActivityRegistration.objects.select_related(
        "participant", "activity", "activity__event"
    ).filter(activity__event=event):
        coordinators = activity_coordinator_map.get(reg.activity_id, [])
        coordinator_names = ", ".join(user.username for user in coordinators) or "-"
        time_range = ""
        if reg.activity.start_time and reg.activity.end_time:
            time_range = f"{reg.activity.start_time} - {reg.activity.end_time}"
        elif reg.activity.start_time:
            time_range = str(reg.activity.start_time)
        elif reg.activity.end_time:
            time_range = str(reg.activity.end_time)
        payment = payment_map.get(reg.id)
        ws3.append(
            [
                reg.participant.username,
                reg.participant.email,
                reg.activity.name,
                reg.activity.event.event,
                reg.activity.event.date_of_event.isoformat()
                if reg.activity.event.date_of_event
                else "",
                time_range,
                coordinator_names,
                reg.registered_at.isoformat(),
                payment.status if payment else "pending",
            ]
        )

    if ws3.max_row == 1:
        ws3.append(["No activity registrations yet.", "", "", "", "", "", "", "", ""]) 

    ws4 = wb.create_sheet("Team Registrations")
    ws4.append(
        [
            "Team Name",
            "Leader",
            "Activity",
            "Event",
            "Event Date",
            "Members",
            "Registered At",
        ]
    )
    for team in TeamRegistration.objects.select_related(
        "leader", "activity", "activity__event"
    ).filter(activity__event=event):
        ws4.append(
            [
                team.team_name,
                team.leader.username,
                team.activity.name,
                team.activity.event.event,
                team.activity.event.date_of_event.isoformat()
                if team.activity.event.date_of_event
                else "",
                team.member_names,
                team.registered_at.isoformat(),
            ]
        )

    if ws4.max_row == 1:
        ws4.append(["No team registrations yet.", "", "", "", "", "", ""]) 

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"event_{event.id}_export.xlsx"
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


@login_required
def manage_activities(request):
    is_head = _is_head_coordinator(request.user)
    is_event_coord = _is_event_coordinator(request.user)
    is_activity_coord = _is_activity_coordinator(request.user)
    can_manage = (
        _is_organizer(request.user)
        or request.user.is_staff
        or request.user.is_superuser
        or is_head
        or is_event_coord
    )
    selected_event_id = request.GET.get("event_id") or request.POST.get("event_id")
    can_view_event_names = (
        request.user.is_superuser
        or request.user.is_staff
        or _is_organizer(request.user)
        or is_head
        or is_event_coord
    )

    # Provide all events for dropdown
    if request.user.is_superuser or request.user.is_staff:
        events = Event.objects.all().order_by("-id")
    elif _is_organizer(request.user):
        events = Event.objects.filter(user=request.user).order_by("-id")
    else:
        events = Event.objects.none()

    # Provide all activities for the selected event
    activities = []
    if selected_event_id:
        activities = Activity.objects.filter(event_id=selected_event_id).order_by("start_time")

    # Collect all form fields
    form_data = {
        "event_id": request.POST.get("event_id", selected_event_id or ""),
        "activity_name": request.POST.get("activity_name", ""),
        "description": request.POST.get("description", ""),
        "rules": request.POST.get("rules", ""),
        "eligibility": request.POST.get("eligibility", ""),
        "date": request.POST.get("date", ""),
        "start_time": request.POST.get("start_time", ""),
        "end_time": request.POST.get("end_time", ""),
        "prize": request.POST.get("prize", ""),
        "max_participants": request.POST.get("max_participants", ""),
        "is_team_event": request.POST.get("is_team_event", None),
        "team_size": request.POST.get("team_size", ""),
        "coordinator_email": request.POST.get("coordinator_email", ""),
        "registration_fee": request.POST.get("registration_fee", ""),
        "registration_form_fields": request.POST.get("registration_form_fields", ""),
        # Handle file upload
        "registration_form": request.FILES.get("registration_form") if request.method == "POST" else None,
    }

    if request.method == "POST":
        # Debug output: print all POST and FILES data to console/log
        print("[DEBUG] POST data:", dict(request.POST))
        print("[DEBUG] FILES data:", dict(request.FILES))
        # Optionally, you can log this to a file or use logging module

        if not can_manage:
            messages.error(request, "Only organizers can create activities.")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        # Validate required fields
        # Check all required fields, including date and file if needed
        required_fields = ["event_id", "activity_name", "registration_fee", "start_time", "end_time", "coordinator_email", "date"]
        missing = [f for f in required_fields if not form_data.get(f)]
        if missing:
            messages.error(request, f"Missing required fields: {', '.join(missing)}. Please fill all required fields.")
            print(f"[DEBUG] Missing fields: {missing}")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        # Validate times
        import datetime
        time_format = "%H:%M"
        try:
            start_time = datetime.datetime.strptime(form_data["start_time"], time_format).time()
        except ValueError:
            messages.error(request, "Start time must be in HH:MM format (e.g., 14:30).")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })
        try:
            end_time = datetime.datetime.strptime(form_data["end_time"], time_format).time()
        except ValueError:
            messages.error(request, "End time must be in HH:MM format (e.g., 16:00).")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        # Validate team event
        is_team_event = form_data["is_team_event"] == "on"
        team_size = None
        if is_team_event:
            if not form_data["team_size"]:
                messages.error(request, "Team size is required for team events.")
                return render(request, "events/manage_activities.html", {
                    "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                    "can_view_event_names": can_view_event_names, "events": events, "activities": activities
                })
            try:
                team_size = int(form_data["team_size"])
            except ValueError:
                messages.error(request, "Team size must be a number.")
                return render(request, "events/manage_activities.html", {
                    "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                    "can_view_event_names": can_view_event_names, "events": events, "activities": activities
                })
            if team_size < 2:
                messages.error(request, "Team size must be at least 2.")
                return render(request, "events/manage_activities.html", {
                    "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                    "can_view_event_names": can_view_event_names, "events": events, "activities": activities
                })

        # Validate email
        try:
            validate_email(form_data["coordinator_email"])
        except ValidationError:
            messages.error(request, "Please enter a valid coordinator email.")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        event = get_object_or_404(Event, id=form_data["event_id"])
        if not _can_manage_event_activities(request.user, event):
            messages.error(request, "You do not have permission to add activities for this event.")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        activity, created = Activity.objects.get_or_create(
            event=event,
            name=form_data["activity_name"],
            defaults={
                "registration_fee": form_data["registration_fee"],
                "start_time": start_time,
                "end_time": end_time,
                "is_team_event": is_team_event,
                "team_size": team_size,
                # Add more fields as needed
            },
        )
        if not created:
            messages.info(request, "This activity already exists for the event.")
            return render(request, "events/manage_activities.html", {
                "form_data": form_data, "can_manage": can_manage, "selected_event_id": selected_event_id,
                "can_view_event_names": can_view_event_names, "events": events, "activities": activities
            })

        invite, created_invite = EventCoordinatorInvite.objects.get_or_create(
            event=event,
            email=form_data["coordinator_email"].lower(),
            status=EventCoordinatorInvite.STATUS_PENDING,
            defaults={"invited_by": request.user},
        )
        if not created_invite:
            messages.info(request, "Coordinator already invited for this event.")
        else:
            # Use event invite email for activity coordinator
            _send_event_invite_email(request, invite)

        messages.success(request, "Activity created successfully.")
        return redirect("events:manage_activities")

    # For GET or after error, show form with preserved data and all context
    return render(request, "events/manage_activities.html", {
        "form_data": form_data,
        "can_manage": can_manage,
        "selected_event_id": selected_event_id,
        "can_view_event_names": can_view_event_names,
        "events": events,
        "activities": activities,
    })


@login_required
def event_dashboard(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can view the event dashboard.")
        return redirect("events:dashboard")

    can_manage = _can_manage_event_activities(request.user, event)
    can_invite_event_coordinator = (
        request.user.is_superuser
        or request.user.is_staff
        or _is_head_coordinator(request.user)
        or (_is_organizer(request.user) and event.user_id == request.user.id)
    )

    if request.method == "POST":
        action = request.POST.get("action") or "add_activity"

        if action == "invite_event_coordinator":
            if not can_invite_event_coordinator:
                messages.error(request, "You do not have permission to invite event coordinators.")
                return redirect("events:event_dashboard", event_id=event_id)

            coordinator_email = (request.POST.get("event_coordinator_email") or "").strip().lower()
            if not coordinator_email:
                messages.error(request, "Coordinator email is required.")
                return redirect("events:event_dashboard", event_id=event_id)

            try:
                validate_email(coordinator_email)
            except ValidationError:
                messages.error(request, "Please enter a valid coordinator email.")
                return redirect("events:event_dashboard", event_id=event_id)

            invite, created_invite = EventCoordinatorInvite.objects.get_or_create(
                event=event,
                email=coordinator_email,
                status=EventCoordinatorInvite.STATUS_PENDING,
                defaults={"invited_by": request.user},
            )
            if not created_invite:
                messages.info(request, "Coordinator already invited for this event.")
            else:
                _send_event_invite_email(request, invite)

            messages.success(request, "Event coordinator invite sent.")
            return redirect("events:event_dashboard", event_id=event_id)

        if not can_manage:
            messages.error(request, "Only authorized coordinators can add activities.")
            return redirect("events:event_dashboard", event_id=event_id)

        activity_name = (request.POST.get("activity_name") or "").strip()
        registration_fee = (request.POST.get("registration_fee") or "").strip()
        start_time = (request.POST.get("start_time") or "").strip()
        end_time = (request.POST.get("end_time") or "").strip()
        coordinator_email = (request.POST.get("coordinator_email") or "").strip().lower()

        if not activity_name or not registration_fee or not start_time or not end_time or not coordinator_email:
            messages.error(request, "Activity name, time, fee, and coordinator email are required.")
            return redirect("events:event_dashboard", event_id=event_id)

        is_team_event = request.POST.get("is_team_event") == "on"
        team_size_value = request.POST.get("team_size")
        team_size = None
        if is_team_event:
            if not team_size_value:
                messages.error(request, "Team size is required for team events.")
                return redirect("events:event_dashboard", event_id=event_id)
            try:
                team_size = int(team_size_value)
            except ValueError:
                messages.error(request, "Team size must be a number.")
                return redirect("events:event_dashboard", event_id=event_id)
            if team_size < 2:
                messages.error(request, "Team size must be at least 2.")
                return redirect("events:event_dashboard", event_id=event_id)

        try:
            validate_email(coordinator_email)
        except ValidationError:
            messages.error(request, "Please enter a valid coordinator email.")
            return redirect("events:event_dashboard", event_id=event_id)

        activity, created = Activity.objects.get_or_create(
            event=event,
            name=activity_name,
            defaults={
                "registration_fee": registration_fee,
                "start_time": start_time,
                "end_time": end_time,
                "is_team_event": is_team_event,
                "team_size": team_size,
            },
        )
        if not created:
            messages.info(request, "This activity already exists for the event.")
            return redirect("events:event_dashboard", event_id=event_id)

        invite, created_invite = EventCoordinatorInvite.objects.get_or_create(
            event=event,
            email=coordinator_email,
            status=EventCoordinatorInvite.STATUS_PENDING,
            defaults={"invited_by": request.user},
        )
        if not created_invite:
            messages.info(request, "Coordinator already invited for this event.")
        else:
            _send_event_invite_email(request, invite)

        messages.success(request, "Activity created successfully.")
        return redirect("events:event_dashboard", event_id=event_id)

    activities = Activity.objects.select_related("event").filter(event=event).order_by("-id")
    activity_coordinators = ActivityCoordinator.objects.select_related("user", "activity")
    activity_coordinator_map = {}
    for row in activity_coordinators:
        activity_coordinator_map.setdefault(row.activity_id, []).append(row.user)

    registration_counts = {
        row["activity_id"]: row["count"]
        for row in ActivityRegistration.objects.filter(activity__event=event)
        .values("activity_id")
        .annotate(count=models.Count("id"))
    }

    activity_rows = []
    for activity in activities:
        coordinators = activity_coordinator_map.get(activity.id, [])
        coordinator_names = ", ".join(user.username for user in coordinators) or "-"
        activity_rows.append(
            {
                "activity": activity,
                "coordinator_names": coordinator_names,
                "registration_count": registration_counts.get(activity.id, 0),
            }
        )

    can_view_participants = _can_view_event_participants(request.user, event)
    if can_view_participants:
        event_registrations = EventRegistration.objects.select_related(
            "participant"
        ).filter(event=event).order_by("-registered_at")
        activity_registrations = ActivityRegistration.objects.select_related(
            "participant", "activity"
        ).filter(activity__event=event).order_by("-registered_at")
    else:
        event_registrations = EventRegistration.objects.none()
        activity_registrations = ActivityRegistration.objects.none()

    return render(
        request,
        "events/event_dashboard.html",
        {
            "event": event,
            "activities": activity_rows,
            "can_manage": can_manage,
            "can_invite_event_coordinator": can_invite_event_coordinator,
            "can_view_participants": can_view_participants,
            "event_registrations": event_registrations,
            "activity_registrations": activity_registrations,
            "event_coordinators": EventCoordinator.objects.select_related("user").filter(event=event),
        },
    )


@login_required
def delete_event(request, event_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    event = get_object_or_404(Event, id=event_id)

    if not _can_manage_event(request.user, event):
        messages.error(request, "You do not have permission to delete this event.")
        return redirect("events:manage_events")

    event.delete()
    messages.success(request, "Event deleted successfully.")
    return redirect("events:manage_events")


@login_required
def accept_activity_invite(request, token):
    invite = get_object_or_404(EventCoordinatorInvite, token=token)

    if invite.status == EventCoordinatorInvite.STATUS_ACCEPTED:
        messages.info(request, "This invite has already been accepted.")
        return redirect("events:dashboard")

    if not request.user.email:
        messages.error(request, "Your account must have an email to accept invites.")
        return redirect("events:dashboard")

    if request.user.email.lower() != invite.email.lower():
        messages.error(request, "This invite is for a different email address.")
        return redirect("events:dashboard")

    if not Profile.objects.filter(user=request.user, role="coordinator").exists():
        messages.error(request, "Only coordinator accounts can accept this invite.")
        return redirect("events:dashboard")

    ActivityCoordinator.objects.get_or_create(activity=invite.activity, user=request.user)
    invite.mark_accepted()
    messages.success(request, "You are now a coordinator for this activity.")
    return redirect("events:dashboard")


@login_required
def accept_event_invite(request, token):
    invite = get_object_or_404(EventCoordinatorInvite, token=token)

    if invite.status == EventCoordinatorInvite.STATUS_ACCEPTED:
        messages.info(request, "This invite has already been accepted.")
        return redirect("events:dashboard")

    if not request.user.email:
        messages.error(request, "Your account must have an email to accept invites.")
        return redirect("events:dashboard")

    if request.user.email.lower() != invite.email.lower():
        messages.error(request, "This invite is for a different email address.")
        return redirect("events:dashboard")

    if not Profile.objects.filter(user=request.user, role="coordinator").exists():
        messages.error(request, "Only coordinator accounts can accept this invite.")
        return redirect("events:dashboard")

    EventCoordinator.objects.get_or_create(event=invite.event, user=request.user)
    invite.mark_accepted()
    messages.success(request, "You are now a coordinator for this event.")
    return redirect("events:dashboard")


@login_required
def scan_attendance(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    qr_token = (request.POST.get("qr_token") or "").strip()
    if not qr_token:
        messages.error(request, "QR token is required.")
        return redirect("events:dashboard")

    registration = get_object_or_404(ActivityRegistration, qr_token=qr_token)
    if not _can_manage_activity(request.user, registration.activity):
        messages.error(request, "You do not have permission to mark attendance.")
        return redirect("events:dashboard")

    attendance, _ = AttendanceRecord.objects.get_or_create(registration=registration)
    attendance.status = AttendanceRecord.STATUS_PRESENT
    attendance.scanned_by = request.user
    attendance.save(update_fields=["status", "scanned_by", "scanned_at"])

    messages.success(request, "Attendance recorded.")
    return redirect("events:dashboard")


@login_required
def update_leaderboard(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    activity_id = request.POST.get("activity_id")
    participant_id = request.POST.get("participant_id")
    score_value = request.POST.get("score")

    if not activity_id or not participant_id or score_value is None:
        messages.error(request, "Activity, participant, and score are required.")
        return redirect("events:dashboard")

    activity = get_object_or_404(Activity, id=activity_id)
    if not _can_manage_activity(request.user, activity):
        messages.error(request, "You do not have permission to update the leaderboard.")
        return redirect("events:dashboard")

    try:
        score_int = int(score_value)
    except ValueError:
        messages.error(request, "Score must be a number.")
        return redirect("events:dashboard")

    entry, _ = LeaderboardEntry.objects.get_or_create(
        activity=activity,
        participant_id=participant_id,
        defaults={"score": score_int, "updated_by": request.user},
    )
    if entry.score != score_int or entry.updated_by_id != request.user.id:
        entry.score = score_int
        entry.updated_by = request.user
        entry.save(update_fields=["score", "updated_by", "updated_at"])

    messages.success(request, "Leaderboard updated.")
    return redirect("events:dashboard")


@login_required
def issue_certificate(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    activity_id = request.POST.get("activity_id")
    participant_id = request.POST.get("participant_id")

    if not activity_id or not participant_id:
        messages.error(request, "Activity and participant are required.")
        return redirect("events:dashboard")

    activity = get_object_or_404(Activity, id=activity_id)
    if not _can_manage_activity(request.user, activity):
        messages.error(request, "You do not have permission to issue certificates.")
        return redirect("events:dashboard")

    certificate, created = Certificate.objects.get_or_create(
        activity=activity,
        participant_id=participant_id,
        defaults={"issued_by": request.user},
    )
    if not created and certificate.issued_by_id != request.user.id:
        certificate.issued_by = request.user
        certificate.save(update_fields=["issued_by"])

    messages.success(request, "Certificate issued.")
    return redirect("events:dashboard")




# Organizer Dashboard (superuser only)
@login_required
def organizer_dashboard(request):
    if not request.user.is_superuser:
        return redirect('events:dashboard')
    return dashboard_context_render(request)

# Coordinator Dashboard (organizer or coordinator)
@login_required
def coordinator_dashboard(request):
    if not (_is_organizer(request.user) or _is_coordinator(request.user)):
        return redirect('events:dashboard')
    return dashboard_context_render(request)

# Participant Dashboard (all authenticated users)
@login_required
def participant_dashboard(request):
    return dashboard_context_render(request)

# Shared dashboard context logic
def dashboard_context_render(request):
    is_head = _is_head_coordinator(request.user)
    is_event_coord = _is_event_coordinator(request.user)
    is_activity_coord = _is_activity_coordinator(request.user)
    can_view_participant_map = _is_organizer(request.user) or is_head or is_event_coord
    can_register = _is_participant(request.user)
    can_view_event_dashboard = request.user.is_superuser
    can_check_payments = (
        _is_coordinator(request.user)
        or can_view_participant_map
        or request.user.is_staff
        or request.user.is_superuser
    )

    events = Event.objects.select_related("user").all().order_by("-id")
    activities = Activity.objects.select_related("event").all().order_by("-id")

    event_activity_rows = []
    if can_view_event_dashboard:
        event_rows = Event.objects.prefetch_related("activities").order_by("-id")
        for event in event_rows:
            activity_names = ", ".join(
                activity.name for activity in event.activities.all()
            )
            event_activity_rows.append(
                {
                    "event": event,
                    "activity_names": activity_names or "-",
                }
            )

    if can_view_participant_map:
        if request.user.is_superuser or request.user.is_staff or is_head:
            registered_events = EventRegistration.objects.select_related(
                "participant", "event"
            ).all()
        elif _is_organizer(request.user):
            registered_events = EventRegistration.objects.select_related(
                "participant", "event"
            ).filter(event__user=request.user)
        else:
            registered_events = EventRegistration.objects.select_related(
                "participant", "event"
            ).filter(event__eventcoordinator__user=request.user)
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

    participant_certificate_activity_ids = set()
    participant_team_activity_ids = set()
    if can_register:
        participant_certificate_activity_ids = set(
            Certificate.objects.filter(participant=request.user).values_list(
                "activity_id", flat=True
            )
        )
        participant_team_activity_ids = set(
            TeamRegistration.objects.filter(leader=request.user).values_list(
                "activity_id", flat=True
            )
        )

    activity_registrations = ActivityRegistration.objects.select_related(
        "participant", "activity", "activity__event"
    ).order_by("-registered_at")
    if request.user.is_staff or request.user.is_superuser or is_head:
        activity_registrations = activity_registrations.all()
    elif _is_organizer(request.user):
        activity_registrations = activity_registrations.filter(
            activity__event__user=request.user
        )
    elif is_event_coord:
        activity_registrations = activity_registrations.filter(
            activity__event__eventcoordinator__user=request.user
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

    coordinator_activities = Activity.objects.none()
    if request.user.is_superuser or request.user.is_staff or is_head:
        coordinator_activities = Activity.objects.all()
    elif _is_organizer(request.user):
        coordinator_activities = Activity.objects.filter(event__user=request.user)
    elif is_event_coord:
        coordinator_activities = Activity.objects.filter(
            event__eventcoordinator__user=request.user
        )
    elif is_activity_coord:
        coordinator_activities = Activity.objects.filter(
            activitycoordinator__user=request.user
        )

    coordinator_registrations = ActivityRegistration.objects.select_related(
        "participant", "activity", "activity__event"
    ).filter(activity__in=coordinator_activities)

    attendance_map = {
        row.registration_id: row
        for row in AttendanceRecord.objects.select_related("registration")
    }
    leaderboard_map = {
        (row.activity_id, row.participant_id): row
        for row in LeaderboardEntry.objects.select_related("activity", "participant")
    }
    certificate_map = {
        (row.activity_id, row.participant_id): row
        for row in Certificate.objects.select_related("activity", "participant")
    }

    coordinator_rows = []
    for row in coordinator_registrations:
        attendance = attendance_map.get(row.id)
        leaderboard = leaderboard_map.get((row.activity_id, row.participant_id))
        certificate = certificate_map.get((row.activity_id, row.participant_id))
        coordinator_rows.append(
            {
                "registration": row,
                "attendance": attendance,
                "leaderboard": leaderboard,
                "certificate": certificate,
            }
        )

    can_export_events = (
        request.user.is_superuser or request.user.is_staff or _is_organizer(request.user)
    )
    if request.user.is_superuser or request.user.is_staff:
        export_events = Event.objects.all().order_by("-id")
    elif _is_organizer(request.user):
        export_events = Event.objects.filter(user=request.user).order_by("-id")
    else:
        export_events = Event.objects.none()

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
            "participant_certificate_activity_ids": participant_certificate_activity_ids,
            "participant_team_activity_ids": participant_team_activity_ids,
            "event_activity_rows": event_activity_rows,
            "can_view_event_dashboard": can_view_event_dashboard,
            "coordinator_rows": coordinator_rows,
            "can_export_events": can_export_events,
            "export_events": export_events,
        },
    )
