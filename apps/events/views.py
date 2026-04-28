from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.services import can_manage_account, get_primary_account_for_user
from apps.auditlog.services import log_account_action
from apps.events.forms import EventForm
from apps.events.models import Event
from apps.plans.services import can_create_active_event


def _get_event_for_user_or_404(user, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not can_manage_account(user, event.account):
        raise Http404("Event not found")
    return event


@login_required
def event_list_view(request):
    account = get_primary_account_for_user(request.user)
    events = Event.objects.none()
    if account:
        events = Event.objects.filter(account=account).order_by("starts_at")
    return render(request, "events/list.html", {"events": events, "account": account})


@login_required
def event_create_view(request):
    account = get_primary_account_for_user(request.user)
    if not account:
        messages.error(request, "No account found for your user.")
        return redirect("event-list")

    subscription = account.subscription_state

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            if not can_create_active_event(account, subscription.plan):
                form.add_error(None, "Your tier allows only one active/upcoming event at a time.")
            else:
                event = form.save(commit=False)
                event.account = account
                event.save()
                log_account_action(
                    account=account,
                    actor=request.user,
                    action="event.created",
                    event=event,
                    target=event,
                    message=f"Event created via web: {event.name}.",
                    metadata={"source": "web"},
                )
                messages.success(request, "Event created.")
                return redirect("event-detail", event_id=event.id)
    else:
        form = EventForm()

    return render(request, "events/form.html", {"form": form, "account": account})


@login_required
def event_detail_view(request, event_id):
    event = _get_event_for_user_or_404(request.user, event_id)
    return render(request, "events/detail.html", {"event": event})