from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from subscriptions.models import Payment, Subscription, SubscriptionCategory
from .services import build_payment_analytics


class PaymentAnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyst", password="safe-test-password")
        category = SubscriptionCategory.objects.create(name="Музыка", slug="music")
        self.subscription = Subscription.objects.create(
            user=self.user,
            category=category,
            name="Music Plus",
            amount=Decimal("9.99"),
            currency="EUR",
            billing_cycle=Subscription.BillingCycle.MONTHLY,
            next_payment_date=date(2026, 12, 1),
        )

    def test_analytics_groups_payments_and_calculates_totals(self):
        Payment.objects.create(
            subscription=self.subscription,
            amount=Decimal("9.99"),
            currency="EUR",
            paid_at=date(2026, 10, 5),
            normalized_amount=Decimal("9.99"),
            normalized_currency="EUR",
        )
        Payment.objects.create(
            subscription=self.subscription,
            amount=Decimal("9.99"),
            currency="EUR",
            paid_at=date(2026, 11, 5),
            normalized_amount=Decimal("9.99"),
            normalized_currency="EUR",
        )

        result = build_payment_analytics(self.user, "EUR")

        self.assertEqual(result["payment_count"], 2)
        self.assertEqual(result["total_spent"], 19.98)
        self.assertEqual(result["category_labels"], ["Музыка"])
        self.assertEqual(result["category_values"], [19.98])
        self.assertEqual(len(result["monthly_labels"]), 6)

    def test_analytics_ignores_failed_and_unconverted_payments(self):
        Payment.objects.create(
            subscription=self.subscription,
            amount=Decimal("9.99"),
            currency="EUR",
            paid_at=date(2026, 11, 5),
            status=Payment.Status.FAILED,
            normalized_amount=Decimal("9.99"),
            normalized_currency="EUR",
        )
        Payment.objects.create(
            subscription=self.subscription,
            amount=Decimal("9.99"),
            currency="USD",
            paid_at=date(2026, 11, 6),
            normalized_amount=None,
            normalized_currency="EUR",
        )

        result = build_payment_analytics(self.user, "EUR")

        self.assertEqual(result["payment_count"], 0)
        self.assertEqual(result["total_spent"], 0.0)
