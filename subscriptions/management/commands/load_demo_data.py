from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import UserPreference
from subscriptions.models import ExchangeRate, Payment, PriceChange, Reminder, Subscription, SubscriptionCategory
from subscriptions.services import convert_to_base, get_exchange_rates


DEMO_SUBSCRIPTIONS = [
    ("Netflix", "video", "Netflix", "13.99", "EUR", "monthly", 4),
    ("Spotify Premium", "music", "Spotify", "10.99", "EUR", "monthly", 8),
    ("YouTube Premium", "video", "Google", "11.99", "EUR", "monthly", 12),
    ("iCloud+", "cloud", "Apple", "2.99", "EUR", "monthly", 15),
    ("Figma Professional", "software", "Figma", "15.00", "USD", "monthly", 19),
    ("Adobe Photography", "software", "Adobe", "11.99", "EUR", "monthly", 22),
    ("PlayStation Plus", "gaming", "Sony", "79.99", "EUR", "yearly", 120),
    ("Notion Plus", "software", "Notion Labs", "10.00", "USD", "monthly", 34),
    ("Google One", "cloud", "Google", "2.99", "EUR", "monthly", 39),
    ("Duolingo Super", "education", "Duolingo", "7.99", "EUR", "monthly", 45),
    ("Strava", "fitness", "Strava", "59.99", "EUR", "yearly", 160),
    ("Dropbox Plus", "cloud", "Dropbox", "11.99", "USD", "monthly", 59),
]


class Command(BaseCommand):
    help = "Create 12 realistic demo subscriptions and payment history for an existing user."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Existing account that will own the demo data.")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("Пользователь не найден. Сначала зарегистрируйтесь в SubWatch.") from exc

        preference, _ = UserPreference.objects.get_or_create(
            user=user, defaults={"default_currency": settings.BASE_CURRENCY}
        )
        today = timezone.localdate()
        currencies = {item[4] for item in DEMO_SUBSCRIPTIONS}
        rates = get_exchange_rates(preference.default_currency, currencies)
        created_subscriptions = 0
        created_payments = 0

        for name, category_slug, provider, amount_text, currency, cycle, due_in in DEMO_SUBSCRIPTIONS:
            category = SubscriptionCategory.objects.get(slug=category_slug)
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    "category": category,
                    "provider": provider,
                    "amount": Decimal(amount_text),
                    "currency": currency,
                    "billing_cycle": cycle,
                    "next_payment_date": today + timedelta(days=due_in),
                    "start_date": today - relativedelta(months=8),
                    "website": "",
                },
            )
            if created:
                created_subscriptions += 1
            Reminder.objects.get_or_create(
                subscription=subscription,
                days_before=preference.reminder_days,
            )
            if subscription.payments.exists():
                continue
            base_amount = convert_to_base(subscription.amount, currency, preference.default_currency, rates)
            quote_rate = rates.get(currency)
            rate_date = None
            exchange_rate = None
            if currency == preference.default_currency:
                exchange_rate = Decimal("1")
                rate_date = today
            elif quote_rate:
                exchange_rate = Decimal("1") / quote_rate
                saved_rate = ExchangeRate.objects.filter(
                    base_currency=preference.default_currency,
                    quote_currency=currency,
                ).order_by("-rate_date").first()
                rate_date = saved_rate.rate_date if saved_rate else today

            payment_months = {
                Subscription.BillingCycle.MONTHLY: (3, 2, 1),
                Subscription.BillingCycle.QUARTERLY: (6, 3),
                Subscription.BillingCycle.YEARLY: (8,),
                Subscription.BillingCycle.WEEKLY: (3, 2, 1),
            }[subscription.billing_cycle]
            for months_ago in payment_months:
                paid_at = today - relativedelta(months=months_ago)
                Payment.objects.create(
                    subscription=subscription,
                    amount=subscription.amount,
                    currency=subscription.currency,
                    paid_at=paid_at,
                    status=Payment.Status.PAID,
                    note="Демонстрационная запись",
                    normalized_amount=base_amount,
                    normalized_currency=preference.default_currency if base_amount is not None else "",
                    exchange_rate=exchange_rate,
                    exchange_rate_date=rate_date,
                )
                created_payments += 1

        price_change_count = 0
        for subscription in Subscription.objects.filter(user=user, name__in=("Netflix", "Spotify Premium", "Figma Professional")):
            if not subscription.price_changes.exists():
                increase = (subscription.amount * Decimal("0.10")).quantize(Decimal("0.01"))
                PriceChange.objects.create(
                    subscription=subscription,
                    old_amount=subscription.amount - increase,
                    old_currency=subscription.currency,
                    new_amount=subscription.amount,
                    new_currency=subscription.currency,
                    note="Демонстрационное изменение тарифа",
                )
                price_change_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Готово: добавлено подписок — {created_subscriptions}, платежей — {created_payments}, изменений цен — {price_change_count}."
        ))
        if created_subscriptions == 0:
            self.stdout.write("Демонстрационные подписки уже существуют; дубликаты не создавались.")
