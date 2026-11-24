from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from subscriptions.forms import PaymentForm, ReminderForm, SubscriptionFilterForm, SubscriptionForm
from subscriptions.models import Reminder, Subscription, SubscriptionCategory
from subscriptions.services import (
    advance_billing_date,
    convert_to_base,
    create_payment,
    get_exchange_rates,
)


class BillingCalculationTests(TestCase):
    def test_monthly_equivalent_for_each_billing_cycle(self):
        cases = [
            (Subscription.BillingCycle.WEEKLY, Decimal("10.00"), Decimal("43.33")),
            (Subscription.BillingCycle.MONTHLY, Decimal("12.00"), Decimal("12.00")),
            (Subscription.BillingCycle.QUARTERLY, Decimal("30.00"), Decimal("10.00")),
            (Subscription.BillingCycle.YEARLY, Decimal("120.00"), Decimal("10.00")),
        ]
        for cycle, amount, expected in cases:
            with self.subTest(cycle=cycle):
                subscription = Subscription(amount=amount, billing_cycle=cycle)
                self.assertEqual(subscription.monthly_amount, expected)
                annual_expected = {
                    Subscription.BillingCycle.WEEKLY: Decimal("520.00"),
                    Subscription.BillingCycle.MONTHLY: Decimal("144.00"),
                    Subscription.BillingCycle.QUARTERLY: Decimal("120.00"),
                    Subscription.BillingCycle.YEARLY: Decimal("120.00"),
                }[cycle]
                self.assertEqual(subscription.annual_amount, annual_expected)

    def test_monthly_billing_date_keeps_month_end(self):
        self.assertEqual(advance_billing_date(date(2026, 1, 31), "monthly"), date(2026, 2, 28))
        self.assertEqual(advance_billing_date(date(2024, 1, 31), "monthly"), date(2024, 2, 29))

    def test_weekly_billing_date_adds_seven_days(self):
        self.assertEqual(advance_billing_date(date(2026, 11, 24), "weekly"), date(2026, 12, 1))

    def test_currency_conversion_uses_inverse_base_rate(self):
        converted = convert_to_base(Decimal("11.00"), "USD", "EUR", {"EUR": Decimal("1"), "USD": Decimal("1.10")})
        self.assertEqual(converted, Decimal("10.00"))

    @patch("subscriptions.services.requests.get")
    def test_exchange_rates_are_loaded_and_saved(self, mocked_get):
        response = Mock()
        response.json.return_value = [
            {"base": "EUR", "quote": "USD", "rate": 1.1, "date": "2026-11-23"},
        ]
        response.raise_for_status.return_value = None
        mocked_get.return_value = response

        rates = get_exchange_rates("EUR", {"USD"})

        self.assertEqual(rates["USD"], Decimal("1.1"))
        self.assertEqual(mocked_get.call_args.kwargs["params"], {"base": "EUR", "quotes": "USD"})


class PaymentRecordingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="payer", password="safe-test-password")
        self.category = SubscriptionCategory.objects.create(name="Облако", slug="payment-cloud")
        self.subscription = Subscription.objects.create(
            user=self.user,
            category=self.category,
            name="Cloud storage",
            amount=Decimal("4.99"),
            currency="EUR",
            billing_cycle=Subscription.BillingCycle.MONTHLY,
            next_payment_date=timezone.localdate(),
        )

    @patch("subscriptions.services.get_conversion_rate")
    def test_paid_payment_advances_next_billing_date(self, mocked_rate):
        mocked_rate.return_value = (Decimal("1"), date(2026, 11, 24))
        form = PaymentForm({
            "amount": "4.99",
            "currency": "EUR",
            "paid_at": timezone.localdate().isoformat(),
            "status": "paid",
            "note": "",
        })
        self.assertTrue(form.is_valid(), form.errors)

        payment = create_payment(self.subscription, form, "EUR")

        self.subscription.refresh_from_db()
        self.assertEqual(payment.normalized_amount, Decimal("4.99"))
        self.assertEqual(
            self.subscription.next_payment_date,
            advance_billing_date(timezone.localdate(), Subscription.BillingCycle.MONTHLY),
        )

    @patch("subscriptions.services.get_conversion_rate")
    def test_failed_payment_does_not_advance_next_billing_date(self, mocked_rate):
        mocked_rate.return_value = (Decimal("1"), date(2026, 11, 24))
        form = PaymentForm({
            "amount": "4.99",
            "currency": "EUR",
            "paid_at": timezone.localdate().isoformat(),
            "status": "failed",
            "note": "Declined",
        })
        self.assertTrue(form.is_valid(), form.errors)

        create_payment(self.subscription, form, "EUR")

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.next_payment_date, timezone.localdate())


class SubscriptionFormTests(TestCase):
    def setUp(self):
        self.category = SubscriptionCategory.objects.get(slug="video")

    def valid_form_data(self):
        return {
            "name": "Video service",
            "provider": "Provider",
            "category": self.category.pk,
            "amount": "9.99",
            "currency": "EUR",
            "billing_cycle": "monthly",
            "next_payment_date": "2026-12-01",
            "start_date": "2026-01-01",
            "trial_end_date": "",
            "website": "https://example.com",
            "status": "active",
            "auto_renew": "on",
            "notes": "",
        }

    def test_form_rejects_zero_amount(self):
        data = self.valid_form_data()
        data["amount"] = "0"
        self.assertFalse(SubscriptionForm(data).is_valid())

    def test_form_rejects_trial_end_before_start(self):
        data = self.valid_form_data()
        data["trial_end_date"] = "2025-12-31"
        self.assertFalse(SubscriptionForm(data).is_valid())

    def test_filter_form_rejects_unknown_status(self):
        form = SubscriptionFilterForm({"status": "unknown"})
        self.assertFalse(form.is_valid())


class ReminderFormTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="reminder-user", password="safe-test-password")
        category = SubscriptionCategory.objects.create(name="Видео", slug="reminder-video")
        self.subscription = Subscription.objects.create(
            user=user,
            category=category,
            name="Video plan",
            amount=Decimal("8.99"),
            currency="EUR",
            next_payment_date=date(2026, 12, 1),
        )
        Reminder.objects.create(subscription=self.subscription, days_before=3)

    def test_form_rejects_duplicate_reminder_schedule(self):
        form = ReminderForm({"days_before": 3, "is_enabled": True})
        form.instance.subscription = self.subscription
        self.assertFalse(form.is_valid())
        self.assertIn("days_before", form.errors)


class SubscriptionOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="safe-test-password")
        self.other = User.objects.create_user(username="other", password="safe-test-password")
        category = SubscriptionCategory.objects.get(slug="music")
        self.subscription = Subscription.objects.create(
            user=self.owner,
            category=category,
            name="My Music",
            amount=Decimal("9.99"),
            currency="EUR",
            billing_cycle=Subscription.BillingCycle.MONTHLY,
            next_payment_date=date(2026, 12, 1),
        )

    def test_user_cannot_open_another_users_subscription(self):
        self.client.login(username="other", password="safe-test-password")
        response = self.client.get(f"/subscriptions/{self.subscription.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_user_can_open_own_subscription(self):
        self.client.login(username="owner", password="safe-test-password")
        response = self.client.get(f"/subscriptions/{self.subscription.pk}/")
        self.assertEqual(response.status_code, 200)
