from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    EventViewSet,
    ExhibitorViewSet,
    PerformerViewSet,
    SpaceTypeViewSet,
    VendorViewSet,
    create_space_booking,
    integration_token_view,
)

router = DefaultRouter()
router.register(r"events", EventViewSet, basename="api-events")
router.register(r"vendors", VendorViewSet, basename="api-vendors")
router.register(r"performers", PerformerViewSet, basename="api-performers")
router.register(r"exhibitors", ExhibitorViewSet, basename="api-exhibitors")
router.register(r"space-types", SpaceTypeViewSet, basename="api-space-types")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", integration_token_view, name="api-token"),
    path("space-bookings/", create_space_booking, name="api-space-bookings"),
]