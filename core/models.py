from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


CURRENCY_CHOICES = [
    ("EUR", "EUR — евро"),
    ("USD", "USD — доллар США"),
    ("GBP", "GBP — фунт стерлингов"),
    ("RUB", "RUB — российский рубль"),
    ("CHF", "CHF — швейцарский франк"),
    ("PLN", "PLN — польский злотый"),
    ("CZK", "CZK — чешская крона"),
    ("SEK", "SEK — шведская крона"),
    ("NOK", "NOK — норвежская крона"),
    ("DKK", "DKK — датская крона"),
    ("HUF", "HUF — венгерский форинт"),
    ("TRY", "TRY — турецкая лира"),
    ("CAD", "CAD — канадский доллар"),
    ("AUD", "AUD — австралийский доллар"),
    ("JPY", "JPY — японская иена"),
    ("CNY", "CNY — китайский юань"),
    ("INR", "INR — индийская рупия"),
    ("NZD", "NZD — новозеландский доллар"),
    ("SGD", "SGD — сингапурский доллар"),
    ("UAH", "UAH — украинская гривна"),
]


class UserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    default_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="EUR")
    reminder_days = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"

    def __str__(self):
        return f"Настройки: {self.user.username}"
