from django.urls import path
from . import views_activity_registration

urlpatterns = [
    path('activity/<int:activity_id>/register/', views_activity_registration.register_for_activity, name='register_for_activity'),
]
