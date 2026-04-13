from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Activity
from .models_activity_registration import ActivityRegistration
from participant.models import Participant

@login_required
def register_for_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    participant = get_object_or_404(Participant, user=request.user)
    already_registered = ActivityRegistration.objects.filter(participant=participant, activity=activity).exists()
    if request.method == 'POST' and not already_registered:
        ActivityRegistration.objects.create(participant=participant, activity=activity)
        return render(request, 'registration/activity_success.html', {'activity': activity})
    return render(request, 'registration/register_activity.html', {
        'activity': activity,
        'already_registered': already_registered
    })