"""Domain services for billing dates, currency conversion and payment recording."""
from datetime import date, timedelta
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import ExchangeRate, Payment, Subscription

FRANKFURTER_RATES_URL = "https://api.frankfurter.dev/v2/rates"
REQUEST_TIMEOUT = 5
RATE_CACHE_SECONDS = 60 * 60 * 6


def advance_billing_date(current_date: date, billing_cycle: str) -> date:
    """Return the next billing date without drifting at month ends."""
    if billing_cycle == Subscription.BillingCycle.WEEKLY:
        return current_date + timedelta(days=7)
    month_steps = {
        Subscription.BillingCycle.MONTHLY: 1,
        Subscription.BillingCycle.QUARTERLY: 3,
        Subscription.BillingCycle.YEARLY: 12,
    }
    return current_date + relativedelta(months=month_steps[billing_cycle])


def get_exchange_rates(base_currency: str, quote_currencies: set[str] | list[str]) -> dict[str, Decimal]:
    """Get latest rates using Frankfurter v2, with a database fallback."""
    base = base_currency.upper()
    quotes = sorted({code.upper() for code in quote_currencies if code.upper() != base})
    result = {base: Decimal("1")}
    if not quotes:
        return result

    cache_key = f"frankfurter:{base}:{','.join(quotes)}"
    cached_rates = cache.get(cache_key)
    if cached_rates:
        return {**result, **cached_rates}

    try:
        response = requests.get(
            FRANKFURTER_RATES_URL,
            params={"base": base, "quotes": ",".join(quotes)},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json(parse_float=Decimal)
        rates = {
            row["quote"].upper(): Decimal(str(row["rate"]))
            for row in rows
            if row.get("quote") and row.get("rate") is not None
        }
        for row in rows:
            if row.get("quote") and row.get("rate") is not None and row.get("date"):
                ExchangeRate.objects.update_or_create(
                    base_currency=base,
                    quote_currency=row["quote"].upper(),
                    rate_date=date.fromisoformat(row["date"]),
                    defaults={"rate": Decimal(str(row["rate"]))},
                )
        cache.set(cache_key, rates, RATE_CACHE_SECONDS)
        return {**result, **rates}
    except (requests.RequestException, ValueError, KeyError, TypeError):
        fallback = {}
        for quote in quotes:
            latest = (
                ExchangeRate.objects.filter(base_currency=base, quote_currency=quote)
                .order_by("-rate_date")
                .first()
            )
            if latest:
                fallback[quote] = latest.rate
        return {**result, **fallback}


def get_conversion_rate(from_currency: str, to_currency: str, on_date: date | None = None):
    """Return a direct rate and its observation date, or (None, None)."""
    source = from_currency.upper()
    target = to_currency.upper()
    if source == target:
        return Decimal("1"), on_date or timezone.localdate()

    params = {}
    if on_date:
        params["date"] = on_date.isoformat()
    try:
        response = requests.get(
            f"https://api.frankfurter.dev/v2/rate/{source.lower()}/{target.lower()}",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json(parse_float=Decimal)
        rate = Decimal(str(payload["rate"]))
        rate_date = date.fromisoformat(payload["date"])
        ExchangeRate.objects.update_or_create(
            base_currency=source,
            quote_currency=target,
            rate_date=rate_date,
            defaults={"rate": rate},
        )
        return rate, rate_date
    except (requests.RequestException, ValueError, KeyError, TypeError):
        saved = (
            ExchangeRate.objects.filter(base_currency=source, quote_currency=target)
            .order_by("-rate_date")
            .first()
        )
        if saved:
            return saved.rate, saved.rate_date
        inverse = (
            ExchangeRate.objects.filter(base_currency=target, quote_currency=source)
            .order_by("-rate_date")
            .first()
        )
        if inverse and inverse.rate:
            return Decimal("1") / inverse.rate, inverse.rate_date
        return None, None


def convert_to_base(amount: Decimal, source_currency: str, base_currency: str, base_rates: dict[str, Decimal]):
    """Convert quote-currency amount to base currency using base->quote rates."""
    source = source_currency.upper()
    base = base_currency.upper()
    if source == base:
        return amount.quantize(Decimal("0.01"))
    rate = base_rates.get(source)
    if not rate or rate <= 0:
        return None
    return (amount / rate).quantize(Decimal("0.01"))


@transaction.atomic
def create_payment(subscription: Subscription, payment_form, base_currency: str) -> Payment:
    """Persist a payment, capture its conversion and advance the next due date."""
    payment = payment_form.save(commit=False)
    payment.subscription = subscription
    rate, rate_date = get_conversion_rate(payment.currency, base_currency, payment.paid_at)
    payment.normalized_currency = base_currency
    payment.exchange_rate = rate
    payment.exchange_rate_date = rate_date
    if rate is not None:
        payment.normalized_amount = (payment.amount * rate).quantize(Decimal("0.01"))
    payment.save()

    if payment.status == Payment.Status.PAID and subscription.status == Subscription.Status.ACTIVE:
        next_date = advance_billing_date(subscription.next_payment_date, subscription.billing_cycle)
        today = timezone.localdate()
        while next_date <= today:
            next_date = advance_billing_date(next_date, subscription.billing_cycle)
        subscription.next_payment_date = next_date
        subscription.save(update_fields=("next_payment_date", "updated_at"))
    return payment
