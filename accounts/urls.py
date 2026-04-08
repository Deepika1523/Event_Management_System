from django.urls import path
from .import views

app_name = 'accounts'

urlpatterns = [
    path('choose-role/', views.role_selection, name='role_selection'),
    path('signup/', views.organizer_signup, name='organizer_signup'),
    path('participant-signup/', views.participant_signup, name='participant_signup'),
    path('login/', views.organizer_login, name='organizer_login'),
    path('participant-login/', views.participant_login, name='participant_login'),
    path('login-choose/', views.unified_login, name='unified_login'),
    path('logout/', views.logout_view, name='logout'),
]
