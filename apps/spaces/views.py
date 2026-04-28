from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.services import can_manage_account
from apps.auditlog.services import log_account_action
from apps.events.models import Event
from apps.spaces.forms import SpaceBookingForm, SpaceBookingQuantityForm, SpaceTypeForm
from apps.spaces.models import SpaceBooking, SpaceType
from apps.spaces.services import unassign_space_booking


def _event_or_404(user, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not can_manage_account(user, event.account):
        raise Http404("Event not found")
    return event


@login_required
def space_list_view(request, event_id):
    event = _event_or_404(request.user, event_id)
    space_types = SpaceType.objects.filter(event=event)
    bookings = SpaceBooking.objects.filter(event=event).select_related("vendor", "space_type")
    return render(
        request,
        "spaces/list.html",
        {"event": event, "space_types": space_types, "bookings": bookings},
    )


@login_required
def space_type_create_view(request, event_id):
    event = _event_or_404(request.user, event_id)
    if request.method == "POST":
        form = SpaceTypeForm(request.POST)
        if form.is_valid():
            space_type = form.save(commit=False)
            space_type.event = event
            space_type.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="space.type.created",
                event=event,
                target=space_type,
                message=f"Space type created: {space_type.name}.",
            )
            messages.success(request, "Space type created.")
            return redirect("space-list", event_id=event.id)
    else:
        form = SpaceTypeForm()

    return render(
        request,
        "spaces/form_space_type.html",
        {"event": event, "form": form},
    )


@login_required
def space_booking_create_view(request, event_id):
    event = _event_or_404(request.user, event_id)
    if request.method == "POST":
        form = SpaceBookingForm(request.POST, event=event)
        if form.is_valid():
            try:
                booking = form.save()
                log_account_action(
                    account=event.account,
                    actor=request.user,
                    action="space.booking.created",
                    event=event,
                    target=booking,
                    message=f"Space assigned to vendor {booking.vendor_id} (quantity {booking.quantity}).",
                )
                messages.success(request, "Space assigned.")
                return redirect("space-list", event_id=event.id)
            except Exception as exc:
                form.add_error(None, str(exc))
    else:
        form = SpaceBookingForm(event=event)

    return render(
        request,
        "spaces/form_booking.html",
        {"event": event, "form": form},
    )


@login_required
def space_booking_update_view(request, event_id, booking_id):
    event = _event_or_404(request.user, event_id)
    booking = get_object_or_404(
        SpaceBooking.objects.select_related("vendor", "space_type"),
        id=booking_id,
        event=event,
    )
    if request.method == "POST":
        form = SpaceBookingQuantityForm(request.POST, booking=booking)
        if form.is_valid():
            previous_quantity = booking.quantity
            updated = form.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="space.booking.updated",
                event=event,
                target=updated,
                message=(
                    f"Space booking updated for vendor {updated.vendor_id}: "
                    f"{updated.space_type.name} quantity {previous_quantity} -> {updated.quantity}."
                ),
            )
            messages.success(request, "Space assignment updated.")
            return redirect("space-list", event_id=event.id)
    else:
        form = SpaceBookingQuantityForm(booking=booking)

    return render(
        request,
        "spaces/form_booking.html",
        {"event": event, "form": form, "booking": booking},
    )


@login_required
def space_booking_delete_view(request, event_id, booking_id):
    event = _event_or_404(request.user, event_id)
    booking = get_object_or_404(
        SpaceBooking.objects.select_related("vendor", "space_type"),
        id=booking_id,
        event=event,
    )

    if request.method == "POST":
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
                f"Space booking removed for vendor {vendor_name}: "
                f"{space_type_name} x {quantity}."
            ),
        )
        messages.success(request, "Space assignment removed.")
        return redirect("space-list", event_id=event.id)

    return render(
        request,
        "spaces/confirm_delete_booking.html",
        {"event": event, "booking": booking},
    )


@login_required
def space_type_update_view(request, event_id, space_type_id):
    event = _event_or_404(request.user, event_id)
    space_type = get_object_or_404(SpaceType, id=space_type_id, event=event)
    if request.method == "POST":
        form = SpaceTypeForm(request.POST, instance=space_type)
        if form.is_valid():
            updated = form.save()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="space.type.updated",
                event=event,
                target=updated,
                message=f"Space type updated: {updated.name}.",
            )
            messages.success(request, "Space type updated.")
            return redirect("space-list", event_id=event.id)
    else:
        form = SpaceTypeForm(instance=space_type)
    return render(
        request,
        "spaces/form_space_type.html",
        {"event": event, "form": form, "space_type": space_type},
    )


@login_required
def space_type_delete_view(request, event_id, space_type_id):
    event = _event_or_404(request.user, event_id)
    space_type = get_object_or_404(SpaceType, id=space_type_id, event=event)
    bookings = list(space_type.bookings.select_related("vendor").all())
    has_bookings = bool(bookings)
    other_types = SpaceType.objects.filter(event=event).exclude(id=space_type_id).order_by("name")

    errors = []

    if request.method == "POST":
        if has_bookings:
            replacement_id = request.POST.get("replacement_space_type")
            if not replacement_id:
                errors.append("You must choose a replacement space type before deleting.")
            else:
                replacement = get_object_or_404(SpaceType, id=replacement_id, event=event)
                if replacement.id == space_type.id:
                    errors.append("Replacement must be a different space type.")
                else:
                    # Vendor uniqueness check: if any vendor already has a booking for the replacement type
                    booking_vendor_ids = [b.vendor_id for b in bookings]
                    conflicts = SpaceBooking.objects.filter(
                        space_type=replacement, vendor_id__in=booking_vendor_ids
                    )
                    if conflicts.exists():
                        conflict_names = ", ".join(
                            conflicts.select_related("vendor").values_list("vendor__name", flat=True)
                        )
                        errors.append(
                            f"The following vendors already have a booking for the replacement type and cannot be moved: {conflict_names}."
                        )
                    else:
                        # Capacity check
                        total_needed = sum(b.quantity for b in bookings)
                        if replacement.available_quantity < total_needed:
                            errors.append(
                                f"'{replacement.name}' only has {replacement.available_quantity} space(s) available "
                                f"but {total_needed} are needed to absorb the re-assigned bookings."
                            )

                if not errors:
                    space_type.bookings.update(space_type=replacement)
                    log_account_action(
                        account=event.account,
                        actor=request.user,
                        action="space.booking.reassigned",
                        event=event,
                        target=replacement,
                        message=(
                            f"{len(bookings)} booking(s) moved from '{space_type.name}' "
                            f"to '{replacement.name}' before deletion."
                        ),
                    )

        if not errors:
            space_type_name = space_type.name
            space_type.delete()
            log_account_action(
                account=event.account,
                actor=request.user,
                action="space.type.deleted",
                event=event,
                target=None,
                message=f"Space type deleted: {space_type_name}.",
            )
            messages.success(request, f"Space type '{space_type_name}' deleted.")
            return redirect("space-list", event_id=event.id)

    return render(
        request,
        "spaces/confirm_delete_space_type.html",
        {
            "event": event,
            "space_type": space_type,
            "bookings": bookings,
            "has_bookings": has_bookings,
            "other_types": other_types,
            "errors": errors,
        },
    )