from django.contrib.auth.views import LoginView
from django.urls import path
from . import views

urlpatterns = [
    path('', views.role_based_user_page, name='home'),
    path('events/', views.event_list, name='event_create_or_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('role-based-user/', views.role_based_user_page, name='role_based_user'),
    path(
        'login/coordinator/',
        LoginView.as_view(template_name='registration/coordinator_login.html'),
        name='coordinator_login',
    ),
    path(
        'login/organizer/',
        LoginView.as_view(template_name='registration/organizer_login.html'),
        name='organizer_login',
    ),
    path(
        'login/participant/',
        LoginView.as_view(template_name='registration/participant_login.html'),
        name='participant_login',
    ),
    path('signup/', views.signup, name='signup'),
]