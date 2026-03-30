from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="payment-index"),
    path("status/", views.payment_status, name="payment_status"),
]
