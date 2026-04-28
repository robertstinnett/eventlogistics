from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.services import can_manage_account
from apps.auditlog.services import log_account_action
from apps.events.models import Event
from apps.participants.forms import ExhibitorForm, PerformerForm, VendorForm
from apps.participants.models import Exhibitor, Performer, Vendor
from apps.spaces.forms import SpaceBookingForm
from apps.spaces.models import SpaceBooking
from apps.spaces.services import unassign_space_booking


def _event_for_manage_or_404(user, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not can_manage_account(user, event.account):
        raise Http404("Event not found")
    return event


@login_required
def participant_list_view(request, event_id):
    event = _event_for_manage_or_404(request.user, event_id)
    context = {
        "event": event,
        "vendors": Vendor.objects.filter(event=event),
        "performers": Performer.objects.filter(event=event),
        "exhibitors": Exhibitor.objects.filter(event=event),
    }
    return render(request, "participants/list.html", context)


@login_required
def vendor_create_view(request, event_id):
    event = _event_for_manage_or_404(request.user, event_id)
    if request.method == "POST":
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.event = event
            vendor.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="participant.vendor.created",
                event=event,
                target=vendor,
                message=f"Vendor added: {vendor.name}.",
            )
            messages.success(request, "Vendor added.")
            return redirect("participant-list", event_id=event.id)
    else:
        form = VendorForm()
    return render(request, "participants/form.html", {"form": form, "event": event, "title": "Add Vendor"})


@login_required
def performer_create_view(request, event_id):
    event = _event_for_manage_or_404(request.user, event_id)
    if request.method == "POST":
        form = PerformerForm(request.POST)
        if form.is_valid():
            performer = form.save(commit=False)
            performer.event = event
            performer.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="participant.performer.created",
                event=event,
                target=performer,
                message=f"Performer added: {performer.name}.",
            )
            messages.success(request, "Performer added.")
            return redirect("participant-list", event_id=event.id)
    else:
        form = PerformerForm()
    return render(request, "participants/form.html", {"form": form, "event": event, "title": "Add Performer"})


@login_required
def exhibitor_create_view(request, event_id):
    event = _event_for_manage_or_404(request.user, event_id)
    if request.method == "POST":
        form = ExhibitorForm(request.POST)
        if form.is_valid():
            exhibitor = form.save(commit=False)
            exhibitor.event = event
            exhibitor.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="participant.exhibitor.created",
                event=event,
                target=exhibitor,
                message=f"Exhibitor added: {exhibitor.name}.",
            )
            messages.success(request, "Exhibitor added.")
            return redirect("participant-list", event_id=event.id)
    else:
        form = ExhibitorForm()
    return render(request, "participants/form.html", {"form": form, "event": event, "title": "Add Exhibitor"})


@login_required
def vendor_update_view(request, event_id, vendor_id):
    event = _event_for_manage_or_404(request.user, event_id)
    vendor = get_object_or_404(Vendor, id=vendor_id, event=event)
    if request.method == "POST":
        if "assign_space" in request.POST:
            form = VendorForm(instance=vendor)
            space_form = SpaceBookingForm(request.POST, event=event, fixed_vendor=vendor)
            if space_form.is_valid():
                try:
                    booking = space_form.save()
                    log_account_action(
                        account=event.account,
                        actor=request.user,
                        action="space.booking.created",
                        event=event,
                        target=booking,
                        message=(
                            f"Space assigned from vendor page to vendor {booking.vendor_id} "
                            f"(quantity {booking.quantity})."
                        ),
                    )
                    messages.success(request, "Space assigned.")
                    return redirect("vendor-update", event_id=event.id, vendor_id=vendor.id)
                except Exception as exc:
                    space_form.add_error(None, str(exc))
        elif "delete_space_booking" in request.POST:
            form = VendorForm(instance=vendor)
            space_form = SpaceBookingForm(event=event, fixed_vendor=vendor)
            booking = get_object_or_404(
                SpaceBooking.objects.select_related("vendor", "space_type"),
                id=request.POST.get("booking_id"),
                event=event,
                vendor=vendor,
            )
            vendor_name = booking.vendor.name
            space_type_name = booking.space_type.name
            quantity = booking.quantity
            unassign_space_booking(booking)
            log_account_action(
                account=event.account,
                actor=request.user,
                action="space.booking.deleted",
                event=event,
                target=None,
                message=(
                    f"Space booking removed from vendor page for vendor {vendor_name}: "
                    f"{space_type_name} x {quantity}."
                ),
            )
            messages.success(request, "Space assignment removed.")
            return redirect("vendor-update", event_id=event.id, vendor_id=vendor.id)
        else:
            form = VendorForm(request.POST, instance=vendor)
            space_form = SpaceBookingForm(event=event, fixed_vendor=vendor)
            if form.is_valid():
                updated = form.save()
                log_account_action(
                    account=event.account,
                    actor=request.user,
                    action="participant.vendor.updated",
                    event=event,
                    target=updated,
                    message=f"Vendor updated: {updated.name}.",
                )
                messages.success(request, "Vendor updated.")
                return redirect("participant-list", event_id=event.id)
    else:
        form = VendorForm(instance=vendor)
        space_form = SpaceBookingForm(event=event, fixed_vendor=vendor)
    space_bookings = SpaceBooking.objects.filter(event=event, vendor=vendor).select_related("space_type")
    return render(
        request,
        "participants/form.html",
        {
            "form": form,
            "event": event,
            "title": "Edit Vendor",
            "vendor": vendor,
            "space_form": space_form,
            "space_bookings": space_bookings,
        },
    )


@login_required
def performer_update_view(request, event_id, performer_id):
    event = _event_for_manage_or_404(request.user, event_id)
    performer = get_object_or_404(Performer, id=performer_id, event=event)
    if request.method == "POST":
        form = PerformerForm(request.POST, instance=performer)
        if form.is_valid():
            updated = form.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="participant.performer.updated",
                event=event,
                target=updated,
                message=f"Performer updated: {updated.name}.",
            )
            messages.success(request, "Performer updated.")
            return redirect("participant-list", event_id=event.id)
    else:
        form = PerformerForm(instance=performer)
    return render(request, "participants/form.html", {"form": form, "event": event, "title": "Edit Performer"})


@login_required
def exhibitor_update_view(request, event_id, exhibitor_id):
    event = _event_for_manage_or_404(request.user, event_id)
    exhibitor = get_object_or_404(Exhibitor, id=exhibitor_id, event=event)
    if request.method == "POST":
        form = ExhibitorForm(request.POST, instance=exhibitor)
        if form.is_valid():
            updated = form.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="participant.exhibitor.updated",
                event=event,
                target=updated,
                message=f"Exhibitor updated: {updated.name}.",
            )
            messages.success(request, "Exhibitor updated.")
            return redirect("participant-list", event_id=event.id)
    else:
        form = ExhibitorForm(instance=exhibitor)
    return render(request, "participants/form.html", {"form": form, "event": event, "title": "Edit Exhibitor"})