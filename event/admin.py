from django.contrib import admin

from .models import (
	Activity,
	Event,
	EventCoordinator,
	EventCoordinatorInvite,
	Profile,
	ActivityRegistrationFormField,
	ActivityRegistrationFormResponse
)
from .forms import EventAdminForm


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	form = EventAdminForm
	list_display = ("name", "user", "category", "template_choice", "date_of_event")
	list_filter = ("category", "template_choice")
	search_fields = ("name", "event", "user__username", "user__email")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "role", "organizer_events")
	list_filter = ("role",)
	search_fields = ("user__username", "user__email")

	def organizer_events(self, obj):
		if obj.role != "organizer":
			return "-"
		events = Event.objects.filter(user=obj.user).values_list("event", flat=True)
		return ", ".join(events) if events else "-"

	organizer_events.short_description = "Events"


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
	list_display = ("name", "event", "registration_fee", "start_time", "end_time")
	search_fields = ("name", "event__event")
	list_filter = ("event",)


@admin.register(EventCoordinator)
class EventCoordinatorAdmin(admin.ModelAdmin):
	list_display = ("event", "user", "added_at")
	search_fields = ("event__event", "user__username", "user__email")
	list_filter = ("event",)


@admin.register(EventCoordinatorInvite)
class EventCoordinatorInviteAdmin(admin.ModelAdmin):
	list_display = ("event", "email", "status", "created_at", "accepted_at")
	search_fields = ("event__event", "email")
	list_filter = ("status", "event")


@admin.register(ActivityRegistrationFormField)
class ActivityRegistrationFormFieldAdmin(admin.ModelAdmin):
    list_display = ("activity", "label", "field_type", "required", "order")
    list_filter = ("activity", "field_type", "required")
    search_fields = ("label", "activity__name")


@admin.register(ActivityRegistrationFormResponse)
class ActivityRegistrationFormResponseAdmin(admin.ModelAdmin):
    list_display = ("activity", "participant", "field", "value", "file", "submitted_at")
    list_filter = ("activity", "field")
    search_fields = ("participant__user__username", "field__label", "activity__name")


