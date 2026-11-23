from decimal import Decimal

from django import forms

from .models import Payment, Reminder, Subscription, SubscriptionCategory


class StyledModelForm(forms.ModelForm):
    def apply_styles(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "form-control")
                field.widget.attrs.setdefault("rows", 3)
            else:
                field.widget.attrs.setdefault("class", "form-control")


class SubscriptionForm(StyledModelForm):
    class Meta:
        model = Subscription
        fields = (
            "name",
            "provider",
            "category",
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
        )
        widgets = {
            "next_payment_date": forms.DateInput(attrs={"type": "date"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "trial_end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["name"].widget.attrs["placeholder"] = "Например, Spotify Premium"
        self.fields["provider"].widget.attrs["placeholder"] = "Компания или сервис"
        self.fields["website"].widget.attrs["placeholder"] = "https://example.com"
        self.fields["notes"].required = False

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= Decimal("0"):
            raise forms.ValidationError("Стоимость должна быть больше нуля.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        trial_end_date = cleaned_data.get("trial_end_date")
        if start_date and trial_end_date and trial_end_date < start_date:
            self.add_error("trial_end_date", "Пробный период не может закончиться раньше начала подписки.")
        return cleaned_data


class PaymentForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ("amount", "currency", "paid_at", "status", "note")
        widgets = {"paid_at": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["note"].required = False

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= Decimal("0"):
            raise forms.ValidationError("Сумма платежа должна быть больше нуля.")
        return amount


class ReminderForm(StyledModelForm):
    class Meta:
        model = Reminder
        fields = ("days_before", "is_enabled")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def clean(self):
        cleaned_data = super().clean()
        subscription = self.instance.subscription
        days_before = cleaned_data.get("days_before")
        if subscription and days_before is not None:
            duplicate = Reminder.objects.filter(
                subscription=subscription, days_before=days_before
            ).exclude(pk=self.instance.pk).exists()
            if duplicate:
                self.add_error("days_before", "Для этого срока напоминание уже настроено.")
        return cleaned_data


class SubscriptionFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=100,
        label="Поиск",
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Название или сервис"}),
    )
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[("", "Все статусы"), *Subscription.Status.choices],
        widget=forms.Select(attrs={"class": "form-select filter-select"}),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=SubscriptionCategory.objects.none(),
        label="Категория",
        empty_label="Все категории",
        widget=forms.Select(attrs={"class": "form-select filter-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = SubscriptionCategory.objects.all()


class ConfirmationForm(forms.Form):
    """Empty confirmation form used for state-changing POST actions."""
