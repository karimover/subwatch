from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("subscriptions/", include("subscriptions.urls")),
    path("analytics/", include("analytics.urls")),
    path("api/v1/", include("api.urls")),
]
