import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.services import can_manage_account, get_primary_account_for_user
from apps.auditlog.services import log_account_action
from apps.events.models import Event
from apps.finance.forms import VendorLedgerEntryForm
from apps.finance.models import VendorLedgerEntry


def _event_for_finance_or_404(user, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not can_manage_account(user, event.account):
        raise Http404("Event not found")
    return event


@login_required
def ledger_list_view(request, event_id):
    event = _event_for_finance_or_404(request.user, event_id)
    entries = VendorLedgerEntry.objects.filter(event=event).select_related("vendor")

    total_billed = sum(e.amount for e in entries if e.entry_type == VendorLedgerEntry.EntryType.CHARGE)
    total_paid = sum(e.amount for e in entries if e.entry_type == VendorLedgerEntry.EntryType.PAYMENT)
    outstanding = total_billed - total_paid

    return render(
        request,
        "finance/ledger_list.html",
        {
            "event": event,
            "entries": entries,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "outstanding": outstanding,
        },
    )


@login_required
def ledger_entry_create_view(request, event_id):
    event = _event_for_finance_or_404(request.user, event_id)

    if request.method == "POST":
        form = VendorLedgerEntryForm(request.POST, event=event)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.event = event
            entry.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="finance.ledger_entry.created",
                event=event,
                target=entry,
                message=f"{entry.entry_type} entry for vendor {entry.vendor_id} amount {entry.amount}.",
                metadata={
                    "vendor_id": entry.vendor_id,
                    "entry_type": entry.entry_type,
                    "amount": str(entry.amount),
                },
            )
            messages.success(request, "Ledger entry created.")
            return redirect("ledger-list", event_id=event.id)
    else:
        form = VendorLedgerEntryForm(event=event)

    return render(request, "finance/ledger_form.html", {"event": event, "form": form})


def _ledger_csv_response(filename):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(["event_id", "event_name", "vendor_id", "vendor_name", "entry_type", "amount", "note", "created_at"])
    return response, writer


@login_required
def event_ledger_export_csv_view(request, event_id):
    event = _event_for_finance_or_404(request.user, event_id)
    entries = VendorLedgerEntry.objects.filter(event=event).select_related("vendor", "event").order_by("created_at", "id")

    response, writer = _ledger_csv_response(f"event_{event.id}_ledger.csv")
    for entry in entries:
        writer.writerow(
            [
                entry.event_id,
                entry.event.name,
                entry.vendor_id,
                entry.vendor.name,
                entry.entry_type,
                entry.amount,
                entry.note,
                entry.created_at.isoformat(),
            ]
        )
    return response


@login_required
def account_ledger_export_csv_view(request):
    account = get_primary_account_for_user(request.user)
    if not account or not can_manage_account(request.user, account):
        raise Http404("Account not found")

    entries = (
        VendorLedgerEntry.objects.filter(event__account=account)
        .select_related("vendor", "event")
        .order_by("event_id", "created_at", "id")
    )

    response, writer = _ledger_csv_response(f"account_{account.id}_ledger.csv")
    for entry in entries:
        writer.writerow(
            [
                entry.event_id,
                entry.event.name,
                entry.vendor_id,
                entry.vendor.name,
                entry.entry_type,
                entry.amount,
                entry.note,
                entry.created_at.isoformat(),
            ]
        )
    return response
