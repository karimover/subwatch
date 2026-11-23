from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import UserPreference

from .forms import (
    ConfirmationForm,
    PaymentForm,
    ReminderForm,
    SubscriptionFilterForm,
    SubscriptionForm,
)
from .models import PriceChange, Reminder, Subscription
from .services import create_payment


@login_required
def subscription_list(request):
    subscriptions = Subscription.objects.filter(user=request.user).select_related("category")
    filter_form = SubscriptionFilterForm(request.GET or None)

    if filter_form.is_valid():
        query = filter_form.cleaned_data["q"]
        status = filter_form.cleaned_data["status"]
        category = filter_form.cleaned_data["category"]
        if query:
            subscriptions = subscriptions.filter(Q(name__icontains=query) | Q(provider__icontains=query))
        if status:
            subscriptions = subscriptions.filter(status=status)
        if category:
            subscriptions = subscriptions.filter(category=category)

    return render(
        request,
        "subscriptions/list.html",
        {
            "subscriptions": subscriptions,
            "filter_form": filter_form,
        },
    )


@login_required
def subscription_create(request):
    form = SubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = request.user
        subscription.save()
        Reminder.objects.get_or_create(
            subscription=subscription,
            days_before=UserPreference.objects.get_or_create(
                user=request.user, defaults={"default_currency": settings.BASE_CURRENCY}
            )[0].reminder_days,
        )
        messages.success(request, "Подписка добавлена.")
        return redirect("subscription_detail", pk=subscription.pk)
    return render(request, "subscriptions/form.html", {"form": form, "page_title": "Новая подписка"})


@login_required
def subscription_detail(request, pk):
    subscription = get_object_or_404(
        Subscription.objects.select_related("category"), pk=pk, user=request.user
    )
    payments = subscription.payments.all()[:12]
    price_changes = subscription.price_changes.all()[:8]
    reminders = subscription.reminders.all()
    configured_reminders = set(reminders.values_list("days_before", flat=True))
    default_reminder_days = next(
        (days for days in (3, 7, 1, 0) if days not in configured_reminders), 3
    )
    return render(
        request,
        "subscriptions/detail.html",
        {
            "subscription": subscription,
            "payments": payments,
            "price_changes": price_changes,
            "reminders": reminders,
            "payment_form": PaymentForm(
                initial={
                    "amount": subscription.amount,
                    "currency": subscription.currency,
                    "paid_at": timezone.localdate(),
                }
            ),
            "reminder_form": ReminderForm(
                initial={"days_before": default_reminder_days, "is_enabled": True}
            ),
        },
    )


@login_required
def subscription_edit(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    old_amount = subscription.amount
    old_currency = subscription.currency
    form = SubscriptionForm(request.POST or None, instance=subscription)
    if request.method == "POST" and form.is_valid():
        updated = form.save()
        if old_amount != updated.amount or old_currency != updated.currency:
            PriceChange.objects.create(
                subscription=updated,
                old_amount=old_amount,
                old_currency=old_currency,
                new_amount=updated.amount,
                new_currency=updated.currency,
            )
        messages.success(request, "Изменения сохранены.")
        return redirect("subscription_detail", pk=updated.pk)
    return render(
        request,
        "subscriptions/form.html",
        {"form": form, "page_title": "Редактировать подписку", "subscription": subscription},
    )


@login_required
def subscription_delete(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    form = ConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = subscription.name
        subscription.delete()
        messages.success(request, f"Подписка «{name}» удалена.")
        return redirect("subscription_list")
    return render(request, "subscriptions/delete.html", {"subscription": subscription, "form": form})


@login_required
def payment_create(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    form = PaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        preference, _ = UserPreference.objects.get_or_create(
            user=request.user, defaults={"default_currency": settings.BASE_CURRENCY}
        )
        payment = create_payment(subscription, form, preference.default_currency)
        if payment.normalized_amount is None:
            messages.warning(
                request,
                "Платёж сохранён, но курс валюты недоступен. Сумма не включена в пересчитанную аналитику.",
            )
        else:
            messages.success(request, "Платёж записан, следующая дата списания обновлена.")
        return redirect("subscription_detail", pk=subscription.pk)
    return render(
        request,
        "subscriptions/payment_form.html",
        {"form": form, "subscription": subscription},
    )


@login_required
def reminder_create(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    form = ReminderForm(request.POST or None)
    form.instance.subscription = subscription
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Напоминание сохранено.")
    else:
        messages.error(request, "Не удалось сохранить напоминание. Проверьте срок и отсутствие дубликата.")
    return redirect("subscription_detail", pk=subscription.pk)


@login_required
def reminder_delete(request, pk, reminder_id):
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    reminder = get_object_or_404(Reminder, pk=reminder_id, subscription=subscription)
    form = ConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reminder.delete()
        messages.success(request, "Напоминание удалено.")
    return redirect("subscription_detail", pk=subscription.pk)
