from django.urls import path

from apps.participants.views import (
    exhibitor_update_view,
    exhibitor_create_view,
    participant_list_view,
    performer_update_view,
    performer_create_view,
    vendor_update_view,
    vendor_create_view,
)

urlpatterns = [
    path("event/<int:event_id>/", participant_list_view, name="participant-list"),
    path("event/<int:event_id>/vendors/new/", vendor_create_view, name="vendor-create"),
    path("event/<int:event_id>/vendors/<int:vendor_id>/edit/", vendor_update_view, name="vendor-update"),
    path("event/<int:event_id>/performers/new/", performer_create_view, name="performer-create"),
    path(
        "event/<int:event_id>/performers/<int:performer_id>/edit/",
        performer_update_view,
        name="performer-update",
    ),
    path("event/<int:event_id>/exhibitors/new/", exhibitor_create_view, name="exhibitor-create"),
    path(
        "event/<int:event_id>/exhibitors/<int:exhibitor_id>/edit/",
        exhibitor_update_view,
        name="exhibitor-update",
    ),
]