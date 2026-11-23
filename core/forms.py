from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserPreference


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Электронная почта")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Логин"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email


class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ("default_currency", "reminder_days")
        widgets = {
            "default_currency": forms.Select(attrs={"class": "form-select"}),
            "reminder_days": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 30}),
        }
