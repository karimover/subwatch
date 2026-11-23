from django.conf import settings
from django.db import transaction

from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from core.models import UserPreference
from subscriptions.models import Payment, PriceChange, Reminder, Subscription, SubscriptionCategory

from .serializers import PaymentSerializer, SubscriptionCategorySerializer, SubscriptionSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    """CRUD endpoint limited to subscriptions owned by the current user."""

    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name", "provider", "category__name")
    ordering_fields = ("name", "amount", "next_payment_date", "created_at")
    ordering = ("next_payment_date", "name")

    def get_queryset(self):
        queryset = Subscription.objects.filter(user=self.request.user).select_related("category")
        status = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        if status in Subscription.Status.values:
            queryset = queryset.filter(status=status)
        if category and category.isdigit():
            queryset = queryset.filter(category_id=int(category))
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        subscription = serializer.save(user=self.request.user)
        preference, _ = UserPreference.objects.get_or_create(
            user=self.request.user, defaults={"default_currency": settings.BASE_CURRENCY}
        )
        Reminder.objects.get_or_create(
            subscription=subscription,
            days_before=preference.reminder_days,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        subscription = self.get_object()
        old_amount = subscription.amount
        old_currency = subscription.currency
        updated = serializer.save()
        if old_amount != updated.amount or old_currency != updated.currency:
            PriceChange.objects.create(
                subscription=updated,
                old_amount=old_amount,
                old_currency=old_currency,
                new_amount=updated.amount,
                new_currency=updated.currency,
                note="Изменение через REST API",
            )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only payment history; users only see payments for their own services."""

    serializer_class = PaymentSerializer
    filter_backends = (filters.OrderingFilter,)
    permission_classes = (IsAuthenticated,)
    ordering_fields = ("paid_at", "amount", "created_at")
    ordering = ("-paid_at", "-created_at")

    def get_queryset(self):
        return Payment.objects.filter(subscription__user=self.request.user).select_related("subscription")


class SubscriptionCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionCategorySerializer
    permission_classes = (IsAuthenticated,)
    queryset = SubscriptionCategory.objects.all()
