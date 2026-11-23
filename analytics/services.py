"""Prepare payment analytics with Pandas and Django ORM."""
import pandas as pd
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from subscriptions.models import Payment


def build_payment_analytics(user, currency: str, months: int = 6):
    payments = Payment.objects.filter(
        subscription__user=user,
        status=Payment.Status.PAID,
        normalized_currency=currency,
        normalized_amount__isnull=False,
    )
    totals = payments.aggregate(
        payment_count=Count("id"),
        total_spent=Sum("normalized_amount"),
        average_payment=Avg("normalized_amount"),
    )
    rows = list(payments.values(
        "paid_at",
        "normalized_amount",
        "subscription__name",
        "subscription__category__name",
    ))
    if not rows:
        return {
            "currency": currency,
            "payment_count": totals["payment_count"] or 0,
            "total_spent": float(totals["total_spent"] or 0),
            "average_payment": float(totals["average_payment"] or 0),
            "monthly_labels": [],
            "monthly_values": [],
            "category_labels": [],
            "category_values": [],
            "top_services": [],
        }

    frame = pd.DataFrame(rows)
    frame["paid_at"] = pd.to_datetime(frame["paid_at"])
    frame["amount"] = pd.to_numeric(frame["normalized_amount"].astype(str), errors="coerce")
    frame = frame.dropna(subset=["amount"])
    frame["month"] = frame["paid_at"].dt.to_period("M").astype(str)

    today = timezone.localdate()
    month_range = pd.period_range(end=pd.Period(today, freq="M"), periods=months, freq="M")
    monthly = frame.groupby("month")["amount"].sum().reindex(month_range.astype(str), fill_value=0)
    categories = frame.groupby("subscription__category__name")["amount"].sum().sort_values(ascending=False)
    services = (
        frame.groupby("subscription__name")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    return {
        "currency": currency,
        "payment_count": int(totals["payment_count"] or 0),
        "total_spent": round(float(totals["total_spent"] or 0), 2),
        "average_payment": round(float(totals["average_payment"] or 0), 2),
        "monthly_labels": [period.strftime("%b %Y") for period in month_range],
        "monthly_values": [round(float(value), 2) for value in monthly.tolist()],
        "category_labels": [str(value) for value in categories.index.tolist()],
        "category_values": [round(float(value), 2) for value in categories.tolist()],
        "top_services": [
            {"name": str(name), "total": round(float(value), 2)}
            for name, value in services.items()
        ],
    }
