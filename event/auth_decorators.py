"""Role-based authentication decorators and utilities."""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Profile


def get_user_role(user):
    """Get the role of a user from their Profile."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "superadmin"
    try:
        profile = Profile.objects.get(user=user)
        return profile.role
    except Profile.DoesNotExist:
        return None


def require_role(*allowed_roles):
    """Decorator to enforce role-based access control.
    
    Usage:
        @require_role('organizer')
        def my_view(request):
            ...
            
        @require_role('coordinator', 'organizer')
        def another_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='events:organizer_login')
        def wrapper(request, *args, **kwargs):
            user_role = get_user_role(request.user)
            
            # Superadmin has access to everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            if user_role not in allowed_roles:
                messages.error(
                    request,
                    f"You do not have permission to access this page. Required: {', '.join(allowed_roles)}"
                )
                return redirect('events:user')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_organizer(view_func):
    """Decorator to restrict access to organizers only."""
    @wraps(view_func)
    @login_required(login_url='events:organizer_login')
    def wrapper(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if request.user.is_superuser or user_role == 'organizer':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Only organizers can access this page.")
        return redirect('events:user')
    
    return wrapper


def require_coordinator(view_func):
    """Decorator to restrict access to coordinators only."""
    @wraps(view_func)
    @login_required(login_url='events:coordinator_login')
    def wrapper(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if request.user.is_superuser or user_role == 'coordinator':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Only coordinators can access this page.")
        return redirect('events:user')
    
    return wrapper


def require_participant(view_func):
    """Decorator to restrict access to participants only."""
    @wraps(view_func)
    @login_required(login_url='events:participant_login')
    def wrapper(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if user_role == 'participant':
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Only participants can access this page.")
        return redirect('events:user')
    
    return wrapper


def get_user_dashboard_redirect(user):
    """Get the appropriate dashboard redirect URL based on user role."""
    if user.is_superuser:
        return 'events:organizer_dashboard'
    
    user_role = get_user_role(user)
    
    if user_role == 'organizer':
        return 'events:organizer_dashboard'
    elif user_role == 'coordinator':
        return 'events:coordinator_dashboard'
    elif user_role == 'participant':
        return 'events:participant_dashboard'
    else:
        return 'events:user'
