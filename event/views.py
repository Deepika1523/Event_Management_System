from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Event


def _can_manage_event(user, event):
	return user.is_superuser or user.is_staff or event.user_id == user.id


def _extract_event_payload(request):
	data = {
		"event": request.POST.get("event") or request.GET.get("event"),
		"activity": request.POST.get("activity") or request.GET.get("activity"),
		"registration": request.POST.get("registration") or request.GET.get("registration"),
		"announcement": request.POST.get("announcement") or request.GET.get("announcement"),
	}

	# For JSON API calls where request.POST is empty.
	if request.content_type and "application/json" in request.content_type and not any(data.values()):
		try:
			import json

			body = json.loads(request.body.decode("utf-8") or "{}")
			data = {
				"event": body.get("event"),
				"activity": body.get("activity"),
				"registration": body.get("registration"),
				"announcement": body.get("announcement"),
			}
		except (ValueError, UnicodeDecodeError):
			return None

	return data


@csrf_exempt
@login_required
def event_list(request):
	if request.method == "GET":
		if request.user.is_superuser or request.user.is_staff:
			queryset = Event.objects.select_related("user").all().order_by("id")
		else:
			queryset = Event.objects.select_related("user").filter(user=request.user).order_by("id")

		data = [
			{
				"id": item.id,
				"user": item.user.username,
				"event": item.event,
				"activity": item.activity,
				"registration": item.registration,
				"announcement": item.announcement,
			}
			for item in queryset
		]
		return JsonResponse({"events": data}, status=200)

	if request.method == "POST":
		payload = _extract_event_payload(request)
		if payload is None:
			return JsonResponse({"error": "Invalid JSON payload."}, status=400)

		missing = [key for key, value in payload.items() if not value]
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
				"registration": created.registration,
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
		return JsonResponse({"error": "You do not have permission to access this event."}, status=403)

	if request.method == "GET":
		return JsonResponse(
			{
				"id": event.id,
				"user": event.user.username,
				"event": event.event,
				"activity": event.activity,
				"registration": event.registration,
				"announcement": event.announcement,
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
	elif request.user.is_authenticated and request.user.is_staff:
		role = "Staff"
		message = "You can manage event operations and participant updates."
	elif request.user.is_authenticated:
		role = "User"
		message = "You can browse, register, and track your event participation."
	else:
		role = "Guest"
		message = "Sign in to create events and manage your registrations."

	return render(
		request,
		"index.html",
		{
			"role": role,
			"message": message,
		},
	)
