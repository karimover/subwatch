from rest_framework import serializers

from subscriptions.models import Payment, Subscription, SubscriptionCategory


class SubscriptionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    monthly_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    annual_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    days_until_payment = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "provider",
            "amount",
            "currency",
            "billing_cycle",
            "next_payment_date",
            "start_date",
            "trial_end_date",
            "website",
            "status",
            "auto_renew",
            "notes",
            "monthly_amount",
            "annual_amount",
            "days_until_payment",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_name",
            "monthly_amount",
            "annual_amount",
            "days_until_payment",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        trial_end_date = attrs.get("trial_end_date", getattr(self.instance, "trial_end_date", None))
        if start_date and trial_end_date and trial_end_date < start_date:
            raise serializers.ValidationError({
                "trial_end_date": "Пробный период не может закончиться раньше начала подписки."
            })
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    subscription_name = serializers.CharField(source="subscription.name", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "subscription",
            "subscription_name",
            "amount",
            "currency",
            "paid_at",
            "status",
            "note",
            "normalized_amount",
            "normalized_currency",
            "exchange_rate",
            "exchange_rate_date",
            "created_at",
        )
        read_only_fields = fields


class SubscriptionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionCategory
        fields = ("id", "name", "slug", "icon", "color")
        read_only_fields = fields
