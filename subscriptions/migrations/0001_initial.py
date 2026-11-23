from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


CURRENCIES = [
    ("EUR", "EUR — евро"), ("USD", "USD — доллар США"), ("GBP", "GBP — фунт стерлингов"),
    ("RUB", "RUB — российский рубль"), ("CHF", "CHF — швейцарский франк"),
    ("PLN", "PLN — польский злотый"), ("CZK", "CZK — чешская крона"), ("SEK", "SEK — шведская крона"),
    ("NOK", "NOK — норвежская крона"), ("DKK", "DKK — датская крона"), ("HUF", "HUF — венгерский форинт"),
    ("TRY", "TRY — турецкая лира"), ("CAD", "CAD — канадский доллар"), ("AUD", "AUD — австралийский доллар"),
    ("JPY", "JPY — японская иена"), ("CNY", "CNY — китайский юань"), ("INR", "INR — индийская рупия"),
    ("NZD", "NZD — новозеландский доллар"), ("SGD", "SGD — сингапурский доллар"), ("UAH", "UAH — украинская гривна"),
]


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_currency", models.CharField(max_length=3, verbose_name="Базовая валюта")),
                ("quote_currency", models.CharField(max_length=3, verbose_name="Котируемая валюта")),
                ("rate", models.DecimalField(decimal_places=8, max_digits=18, verbose_name="Курс")),
                ("rate_date", models.DateField(verbose_name="Дата курса")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Валютный курс", "verbose_name_plural": "Валютные курсы"},
        ),
        migrations.CreateModel(
            name="SubscriptionCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60, unique=True, verbose_name="Название")),
                ("slug", models.SlugField(max_length=60, unique=True, verbose_name="Код")),
                ("icon", models.CharField(default="layers", max_length=24, verbose_name="Иконка")),
                ("color", models.CharField(default="#8B7CFF", max_length=7, verbose_name="Цвет")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")),
            ],
            options={"verbose_name": "Категория подписок", "verbose_name_plural": "Категории подписок", "ordering": ("sort_order", "name")},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Название подписки")),
                ("provider", models.CharField(blank=True, max_length=100, verbose_name="Провайдер")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="Стоимость")),
                ("currency", models.CharField(choices=CURRENCIES, default="EUR", max_length=3, verbose_name="Валюта")),
                ("billing_cycle", models.CharField(choices=[("weekly", "Еженедельно"), ("monthly", "Ежемесячно"), ("quarterly", "Раз в квартал"), ("yearly", "Ежегодно")], default="monthly", max_length=12, verbose_name="Период оплаты")),
                ("next_payment_date", models.DateField(verbose_name="Следующее списание")),
                ("start_date", models.DateField(default=django.utils.timezone.localdate, verbose_name="Дата начала")),
                ("trial_end_date", models.DateField(blank=True, null=True, verbose_name="Окончание пробного периода")),
                ("website", models.URLField(blank=True, verbose_name="Сайт сервиса")),
                ("status", models.CharField(choices=[("active", "Активна"), ("paused", "Приостановлена"), ("cancelled", "Отменена")], default="active", max_length=12, verbose_name="Статус")),
                ("auto_renew", models.BooleanField(default=True, verbose_name="Автопродление")),
                ("notes", models.TextField(blank=True, verbose_name="Заметки")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создана")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлена")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="subscriptions.subscriptioncategory", verbose_name="Категория")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subscriptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Подписка", "verbose_name_plural": "Подписки", "ordering": ("next_payment_date", "name")},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))], verbose_name="Сумма списания")),
                ("currency", models.CharField(choices=CURRENCIES, max_length=3, verbose_name="Валюта")),
                ("paid_at", models.DateField(default=django.utils.timezone.localdate, verbose_name="Дата платежа")),
                ("status", models.CharField(choices=[("paid", "Оплачен"), ("failed", "Не прошёл")], default="paid", max_length=10, verbose_name="Статус")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="Комментарий")),
                ("normalized_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Сумма в основной валюте")),
                ("normalized_currency", models.CharField(blank=True, max_length=3, verbose_name="Основная валюта")),
                ("exchange_rate", models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True, verbose_name="Курс конвертации")),
                ("exchange_rate_date", models.DateField(blank=True, null=True, verbose_name="Дата курса")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Запись создана")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="subscriptions.subscription")),
            ],
            options={"verbose_name": "Платёж", "verbose_name_plural": "Платежи", "ordering": ("-paid_at", "-created_at")},
        ),
        migrations.CreateModel(
            name="PriceChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("old_amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Старая стоимость")),
                ("old_currency", models.CharField(choices=CURRENCIES, max_length=3, verbose_name="Старая валюта")),
                ("new_amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Новая стоимость")),
                ("new_currency", models.CharField(choices=CURRENCIES, max_length=3, verbose_name="Новая валюта")),
                ("changed_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Дата изменения")),
                ("note", models.CharField(blank=True, max_length=255, verbose_name="Причина изменения")),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="price_changes", to="subscriptions.subscription")),
            ],
            options={"verbose_name": "Изменение стоимости", "verbose_name_plural": "История стоимости", "ordering": ("-changed_at",)},
        ),
        migrations.CreateModel(
            name="Reminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("days_before", models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)], verbose_name="За сколько дней напомнить")),
                ("is_enabled", models.BooleanField(default=True, verbose_name="Напоминание активно")),
                ("last_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Последнее уведомление")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("subscription", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reminders", to="subscriptions.subscription")),
            ],
            options={"verbose_name": "Напоминание", "verbose_name_plural": "Напоминания", "ordering": ("days_before",)},
        ),
        migrations.AddIndex(model_name="subscription", index=models.Index(fields=["user", "status"], name="sub_user_status_idx")),
        migrations.AddIndex(model_name="subscription", index=models.Index(fields=["user", "next_payment_date"], name="sub_user_due_idx")),
        migrations.AddConstraint(model_name="subscription", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="subscription_amount_positive")),
        migrations.AddIndex(model_name="payment", index=models.Index(fields=["subscription", "paid_at"], name="payment_sub_date_idx")),
        migrations.AddConstraint(model_name="payment", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="payment_amount_positive")),
        migrations.AddConstraint(model_name="reminder", constraint=models.UniqueConstraint(fields=("subscription", "days_before"), name="unique_subscription_reminder_days")),
        migrations.AddConstraint(model_name="exchangerate", constraint=models.UniqueConstraint(fields=("base_currency", "quote_currency", "rate_date"), name="unique_exchange_rate_day")),
        migrations.AddIndex(model_name="exchangerate", index=models.Index(fields=["base_currency", "quote_currency", "rate_date"], name="exchange_rate_lookup_idx")),
    ]
