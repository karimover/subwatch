from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from subscriptions.models import Payment, PriceChange, Subscription

from .forms import SignupForm, UserPreferenceForm
from .models import UserPreference
from .services import build_dashboard_summary


def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/landing.html")


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserPreference.objects.create(user=user, default_currency=settings.BASE_CURRENCY)
        login(request, user)
        messages.success(request, "Аккаунт создан. Добавьте первую подписку.")
        return redirect("subscription_create")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    today = timezone.localdate()
    active_subscriptions = (
        Subscription.objects.filter(user=request.user, status=Subscription.Status.ACTIVE)
        .select_related("category")
        .order_by("next_payment_date")
    )
    preference, _ = UserPreference.objects.get_or_create(
        user=request.user, defaults={"default_currency": settings.BASE_CURRENCY}
    )
    summary = build_dashboard_summary(active_subscriptions, preference.default_currency)
    upcoming = active_subscriptions.filter(
        next_payment_date__range=(today - timedelta(days=7), today + timedelta(days=30))
    )[:6]
    due_soon_count = active_subscriptions.filter(
        next_payment_date__range=(today, today + timedelta(days=7))
    ).count()
    category_counts = list(
        active_subscriptions.values("category__name", "category__color")
        .annotate(subscription_count=Count("id"))
        .order_by("-subscription_count", "category__name")
    )
    latest_payments = (
        Payment.objects.filter(subscription__user=request.user)
        .select_related("subscription", "subscription__category")[:5]
    )
    recent_price_changes = (
        PriceChange.objects.filter(subscription__user=request.user)
        .select_related("subscription")[:4]
    )
    context = {
        "active_count": active_subscriptions.count(),
        "paused_count": Subscription.objects.filter(user=request.user, status=Subscription.Status.PAUSED).count(),
        "summary": summary,
        "upcoming": upcoming,
        "due_soon_count": due_soon_count,
        "category_counts": category_counts,
        "latest_payments": latest_payments,
        "recent_price_changes": recent_price_changes,
        "today": today,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def preferences(request):
    preference, _ = UserPreference.objects.get_or_create(
        user=request.user, defaults={"default_currency": settings.BASE_CURRENCY}
    )
    form = UserPreferenceForm(request.POST or None, instance=preference)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Настройки сохранены.")
        return redirect("preferences")
    return render(request, "core/preferences.html", {"form": form})
