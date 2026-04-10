from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import OrganizerProfile

def role_selection(request):
    """
    Dedicated role selection screen shown after landing.
    Saves the picked role in session so login/signup can prefill it.
    """

    roles = [
        ("organizer","Organizer","Design and publish events, manage activities, invite coordinators.","indigo","#4f46e5","#4338ca","rocket"),
        ("coordinator","Coordinator","Run on-ground ops, scan QR codes, validate payments, update leaderboards.","green","#16a34a","#15803d","badge-check"),
    ]

    if request.method == "POST":
        role = request.POST.get("role")
        next_action = request.POST.get("next_action", "login")

        if role not in {"organizer", "coordinator"}:
            messages.error(request, "Please choose a valid role.")
            return redirect("accounts:role_selection")

        request.session["selected_role"] = role

        target = "events:unified_login"
        if next_action == "signup":
            target = "events:signup"

        return redirect(f"{reverse(target)}?role={role}")

    selected_role = request.session.get("selected_role", "")

    return render(
        request,
        "accounts/role_selection.html",
        {
            "selected_role": selected_role,
            "roles": roles   
        },
    )

def organizer_signup(request):
    """Handle organizer signup"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        organization_name = request.POST.get('organization_name', '')
        phone_number = request.POST.get('phone_number', '')

        # Validation
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'registration/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'registration/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'registration/signup.html')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create organizer profile
        OrganizerProfile.objects.create(
            user=user,
            organization_name=organization_name,
            phone_number=phone_number
        )

        messages.success(request, "Account created successfully! Please log in.")
        return redirect('accounts:organizer_login')

    return render(request, 'registration/signup.html')


def organizer_login(request):
    """Handle organizer login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is None:
            # fallback: allow login using email address
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            candidate = UserModel.objects.filter(email__iexact=(username or '').strip()).first()
            if candidate:
                user = authenticate(request, username=candidate.username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('events:organizer_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'registration/organizer_login.html')


def participant_signup(request):
    """Participant signup is hidden — redirect to role selection."""
    messages.info(request, "Participant signup is not available here.")
    return redirect('accounts:role_selection')


def    participant_login(request):
    """Participant login is hidden — redirect to role selection."""
    messages.info(request, "Participant access is disabled. Choose Organizer or Coordinator.")
    return redirect('accounts:role_selection')


def unified_login(request):
    """Unified login page - choose role first"""
    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'organizer':
            return redirect('accounts:organizer_login')
        elif role == 'coordinator':
            return redirect('accounts:coordinator_login')
        else:
            messages.error(request, "Please select a valid role.")
    # Allow preselecting role via GET (e.g., ?role=organizer) or session
    selected_role = request.GET.get('role') or request.session.get('selected_role', '')
    return render(request, 'registration/unified_login.html', {"selected_role": selected_role})


@login_required(login_url='accounts:organizer_login')
def logout_view(request):
    """Handle logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('website-index')

