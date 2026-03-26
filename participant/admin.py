from django.contrib import admin

from .models import EventRegistration


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
	list_display = ("id", "participant", "event", "registered_at")
	search_fields = ("participant__username", "event__event")
	list_filter = ("registered_at",)
