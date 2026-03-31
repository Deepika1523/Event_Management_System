"""
Event management views for organizers
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from datetime import datetime
from .models import Event, Activity, ActivityRegistrationFormField
from accounts.models import OrganizerProfile


@login_required(login_url='accounts:organizer_login')
def organizer_dashboard(request):
    """Main organizer dashboard"""
    try:
        organizer_profile = OrganizerProfile.objects.get(user=request.user)
    except OrganizerProfile.DoesNotExist:
        organizer_profile = OrganizerProfile.objects.create(user=request.user)

    # Get organizer's events
    events = Event.objects.filter(user=request.user).order_by('-date_of_event')
    total_events = events.count()
    
    # Calculate stats
    total_activities = Activity.objects.filter(event__in=events).count()

    context = {
        'organizer_profile': organizer_profile,
        'events': events,
        'total_events': total_events,
        'total_activities': total_activities,
    }
    return render(request, 'organizer_dashboard.html', context)


@login_required(login_url='accounts:organizer_login')
def create_event(request):
    """Create a new event"""
    if request.method == 'POST':
        event_name = request.POST.get('event_name')
        description = request.POST.get('description')
        date_of_event = request.POST.get('date_of_event')
        time_of_event = request.POST.get('time_of_event')
        venue = request.POST.get('venue')
        location = request.POST.get('location')
        category = request.POST.get('category', 'other')
        tagline = request.POST.get('tagline')
        contact_info = request.POST.get('contact_info')
        last_registration_date = request.POST.get('last_registration_date')
        template_choice = request.POST.get('template_choice', 'classic')

        # Validate required fields
        if not event_name or not date_of_event:
            messages.error(request, "Event name and date are required.")
            return render(request, 'events/create_event.html')

        try:
            event = Event.objects.create(
                user=request.user,
                event=event_name,
                activity='',  # Will be populated from activities
                description=description,
                date_of_event=date_of_event,
                time_of_event=time_of_event or None,
                venue=venue,
                location=location,
                category=category,
                tagline=tagline,
                contact_info=contact_info,
                last_registration_date=last_registration_date or None,
                template_choice=template_choice,
                registration='Open',
                announcement='Welcome to the event!'
            )

            # Handle banner image if provided
            if 'banner_image' in request.FILES:
                file = request.FILES['banner_image']
                # Save the file path
                file_path = f"events/{event.id}/{file.name}"
                # For now, just store the filename

            messages.success(request, f"Event '{event_name}' created successfully!")
            return redirect('events:manage_events')
        except Exception as e:
            messages.error(request, f"Error creating event: {str(e)}")
            return render(request, 'events/create_event.html')

    return render(request, 'events/create_event.html')


@login_required(login_url='accounts:organizer_login')
def manage_events(request):
    """View and manage all organizer's events"""
    events = Event.objects.filter(user=request.user).order_by('-date_of_event')
    context = {
        'events': events,
    }
    return render(request, 'events/manage_events.html', context)


@login_required(login_url='accounts:organizer_login')
def edit_event(request, event_id):
    """Edit an existing event"""
    event = get_object_or_404(Event, id=event_id, user=request.user)

    if request.method == 'POST':
        event.event = request.POST.get('event_name', event.event)
        event.description = request.POST.get('description', event.description)
        event.date_of_event = request.POST.get('date_of_event', event.date_of_event)
        event.time_of_event = request.POST.get('time_of_event') or event.time_of_event
        event.venue = request.POST.get('venue', event.venue)
        event.location = request.POST.get('location', event.location)
        event.category = request.POST.get('category', event.category)
        event.tagline = request.POST.get('tagline', event.tagline)
        event.contact_info = request.POST.get('contact_info', event.contact_info)
        event.last_registration_date = request.POST.get('last_registration_date') or event.last_registration_date
        event.template_choice = request.POST.get('template_choice', event.template_choice)
        event.save()

        messages.success(request, "Event updated successfully!")
        return redirect('events:manage_events')

    context = {'event': event}
    return render(request, 'events/edit_event.html', context)


@login_required(login_url='accounts:organizer_login')
def delete_event(request, event_id):
    """Delete an event"""
    event = get_object_or_404(Event, id=event_id, user=request.user)

    if request.method == 'POST':
        event_name = event.event
        event.delete()
        messages.success(request, f"Event '{event_name}' deleted successfully!")
        return redirect('events:manage_events')

    context = {'event': event}
    return render(request, 'events/confirm_delete.html', context)


@login_required(login_url='accounts:organizer_login')
def create_activity(request):
    """Create a new activity for an event"""
    if request.method == 'GET':
        events = Event.objects.filter(user=request.user)
        context = {'events': events}
        return render(request, 'events/create_activity.html', context)

    # POST request
    event_id = request.POST.get('event_id')
    activity_name = request.POST.get('activity_name')
    description = request.POST.get('description')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    max_participants = request.POST.get('max_participants')
    registration_fee = request.POST.get('registration_fee', 'Free')
    is_team_event = request.POST.get('is_team_event') == 'on'
    team_size = request.POST.get('team_size')

    # Validate
    if not event_id or not activity_name:
        messages.error(request, "Event and activity name are required.")
        events = Event.objects.filter(user=request.user)
        return render(request, 'events/create_activity.html', {'events': events})

    event = get_object_or_404(Event, id=event_id, user=request.user)

    try:
        activity = Activity.objects.create(
            event=event,
            name=activity_name,
            description=description,
            start_time=start_time or None,
            end_time=end_time or None,
            max_participants=int(max_participants) if max_participants else None,
            registration_fee=registration_fee,
            is_team_event=is_team_event,
            team_size=int(team_size) if team_size else None,
        )

        messages.success(request, f"Activity '{activity_name}' created successfully!")
        return redirect('events:manage_activities')
    except Exception as e:
        messages.error(request, f"Error creating activity: {str(e)}")
        events = Event.objects.filter(user=request.user)
        return render(request, 'events/create_activity.html', {'events': events})


@login_required(login_url='accounts:organizer_login')
def manage_activities(request):
    """View and manage activities for organizer's events"""
    event_id = request.GET.get('event_id')

    if event_id:
        event = get_object_or_404(Event, id=event_id, user=request.user)
        activities = Activity.objects.filter(event=event)
    else:
        # Show all activities for all events
        events = Event.objects.filter(user=request.user)
        activities = Activity.objects.filter(event__in=events)

    context = {
        'activities': activities,
        'event_id': event_id,
    }
    return render(request, 'events/manage_activities.html', context)


@login_required(login_url='accounts:organizer_login')
def event_dashboard(request, event_id):
    """Dashboard for a specific event - shows activities and registrations"""
    event = get_object_or_404(Event, id=event_id, user=request.user)
    activities = Activity.objects.filter(event=event)

    context = {
        'event': event,
        'activities': activities,
    }
    return render(request, 'events/event_dashboard.html', context)


@login_required(login_url='accounts:participant_login')
def participant_dashboard(request):
    """Participant dashboard"""
    # Get all available events
    events = Event.objects.all().order_by('-date_of_event')

    # Get participant's registrations
    from participant.models import EventRegistration, ActivityRegistration
    event_registrations = EventRegistration.objects.filter(participant=request.user)
    activity_registrations = ActivityRegistration.objects.filter(participant=request.user)

    context = {
        'events': events,
        'event_registrations': event_registrations,
        'activity_registrations': activity_registrations,
    }
    return render(request, 'participant_dashboard.html', context)
