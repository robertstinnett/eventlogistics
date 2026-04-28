from django.urls import path

from apps.spaces.views import (
    space_booking_create_view,
    space_booking_delete_view,
    space_booking_update_view,
    space_list_view,
    space_type_create_view,
    space_type_delete_view,
    space_type_update_view,
)

urlpatterns = [
    path("event/<int:event_id>/", space_list_view, name="space-list"),
    path("event/<int:event_id>/types/new/", space_type_create_view, name="space-type-create"),
    path("event/<int:event_id>/types/<int:space_type_id>/edit/", space_type_update_view, name="space-type-update"),
    path("event/<int:event_id>/types/<int:space_type_id>/delete/", space_type_delete_view, name="space-type-delete"),
    path("event/<int:event_id>/bookings/new/", space_booking_create_view, name="space-booking-create"),
    path("event/<int:event_id>/bookings/<int:booking_id>/edit/", space_booking_update_view, name="space-booking-update"),
    path("event/<int:event_id>/bookings/<int:booking_id>/delete/", space_booking_delete_view, name="space-booking-delete"),
]