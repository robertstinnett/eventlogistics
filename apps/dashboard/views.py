from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from apps.accounts.services import can_manage_account
from apps.accounts.services import get_primary_account_for_user
from apps.auditlog.models import AuditLogEntry
from apps.dashboard.services import event_dashboard_summary
from apps.events.models import Event


@login_required
def event_dashboard_view(request, event_id):
    event = Event.objects.get(id=event_id)
    if not can_manage_account(request.user, event.account):
        raise Http404("Event not found")

    summary = event_dashboard_summary(event)
    return render(request, "dashboard/detail.html", {"event": event, "metrics": summary})


@login_required
def account_audit_log_view(request):
    account = get_primary_account_for_user(request.user)
    if not account or not can_manage_account(request.user, account):
        raise Http404("Account not found")

    entries = AuditLogEntry.objects.filter(account=account).select_related("actor", "event")[:200]
    return render(
        request,
        "dashboard/audit_log.html",
        {
            "account": account,
            "entries": entries,
        },
    )