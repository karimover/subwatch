from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("default_currency", models.CharField(choices=[("EUR", "EUR — евро"), ("USD", "USD — доллар США"), ("GBP", "GBP — фунт стерлингов"), ("RUB", "RUB — российский рубль"), ("CHF", "CHF — швейцарский франк"), ("PLN", "PLN — польский злотый"), ("CZK", "CZK — чешская крона"), ("SEK", "SEK — шведская крона"), ("NOK", "NOK — норвежская крона"), ("DKK", "DKK — датская крона"), ("HUF", "HUF — венгерский форинт"), ("TRY", "TRY — турецкая лира"), ("CAD", "CAD — канадский доллар"), ("AUD", "AUD — австралийский доллар"), ("JPY", "JPY — японская иена"), ("CNY", "CNY — китайский юань"), ("INR", "INR — индийская рупия"), ("NZD", "NZD — новозеландский доллар"), ("SGD", "SGD — сингапурский доллар"), ("UAH", "UAH — украинская гривна")], default="EUR", max_length=3)),
                ("reminder_days", models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Настройки пользователя", "verbose_name_plural": "Настройки пользователей"},
        ),
    ]
