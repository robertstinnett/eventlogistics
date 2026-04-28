from django.urls import path

from apps.events.views import event_create_view, event_detail_view, event_list_view

urlpatterns = [
    path("", event_list_view, name="event-list"),
    path("new/", event_create_view, name="event-create"),
    path("<int:event_id>/", event_detail_view, name="event-detail"),
]