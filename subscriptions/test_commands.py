from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from subscriptions.models import (
    Payment,
    PriceChange,
    Reminder,
    Subscription,
    SubscriptionCategory,
)


class DemoDataCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="demo-account",
            email="demo@example.com",
            password="safe-test-password",
        )

    def run_demo_command(self):
        with patch(
            "subscriptions.management.commands.load_demo_data.get_exchange_rates",
            return_value={"EUR": Decimal("1"), "USD": Decimal("1.08")},
        ):
            call_command("load_demo_data", username=self.user.username, stdout=StringIO())

    def test_demo_command_creates_twelve_subscriptions_and_history(self):
        self.run_demo_command()

        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 12)
        self.assertEqual(Reminder.objects.filter(subscription__user=self.user).count(), 12)
        self.assertGreater(Payment.objects.filter(subscription__user=self.user).count(), 12)
        self.assertEqual(PriceChange.objects.filter(subscription__user=self.user).count(), 3)

    def test_demo_command_is_idempotent(self):
        self.run_demo_command()
        initial_counts = (
            Subscription.objects.filter(user=self.user).count(),
            Payment.objects.filter(subscription__user=self.user).count(),
            Reminder.objects.filter(subscription__user=self.user).count(),
            PriceChange.objects.filter(subscription__user=self.user).count(),
        )

        self.run_demo_command()

        repeated_counts = (
            Subscription.objects.filter(user=self.user).count(),
            Payment.objects.filter(subscription__user=self.user).count(),
            Reminder.objects.filter(subscription__user=self.user).count(),
            PriceChange.objects.filter(subscription__user=self.user).count(),
        )
        self.assertEqual(repeated_counts, initial_counts)

    def test_demo_command_requires_an_existing_user(self):
        with self.assertRaises(CommandError):
            call_command("load_demo_data", username="missing-user", stdout=StringIO())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SubscriptionReminderCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reminder-account",
            email="reminder@example.com",
            password="safe-test-password",
        )
        category = SubscriptionCategory.objects.get(slug="video")
        self.subscription = Subscription.objects.create(
            user=self.user,
            category=category,
            name="Video subscription",
            amount=Decimal("12.99"),
            currency="EUR",
            next_payment_date=timezone.localdate() + timedelta(days=3),
        )
        self.reminder = Reminder.objects.create(subscription=self.subscription, days_before=3)

    def test_reminder_is_sent_once_and_timestamp_is_saved(self):
        call_command("send_subscription_reminders", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Video subscription", mail.outbox[0].subject)
        self.reminder.refresh_from_db()
        self.assertIsNotNone(self.reminder.last_sent_at)

        call_command("send_subscription_reminders", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)

    def test_dry_run_does_not_send_email_or_update_timestamp(self):
        output = StringIO()

        call_command("send_subscription_reminders", dry_run=True, stdout=output)

        self.assertIn("DRY RUN", output.getvalue())
        self.assertEqual(len(mail.outbox), 0)
        self.reminder.refresh_from_db()
        self.assertIsNone(self.reminder.last_sent_at)

    def test_disabled_reminder_is_not_sent(self):
        self.reminder.is_enabled = False
        self.reminder.save(update_fields=("is_enabled",))

        call_command("send_subscription_reminders", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 0)
