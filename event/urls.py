from django.urls import path
from . import views

urlpatterns = [
    path('', views.role_based_user_page, name='home'),
    path('events/', views.event_list, name='event_create_or_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('role-based-user/', views.role_based_user_page, name='role_based_user'),
]