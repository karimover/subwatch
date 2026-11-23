from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import UserPreference
from .services import build_payment_analytics


@login_required
def analytics_dashboard(request):
    preference, _ = UserPreference.objects.get_or_create(
        user=request.user, defaults={"default_currency": settings.BASE_CURRENCY}
    )
    data = build_payment_analytics(request.user, preference.default_currency)
    return render(request, "analytics/dashboard.html", {"analytics": data})
