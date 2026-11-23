from django.contrib import admin

from .models import ExchangeRate, Payment, PriceChange, Reminder, Subscription, SubscriptionCategory


@admin.register(SubscriptionCategory)
class SubscriptionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "sort_order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("created_at",)


class ReminderInline(admin.TabularInline):
    model = Reminder
    extra = 0


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "category", "amount", "currency", "billing_cycle", "next_payment_date", "status")
    list_filter = ("status", "billing_cycle", "currency", "category")
    search_fields = ("name", "provider", "user__username", "user__email")
    date_hierarchy = "next_payment_date"
    inlines = (PaymentInline, ReminderInline)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("subscription", "amount", "currency", "paid_at", "status", "normalized_amount", "normalized_currency")
    list_filter = ("status", "currency", "normalized_currency")
    search_fields = ("subscription__name", "subscription__user__username", "note")
    date_hierarchy = "paid_at"


@admin.register(PriceChange)
class PriceChangeAdmin(admin.ModelAdmin):
    list_display = ("subscription", "old_amount", "old_currency", "new_amount", "new_currency", "changed_at")
    search_fields = ("subscription__name", "subscription__user__username")
    date_hierarchy = "changed_at"


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("subscription", "days_before", "is_enabled", "last_sent_at")
    list_filter = ("is_enabled", "days_before")
    search_fields = ("subscription__name", "subscription__user__username")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "quote_currency", "rate", "rate_date", "updated_at")
    list_filter = ("base_currency", "quote_currency", "rate_date")
    search_fields = ("base_currency", "quote_currency")
