from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from event.models import Profile
from participant.models import ActivityRegistration
from payment.models import PaymentCheck


def index(request):
    return HttpResponse("Payment app")


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


def _can_check_payment_for_registration(user, registration):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if _is_organizer(user):
        return registration.activity.event.user_id == user.id
    if _is_head_coordinator(user):
        return True
    if _is_event_coordinator(user):
        return registration.activity.event.eventcoordinator_set.filter(user=user).exists()
    if not _is_coordinator(user):
        return False
    return ActivityCoordinator.objects.filter(
        activity=registration.activity,
        user=user,
    ).exists()


@login_required
def payment_status(request):
    can_view = (
        _is_organizer(request.user)
        or _is_coordinator(request.user)
        or request.user.is_staff
        or request.user.is_superuser
    )
    if not can_view:
        messages.error(request, "You do not have permission to view payments.")
        return redirect("events:dashboard")

    if request.method == "POST":
        registration_id = request.POST.get("registration_id")
        registration = get_object_or_404(
            ActivityRegistration.objects.select_related("activity", "activity__event"),
            id=registration_id,
        )
        if not _can_check_payment_for_registration(request.user, registration):
            messages.error(
                request,
                "You do not have permission to check payment for this activity.",
            )
            return redirect("payment_status")

        payment, _ = PaymentCheck.objects.get_or_create(registration=registration)
        payment.mark_confirmed(request.user)
        messages.success(request, "Payment marked as confirmed.")
        return redirect("payment_status")

    activity_registrations = ActivityRegistration.objects.select_related(
        "participant", "activity", "activity__event"
    ).order_by("-registered_at")

    if request.user.is_staff or request.user.is_superuser:
        activity_registrations = activity_registrations.all()
    elif _is_organizer(request.user):
        activity_registrations = activity_registrations.filter(
            activity__event__user=request.user
        )
    else:
        activity_registrations = activity_registrations.filter(
            activity__activitycoordinator__user=request.user
        )

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
        "payment/status.html",
        {"activity_registrations": activity_registration_rows},
    )
