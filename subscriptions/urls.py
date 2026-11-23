from django.urls import path

from . import views

urlpatterns = [
    path("", views.subscription_list, name="subscription_list"),
    path("add/", views.subscription_create, name="subscription_create"),
    path("<int:pk>/", views.subscription_detail, name="subscription_detail"),
    path("<int:pk>/edit/", views.subscription_edit, name="subscription_edit"),
    path("<int:pk>/delete/", views.subscription_delete, name="subscription_delete"),
    path("<int:pk>/payments/add/", views.payment_create, name="payment_create"),
    path("<int:pk>/reminders/add/", views.reminder_create, name="reminder_create"),
    path("<int:pk>/reminders/<int:reminder_id>/delete/", views.reminder_delete, name="reminder_delete"),
]
