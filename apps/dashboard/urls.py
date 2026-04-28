from django.urls import path

from apps.dashboard.views import account_audit_log_view, event_dashboard_view

urlpatterns = [
    path("event/<int:event_id>/", event_dashboard_view, name="event-dashboard"),
    path("audit-log/", account_audit_log_view, name="account-audit-log"),
]