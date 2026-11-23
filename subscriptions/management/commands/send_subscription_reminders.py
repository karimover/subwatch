from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Reminder, Subscription


class Command(BaseCommand):
    help = "Send email reminders for upcoming subscription payments. Schedule once per day."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show due reminders without sending email.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        reminders = Reminder.objects.filter(
            is_enabled=True,
            subscription__status=Subscription.Status.ACTIVE,
        ).select_related("subscription", "subscription__user")
        sent = 0
        skipped = 0

        for reminder in reminders:
            subscription = reminder.subscription
            days_left = (subscription.next_payment_date - today).days
            if days_left != reminder.days_before:
                continue
            if reminder.last_sent_at and timezone.localtime(reminder.last_sent_at).date() == today:
                continue
            if not subscription.user.email:
                skipped += 1
                continue

            subject = f"Списание по подписке {subscription.name}"
            message = (
                f"Привет, {subscription.user.get_username()}!\n\n"
                f"Через {days_left} дн. запланировано списание за {subscription.name}.\n"
                f"Сумма: {subscription.amount} {subscription.currency}.\n"
                f"Дата: {subscription.next_payment_date:%d.%m.%Y}.\n\n"
                "Проверьте подписку в SubWatch."
            )
            if options["dry_run"]:
                self.stdout.write(f"DRY RUN: {subscription.user.email} — {subject}")
                continue

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [subscription.user.email], fail_silently=False)
            reminder.last_sent_at = timezone.now()
            reminder.save(update_fields=("last_sent_at",))
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Отправлено: {sent}. Пропущено без email: {skipped}."))
