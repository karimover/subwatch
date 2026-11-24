from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import UserPreference
from subscriptions.models import Subscription, SubscriptionCategory


class AccountWorkflowTests(TestCase):
    def test_signup_creates_preferences_and_authenticates_user(self):
        password = "A-Very-Strong-Password-2026!!"
        response = self.client.post(
            reverse("signup"),
            {
                "username": "new-subwatch-user",
                "email": "new@example.com",
                "password1": password,
                "password2": password,
            },
        )

        self.assertRedirects(response, reverse("subscription_create"))
        user = User.objects.get(username="new-subwatch-user")
        preference = UserPreference.objects.get(user=user)
        self.assertEqual(preference.default_currency, "EUR")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_rejects_an_email_already_in_use(self):
        User.objects.create_user(
            username="existing-user",
            email="taken@example.com",
            password="A-Very-Strong-Password-2026!!",
        )
        password = "Another-Strong-Password-2026!!"

        response = self.client.post(
            reverse("signup"),
            {
                "username": "second-user",
                "email": "TAKEN@example.com",
                "password1": password,
                "password2": password,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="second-user").exists())

    def test_preferences_update_currency_and_reminder_period(self):
        user = User.objects.create_user(username="settings-user", password="safe-test-password")
        self.client.force_login(user)
        preference = UserPreference.objects.create(user=user, default_currency="EUR")

        response = self.client.post(
            reverse("preferences"),
            {"default_currency": "PLN", "reminder_days": "7"},
        )

        self.assertRedirects(response, reverse("preferences"))
        preference.refresh_from_db()
        self.assertEqual(preference.default_currency, "PLN")
        self.assertEqual(preference.reminder_days, 7)

    def test_dashboard_counts_only_the_current_users_subscriptions(self):
        user = User.objects.create_user(username="dashboard-owner", password="safe-test-password")
        another_user = User.objects.create_user(username="other-owner", password="safe-test-password")
        category = SubscriptionCategory.objects.get(slug="video")
        today = timezone.localdate()

        Subscription.objects.create(
            user=user,
            category=category,
            name="My active service",
            amount=Decimal("9.99"),
            currency="EUR",
            next_payment_date=today,
        )
        Subscription.objects.create(
            user=user,
            category=category,
            name="My paused service",
            amount=Decimal("4.99"),
            currency="EUR",
            next_payment_date=today,
            status=Subscription.Status.PAUSED,
        )
        Subscription.objects.create(
            user=another_user,
            category=category,
            name="Private service",
            amount=Decimal("99.99"),
            currency="EUR",
            next_payment_date=today,
        )
        self.client.force_login(user)

        with patch("core.services.get_exchange_rates", return_value={"EUR": Decimal("1")}):
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["paused_count"], 1)
        self.assertNotContains(response, "Private service")

    def test_authenticated_user_is_redirected_from_landing_page(self):
        user = User.objects.create_user(username="landing-user", password="safe-test-password")
        self.client.force_login(user)

        response = self.client.get(reverse("landing"))

        self.assertRedirects(response, reverse("dashboard"))
