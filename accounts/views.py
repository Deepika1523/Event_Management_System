from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import OrganizerProfile


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
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('events:organizer_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'registration/organizer_login.html')


def participant_signup(request):
    """Handle participant signup"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

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

        messages.success(request, "Account created successfully! Please log in.")
        return redirect('accounts:participant_login')

    return render(request, 'registration/signup.html')


def participant_login(request):
    """Handle participant login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('events:participant_dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'registration/participant_login.html')


def unified_login(request):
    """Unified login page - choose role first"""
    if request.method == 'POST':
        role = request.POST.get('role')
        if role == 'organizer':
            return redirect('accounts:organizer_login')
        elif role == 'participant':
            return redirect('accounts:participant_login')
        else:
            messages.error(request, "Please select a valid role.")

    return render(request, 'registration/unified_login.html')


@login_required(login_url='accounts:organizer_login')
def logout_view(request):
    """Handle logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('website-index')

