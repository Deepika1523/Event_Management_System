from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from .models import Event, Activity, Profile, ActivityCoordinator
from .pure_forms import OrganizerEventForm, OrganizerActivityForm, RegistrationFormFieldForm, PureCoordinatorForm

class OrganizerLandingView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "pure_ems/dashboard.html"
    context_object_name = "events"

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user).order_by("-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_organizer'] = Profile.objects.filter(user=self.request.user, role="organizer").exists()
        return context

class Step1DetailsView(LoginRequiredMixin, View):
    def get(self, request, event_id=None):
        instance = None
        if event_id:
            instance = get_object_or_404(Event, id=event_id, user=request.user)
        form = OrganizerEventForm(instance=instance)
        return render(request, "pure_ems/step1_details.html", {"form": form, "event_id": event_id})

    def post(self, request, event_id=None):
        instance = None
        if event_id:
            instance = get_object_or_404(Event, id=event_id, user=request.user)
        
        form = OrganizerEventForm(request.POST, instance=instance)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.is_draft = True  # Always draft during creation
            # Ensure required Model fields that aren't in the form have fallback values
            if not hasattr(event, 'event') or not event.event:
                event.event = event.name
            event.save()
            messages.success(request, "Event details saved.")
            return redirect("events:pure_step2_activities", event_id=event.id)
        
        return render(request, "pure_ems/step1_details.html", {"form": form, "event_id": event_id})

class Step2ActivitiesView(LoginRequiredMixin, View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, user=request.user)
        activities = event.activities.all()
        form = OrganizerActivityForm()
        return render(request, "pure_ems/step2_activities.html", {
            "event": event,
            "activities": activities,
            "form": form
        })

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, user=request.user)
        form = OrganizerActivityForm(request.POST)
        
        if "next_step" in request.POST:
            if event.activities.exists():
                return redirect("events:pure_step3_form_builder", event_id=event.id)
            else:
                messages.error(request, "Please add at least one activity.")
        elif form.is_valid():
            activity = form.save(commit=False)
            activity.event = event
            activity.save()
            messages.success(request, f"Activity '{activity.name}' added.")
            return redirect("events:pure_step2_activities", event_id=event.id)

        activities = event.activities.all()
        return render(request, "pure_ems/step2_activities.html", {
            "event": event,
            "activities": activities,
            "form": form
        })
