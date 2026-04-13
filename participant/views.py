from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse
from payment.models import PaymentCheck
from notification.services import notify_user
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from event.models import Event, Activity
from participant.models import ActivityRegistration
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from .models import Participant
from event.models import Event


def _handle_participant_signup(request):
    """Validate and create a participant account."""
    errors = []
    form_data = {
        "username": "",
        "fullname": "",
        "email": "",
    }

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        fullname = (request.POST.get("fullname") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""

        form_data.update({
            "username": username,
            "fullname": fullname,
            "email": email,
        })

        if not username:
            errors.append("Username is required.")
        if not fullname:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        if not password1:
            errors.append("Password is required.")
        if password1 != password2:
            errors.append("Passwords do not match.")
        if username and User.objects.filter(username__iexact=username).exists():
            errors.append("Username is already taken.")
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append("A user with this email already exists.")

        if not errors:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=fullname,
            )
            Participant.objects.create(user=user)
            login(request, user)
            return user, errors, form_data

    return None, errors, form_data

# SIGNUP
# SIGNUP
@require_http_methods(["GET", "POST"])
def participant_signup(request):

    # Multi-step registration for activity (website/activity_register.html)
    @login_required
    @require_http_methods(["GET", "POST"])
    def activity_register(request, activity_id):
        from event.models import Activity
        from participant.models import ActivityRegistration
        activity = get_object_or_404(Activity, id=activity_id)
        event = activity.event
        user = request.user
        registration = ActivityRegistration.objects.filter(activity=activity, participant=user).first()
        registration_complete = False
        download_pass_url = None
        messages_list = []

        if registration and registration.status == 'approved':
            registration_complete = True
            download_pass_url = reverse('participant:download_pass', args=[registration.id])

        if request.method == 'POST':
            # Step 1: Basic Info
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            college = request.POST.get('college', '').strip()
            # Step 2: File Upload
            id_proof = request.FILES.get('id_proof')
            photo = request.FILES.get('photo')
            # Step 3: Payment
            payment_proof = request.FILES.get('payment_proof')
            payment_reference = request.POST.get('payment_reference', '').strip()

            if not registration:
                registration = ActivityRegistration.objects.create(
                    activity=activity,
                    participant=user,
                    status='pending',
                    phone=phone,
                    email=email,
                    college=college,
                )
            # Save files if uploaded
            if id_proof:
                registration.id_proof.save(id_proof.name, id_proof)
            if photo:
                registration.photo.save(photo.name, photo)
            if payment_proof:
                # Save payment proof in PaymentCheck
                payment_check, _ = PaymentCheck.objects.get_or_create(registration=registration)
                payment_check.payment_proof.save(payment_proof.name, payment_proof)
                payment_check.save()
            if payment_reference:
                registration.payment_reference = payment_reference
            registration.save()

            # Notify user and coordinator
            notify_user(user, f"Your registration for {activity.name} is under review.",
                email_subject="Registration Submitted",
                email_body="Your application is under review. You will be updated within 24 hours via email. You will receive both the gate pass and activity pass.")
            # TODO: Notify coordinator (if needed)

            messages.success(request, "Your application is under review. You will be updated within 24 hours via email. You will receive both the gate pass and activity pass.")
            registration_complete = False

        context = {
            'activity': activity,
            'event': event,
            'registration_complete': registration_complete,
            'download_pass_url': download_pass_url,
            'messages': messages.get_messages(request),
        }
        return render(request, 'website/activity_register.html', context)

    # Pass download (PDF placeholder)
    @login_required
    def download_pass(request, registration_id):
        from participant.models import ActivityRegistration
        registration = get_object_or_404(ActivityRegistration, id=registration_id, participant=request.user)
        if registration.status != 'approved':
            return HttpResponseForbidden("Pass not available until approved.")
        # Generate PDF pass
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica-Bold", 20)
        p.drawString(100, 700, f"Event Pass for {registration.activity.name}")
        p.setFont("Helvetica", 14)
        p.drawString(100, 670, f"Name: {registration.participant.get_full_name()}")
        p.drawString(100, 650, f"Event: {registration.activity.event.event}")
        p.drawString(100, 630, f"Status: Approved")
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename="event_pass.pdf")
    user, errors, form_data = _handle_participant_signup(request)
    if user is not None:
        return redirect("events:participant_dashboard")

    return render(
        request,
        "participant/signup.html",
        {
            "errors": errors,
            **form_data,
        },
    )


def participant_signup_for_event(request, event_id):
    """Create a participant account from an event-branded signup page."""
    event = get_object_or_404(Event, id=event_id)
    user, errors, form_data = _handle_participant_signup(request)
    if user is not None:
        messages.success(request, "Your participant account has been created.")
        return redirect("events:event_website_home", event_id=event.id)

    return render(
        request,
        "website/participant_registration.html",
        {
            "event": event,
            "errors": errors,
            **form_data,
        },
    )


# LOGIN (EMAIL BASED)
def participant_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)

            if user:
                login(request, user)
                return redirect('events:participant_dashboard')
        except User.DoesNotExist:
            pass

    return render(request, 'participant/login.html')


# LOGOUT
def participant_logout(request):
    logout(request)
    return redirect('website-index')













































# @login_required
# def activity_selection(request, event_id):
#     event = get_object_or_404(Event, id=event_id)
#     # Only allow if user is registered for the event
#     if not EventRegistration.objects.filter(participant=request.user, event=event).exists():
#         return HttpResponseForbidden("You are not registered for this event.")

#     activities = Activity.objects.filter(event=event)
#     if request.method == "POST":
#         selected_ids = request.POST.getlist("activities")
#         selected_activities = activities.filter(id__in=selected_ids)
#         if not selected_activities:
#             messages.error(request, "wrong")
#             # Preserve previous selections
#             registered_ids = set(int(i) for i in selected_ids)
#             return render(request, "events/activity_selection.html", {
#                 "event": event,
#                 "activities": activities,
#                 "registered_ids": registered_ids,
#             })
#         # Remove previous registrations for this event/participant
#         ActivityRegistration.objects.filter(participant=request.user, activity__event=event).delete()
#         # Register for selected activities
#         for activity in selected_activities:
#             ActivityRegistration.objects.create(participant=request.user, activity=activity)
#         # Calculate fee
#         total_fee = 0
#         for activity in selected_activities:
#             try:
#                 total_fee += int(activity.registration_fee)
#             except Exception:
#                 pass
#         if len(selected_activities) > 2:
#             total_fee += 50
#         # Optionally allow user to override amount
#         custom_amount = request.POST.get("custom_amount")
#         if custom_amount:
#             try:
#                 total_fee = int(custom_amount)
#             except Exception:
#                 pass
#         messages.success(request, f"Registered for {len(selected_activities)} activities. Total fee: {total_fee}")
#         return redirect("participant-index")

#     # For GET, show form
#     registered_ids = set(ActivityRegistration.objects.filter(participant=request.user, activity__event=event).values_list("activity_id", flat=True))
#     return render(request, "events/activity_selection.html", {
#         "event": event,
#         "activities": activities,
#         "registered_ids": registered_ids,
#     })


# def index(request):
#     return HttpResponse("Participant app")


# def _pdf_response(filename, title, lines):
#     buffer = BytesIO()
#     pdf = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter

#     pdf.setFont("Helvetica-Bold", 18)
#     pdf.drawString(40, height - 60, title)

#     pdf.setFont("Helvetica", 12)
#     y = height - 100
#     for line in lines:
#         pdf.drawString(40, y, line)
#         y -= 18
#         if y < 60:
#             pdf.showPage()
#             pdf.setFont("Helvetica", 12)
#             y = height - 60

#     pdf.showPage()
#     pdf.save()

#     buffer.seek(0)
#     response = HttpResponse(buffer, content_type="application/pdf")
#     response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
#     return response


# @login_required
# def gate_pass_pdf(request, event_id):
#     event = Event.objects.filter(id=event_id).first()
#     if event is None:
#         return HttpResponse("Event not found.", status=404)

#     registration = EventRegistration.objects.filter(
#         participant=request.user,
#         event=event,
#     ).first()
#     if not registration:
#         return HttpResponseForbidden("You are not registered for this event.")

#     # Assume status field exists on registration (add if missing)
#     status = getattr(registration, 'status', 'approved')  # fallback to approved if not present

#     lines = [
#         f"Participant: {request.user.username}",
#         f"Event: {event.event}",
#         f"Date: {event.date_of_event}",
#         f"Time: {event.time_of_event}",
#         f"Venue: {event.venue}",
#         f"Registration Status: {status.title()}",
#     ]
#     filename = f"gate_pass_event_{event.id}.pdf"

#     # QR code functionality removed
#     buffer = BytesIO()
#     pdf = canvas.Canvas(buffer, pagesize=letter)
#     width, height = letter

#     pdf.setFont("Helvetica-Bold", 18)
#     pdf.drawString(40, height - 60, "Event Gate Pass")

#     pdf.setFont("Helvetica", 12)
#     y = height - 100
#     for line in lines:
#         pdf.drawString(40, y, line)
#         y -= 18
#         if y < 120:
#             pdf.showPage()
#             pdf.setFont("Helvetica", 12)
#             y = height - 60

#     # QR code drawing removed

#     pdf.showPage()
#     pdf.save()
#     buffer.seek(0)
#     response = HttpResponse(buffer, content_type="application/pdf")
#     response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
#     return response


# @login_required
# def certificate_pdf(request, activity_id):
#     certificate = Certificate.objects.select_related("activity").filter(
#         activity_id=activity_id,
#         participant=request.user,
#     ).first()
#     if certificate is None:
#         return HttpResponseForbidden("Certificate not available.")

#     activity = certificate.activity
#     lines = [
#         f"Participant: {request.user.username}",
#         f"Activity: {activity.name}",
#         f"Event: {activity.event.event}",
#         f"Issued: {certificate.issued_at}",
#         f"Certificate ID: {certificate.certificate_id}",
#     ]
#     filename = f"certificate_{certificate.certificate_id}.pdf"
#     return _pdf_response(filename, "Participation Certificate", lines)
