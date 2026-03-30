from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from event.models import Event, Activity
from participant.models import Certificate, EventRegistration, ActivityRegistration
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
@login_required
def activity_selection(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    # Only allow if user is registered for the event
    if not EventRegistration.objects.filter(participant=request.user, event=event).exists():
        return HttpResponseForbidden("You are not registered for this event.")

    activities = Activity.objects.filter(event=event)
    if request.method == "POST":
        selected_ids = request.POST.getlist("activities")
        selected_activities = activities.filter(id__in=selected_ids)
        if not selected_activities:
            messages.error(request, "wrong")
            # Preserve previous selections
            registered_ids = set(int(i) for i in selected_ids)
            return render(request, "events/activity_selection.html", {
                "event": event,
                "activities": activities,
                "registered_ids": registered_ids,
            })
        # Remove previous registrations for this event/participant
        ActivityRegistration.objects.filter(participant=request.user, activity__event=event).delete()
        # Register for selected activities
        for activity in selected_activities:
            ActivityRegistration.objects.create(participant=request.user, activity=activity)
        # Calculate fee
        total_fee = 0
        for activity in selected_activities:
            try:
                total_fee += int(activity.registration_fee)
            except Exception:
                pass
        if len(selected_activities) > 2:
            total_fee += 50
        # Optionally allow user to override amount
        custom_amount = request.POST.get("custom_amount")
        if custom_amount:
            try:
                total_fee = int(custom_amount)
            except Exception:
                pass
        messages.success(request, f"Registered for {len(selected_activities)} activities. Total fee: {total_fee}")
        return redirect("participant-index")

    # For GET, show form
    registered_ids = set(ActivityRegistration.objects.filter(participant=request.user, activity__event=event).values_list("activity_id", flat=True))
    return render(request, "events/activity_selection.html", {
        "event": event,
        "activities": activities,
        "registered_ids": registered_ids,
    })


def index(request):
    return HttpResponse("Participant app")


def _pdf_response(filename, title, lines):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 60, title)

    pdf.setFont("Helvetica", 12)
    y = height - 100
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 18
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = height - 60

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


@login_required
def gate_pass_pdf(request, event_id):
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        return HttpResponse("Event not found.", status=404)

    registration = EventRegistration.objects.filter(
        participant=request.user,
        event=event,
    ).first()
    if not registration:
        return HttpResponseForbidden("You are not registered for this event.")

    # Assume status field exists on registration (add if missing)
    status = getattr(registration, 'status', 'approved')  # fallback to approved if not present

    lines = [
        f"Participant: {request.user.username}",
        f"Event: {event.event}",
        f"Date: {event.date_of_event}",
        f"Time: {event.time_of_event}",
        f"Venue: {event.venue}",
        f"Registration Status: {status.title()}",
    ]
    filename = f"gate_pass_event_{event.id}.pdf"

    # QR code functionality removed
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 60, "Event Gate Pass")

    pdf.setFont("Helvetica", 12)
    y = height - 100
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 18
        if y < 120:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = height - 60

    # QR code drawing removed

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


@login_required
def certificate_pdf(request, activity_id):
    certificate = Certificate.objects.select_related("activity").filter(
        activity_id=activity_id,
        participant=request.user,
    ).first()
    if certificate is None:
        return HttpResponseForbidden("Certificate not available.")

    activity = certificate.activity
    lines = [
        f"Participant: {request.user.username}",
        f"Activity: {activity.name}",
        f"Event: {activity.event.event}",
        f"Issued: {certificate.issued_at}",
        f"Certificate ID: {certificate.certificate_id}",
    ]
    filename = f"certificate_{certificate.certificate_id}.pdf"
    return _pdf_response(filename, "Participation Certificate", lines)
