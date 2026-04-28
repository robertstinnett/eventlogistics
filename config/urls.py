from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from config.health import liveness, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.users.urls")),
    path("team/", include("apps.accounts.urls")),
    path("billing/", include("apps.plans.urls")),
    path("events/", include("apps.events.urls")),
    path("participants/", include("apps.participants.urls")),
    path("spaces/", include("apps.spaces.urls")),
    path("finance/", include("apps.finance.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("api/", include("apps.api.urls")),
    path("healthz/", liveness, name="healthz"),
    path("readyz/", readiness, name="readyz"),
    path("", TemplateView.as_view(template_name="core/home.html"), name="home"),
]
