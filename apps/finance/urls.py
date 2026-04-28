from django.urls import path

from apps.finance.views import (
    account_ledger_export_csv_view,
    event_ledger_export_csv_view,
    ledger_entry_create_view,
    ledger_list_view,
)

urlpatterns = [
    path("account/ledger/export.csv", account_ledger_export_csv_view, name="account-ledger-export-csv"),
    path("event/<int:event_id>/ledger/", ledger_list_view, name="ledger-list"),
    path("event/<int:event_id>/ledger/new/", ledger_entry_create_view, name="ledger-entry-create"),
    path("event/<int:event_id>/ledger/export.csv", event_ledger_export_csv_view, name="event-ledger-export-csv"),
]
