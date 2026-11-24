from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from subscriptions.models import Payment, PriceChange, Reminder, Subscription, SubscriptionCategory

User = get_user_model()


class SubscriptionApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="api-owner", password="safe-test-password")
        self.other = User.objects.create_user(username="api-other", password="safe-test-password")
        self.category = SubscriptionCategory.objects.get(slug="music")
        self.own_subscription = Subscription.objects.create(
            user=self.owner,
            category=self.category,
            name="Own service",
            amount=Decimal("9.99"),
            currency="EUR",
            next_payment_date=date(2026, 12, 1),
        )
        self.other_subscription = Subscription.objects.create(
            user=self.other,
            category=self.category,
            name="Private service",
            amount=Decimal("19.99"),
            currency="EUR",
            next_payment_date=date(2026, 12, 2),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_subscription_list_only_returns_current_users_data(self):
        response = self.client.get("/api/v1/subscriptions/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["name"], "Own service")

    def test_create_subscription_assigns_authenticated_owner(self):
        response = self.client.post(
            "/api/v1/subscriptions/",
            {
                "category": self.category.pk,
                "name": "Created through API",
                "provider": "Example",
                "amount": "4.99",
                "currency": "EUR",
                "billing_cycle": "monthly",
                "next_payment_date": "2026-12-10",
                "start_date": "2026-11-24",
                "status": "active",
                "auto_renew": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        created = Subscription.objects.get(name="Created through API")
        self.assertEqual(created.user, self.owner)
        self.assertTrue(Reminder.objects.filter(subscription=created, days_before=3).exists())

    def test_user_cannot_update_another_users_subscription(self):
        response = self.client.patch(
            f"/api/v1/subscriptions/{self.other_subscription.pk}/",
            {"name": "Stolen"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_rejects_trial_end_before_start(self):
        response = self.client.post(
            "/api/v1/subscriptions/",
            {
                "category": self.category.pk,
                "name": "Invalid trial",
                "amount": "4.99",
                "currency": "EUR",
                "billing_cycle": "monthly",
                "next_payment_date": "2026-12-10",
                "start_date": "2026-11-24",
                "trial_end_date": "2026-11-23",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Subscription.objects.filter(name="Invalid trial").exists())

    def test_price_update_creates_audit_record(self):
        response = self.client.patch(
            f"/api/v1/subscriptions/{self.own_subscription.pk}/",
            {"amount": "12.99"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        change = PriceChange.objects.get(subscription=self.own_subscription)
        self.assertEqual(change.old_amount, Decimal("9.99"))
        self.assertEqual(change.new_amount, Decimal("12.99"))

    def test_api_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/subscriptions/")
        self.assertIn(response.status_code, (401, 403))

    def test_payment_history_is_limited_to_current_users_subscriptions(self):
        Payment.objects.create(
            subscription=self.own_subscription,
            amount=Decimal("9.99"),
            currency="EUR",
            paid_at=date(2026, 11, 1),
        )
        Payment.objects.create(
            subscription=self.other_subscription,
            amount=Decimal("19.99"),
            currency="EUR",
            paid_at=date(2026, 11, 1),
        )
        response = self.client.get("/api/v1/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
