from django.contrib import admin

from .models import ActivityRegistration, Participant


@admin.register(ActivityRegistration)
class ActivityRegistrationAdmin(admin.ModelAdmin):
	list_display = ("id", "participant", "activity", "status", "registered_at")
	search_fields = ("participant__username", "participant__email", "activity__name")
	list_filter = ("status", "registered_at")


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "phone")
	search_fields = ("user__username", "user__email", "phone")
