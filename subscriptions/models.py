from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import CURRENCY_CHOICES


class SubscriptionCategory(models.Model):
    name = models.CharField("Название", max_length=60, unique=True)
    slug = models.SlugField("Код", max_length=60, unique=True)
    icon = models.CharField("Иконка", max_length=24, default="layers")
    color = models.CharField("Цвет", max_length=7, default="#8B7CFF")
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "Категория подписок"
        verbose_name_plural = "Категории подписок"

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class BillingCycle(models.TextChoices):
        WEEKLY = "weekly", "Еженедельно"
        MONTHLY = "monthly", "Ежемесячно"
        QUARTERLY = "quarterly", "Раз в квартал"
        YEARLY = "yearly", "Ежегодно"

    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        PAUSED = "paused", "Приостановлена"
        CANCELLED = "cancelled", "Отменена"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    category = models.ForeignKey(
        SubscriptionCategory,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        verbose_name="Категория",
    )
    name = models.CharField("Название подписки", max_length=100)
    provider = models.CharField("Провайдер", max_length=100, blank=True)
    amount = models.DecimalField("Стоимость", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency = models.CharField("Валюта", max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    billing_cycle = models.CharField("Период оплаты", max_length=12, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    next_payment_date = models.DateField("Следующее списание")
    start_date = models.DateField("Дата начала", default=timezone.localdate)
    trial_end_date = models.DateField("Окончание пробного периода", null=True, blank=True)
    website = models.URLField("Сайт сервиса", blank=True)
    status = models.CharField("Статус", max_length=12, choices=Status.choices, default=Status.ACTIVE)
    auto_renew = models.BooleanField("Автопродление", default=True)
    notes = models.TextField("Заметки", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        ordering = ("next_payment_date", "name")
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        indexes = [
            models.Index(fields=("user", "status"), name="sub_user_status_idx"),
            models.Index(fields=("user", "next_payment_date"), name="sub_user_due_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="subscription_amount_positive"),
        ]

    def __str__(self):
        return self.name

    @property
    def monthly_amount(self):
        monthly_factors = {
            self.BillingCycle.WEEKLY: Decimal("52") / Decimal("12"),
            self.BillingCycle.MONTHLY: Decimal("1"),
            self.BillingCycle.QUARTERLY: Decimal("1") / Decimal("3"),
            self.BillingCycle.YEARLY: Decimal("1") / Decimal("12"),
        }
        return (self.amount * monthly_factors[self.billing_cycle]).quantize(Decimal("0.01"))

    @property
    def annual_amount(self):
        annual_factors = {
            self.BillingCycle.WEEKLY: Decimal("52"),
            self.BillingCycle.MONTHLY: Decimal("12"),
            self.BillingCycle.QUARTERLY: Decimal("4"),
            self.BillingCycle.YEARLY: Decimal("1"),
        }
        return (self.amount * annual_factors[self.billing_cycle]).quantize(Decimal("0.01"))

    @property
    def days_until_payment(self):
        return (self.next_payment_date - timezone.localdate()).days

    @property
    def is_due_soon(self):
        return 0 <= self.days_until_payment <= 7

    def clean(self):
        super().clean()
        if self.trial_end_date and self.trial_end_date < self.start_date:
            from django.core.exceptions import ValidationError

            raise ValidationError({"trial_end_date": "Окончание пробного периода не может быть раньше даты начала."})


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Оплачен"
        FAILED = "failed", "Не прошёл"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("Сумма списания", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency = models.CharField("Валюта", max_length=3, choices=CURRENCY_CHOICES)
    paid_at = models.DateField("Дата платежа", default=timezone.localdate)
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.PAID)
    note = models.CharField("Комментарий", max_length=255, blank=True)
    normalized_amount = models.DecimalField("Сумма в основной валюте", max_digits=14, decimal_places=2, null=True, blank=True)
    normalized_currency = models.CharField("Основная валюта", max_length=3, blank=True)
    exchange_rate = models.DecimalField("Курс конвертации", max_digits=18, decimal_places=8, null=True, blank=True)
    exchange_rate_date = models.DateField("Дата курса", null=True, blank=True)
    created_at = models.DateTimeField("Запись создана", auto_now_add=True)

    class Meta:
        ordering = ("-paid_at", "-created_at")
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        indexes = [models.Index(fields=("subscription", "paid_at"), name="payment_sub_date_idx")]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")]

    def __str__(self):
        return f"{self.subscription.name}: {self.amount} {self.currency}"


class PriceChange(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="price_changes")
    old_amount = models.DecimalField("Старая стоимость", max_digits=12, decimal_places=2)
    old_currency = models.CharField("Старая валюта", max_length=3, choices=CURRENCY_CHOICES)
    new_amount = models.DecimalField("Новая стоимость", max_digits=12, decimal_places=2)
    new_currency = models.CharField("Новая валюта", max_length=3, choices=CURRENCY_CHOICES)
    changed_at = models.DateTimeField("Дата изменения", default=timezone.now)
    note = models.CharField("Причина изменения", max_length=255, blank=True)

    class Meta:
        ordering = ("-changed_at",)
        verbose_name = "Изменение стоимости"
        verbose_name_plural = "История стоимости"

    def __str__(self):
        return f"{self.subscription.name}: {self.old_amount} → {self.new_amount}"


class Reminder(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="reminders")
    days_before = models.PositiveSmallIntegerField(
        "За сколько дней напомнить",
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
    )
    is_enabled = models.BooleanField("Напоминание активно", default=True)
    last_sent_at = models.DateTimeField("Последнее уведомление", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("days_before",)
        verbose_name = "Напоминание"
        verbose_name_plural = "Напоминания"
        constraints = [
            models.UniqueConstraint(fields=("subscription", "days_before"), name="unique_subscription_reminder_days"),
        ]

    def __str__(self):
        return f"{self.subscription.name}: за {self.days_before} дн."


class ExchangeRate(models.Model):
    base_currency = models.CharField("Базовая валюта", max_length=3)
    quote_currency = models.CharField("Котируемая валюта", max_length=3)
    rate = models.DecimalField("Курс", max_digits=18, decimal_places=8)
    rate_date = models.DateField("Дата курса")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Валютный курс"
        verbose_name_plural = "Валютные курсы"
        constraints = [
            models.UniqueConstraint(fields=("base_currency", "quote_currency", "rate_date"), name="unique_exchange_rate_day"),
        ]
        indexes = [models.Index(fields=("base_currency", "quote_currency", "rate_date"), name="exchange_rate_lookup_idx")]

    def __str__(self):
        return f"1 {self.base_currency} = {self.rate} {self.quote_currency}"
