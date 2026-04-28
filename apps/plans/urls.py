from django.urls import path

from apps.plans.views import subscription_overview_view

urlpatterns = [
    path("", subscription_overview_view, name="billing-overview"),
]
