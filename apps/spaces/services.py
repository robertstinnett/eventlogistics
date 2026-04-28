from django.db import transaction
from django.db.models import Sum

from apps.finance.models import VendorLedgerEntry
from apps.spaces.models import SpaceType, SpaceBooking


def _create_space_ledger_charge(event, vendor, space_type, quantity, amount):
    VendorLedgerEntry.objects.create(
        event=event,
        vendor=vendor,
        entry_type=VendorLedgerEntry.EntryType.CHARGE,
        amount=amount,
        note=f"Space assignment: {space_type.name} x {quantity}",
    )


def _create_space_ledger_reversal(event, vendor, space_type, quantity, amount):
    VendorLedgerEntry.objects.create(
        event=event,
        vendor=vendor,
        entry_type=VendorLedgerEntry.EntryType.CHARGE,
        amount=-amount,
        note=f"Space removal: {space_type.name} x {quantity}",
    )


@transaction.atomic
def book_space(event, space_type_id, vendor, quantity):
    # Row-level lock blocks concurrent updates for the same space type.
    space_type = SpaceType.objects.select_for_update().get(id=space_type_id, event=event)

    current = (
        SpaceBooking.objects.filter(space_type=space_type)
        .aggregate(total=Sum("quantity"))
        .get("total")
        or 0
    )

    if current + quantity > space_type.total_quantity:
        raise ValueError("Not enough inventory for selected space type.")

    booking, created = SpaceBooking.objects.get_or_create(
        event=event,
        space_type=space_type,
        vendor=vendor,
        defaults={
            "quantity": quantity,
            "unit_price_snapshot": space_type.price,
            "fee_percent_snapshot": space_type.fee_percent,
        },
    )

    if not created:
        new_qty = booking.quantity + quantity
        if current - booking.quantity + new_qty > space_type.total_quantity:
            raise ValueError("Not enough inventory for selected space type.")
        booking.quantity = new_qty
        booking.save(update_fields=["quantity"])

    _create_space_ledger_charge(
        event=event,
        vendor=vendor,
        space_type=space_type,
        quantity=quantity,
        amount=space_type.price * quantity,
    )

    return booking


@transaction.atomic
def unassign_space_booking(booking):
    _create_space_ledger_reversal(
        event=booking.event,
        vendor=booking.vendor,
        space_type=booking.space_type,
        quantity=booking.quantity,
        amount=booking.unit_price_snapshot * booking.quantity,
    )
    booking.delete()


@transaction.atomic
def update_space_booking_quantity(booking, new_quantity):
    booking = SpaceBooking.objects.select_related("space_type", "vendor").select_for_update().get(id=booking.id)
    space_type = SpaceType.objects.select_for_update().get(id=booking.space_type_id, event=booking.event)

    if new_quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    old_quantity = booking.quantity
    delta = new_quantity - old_quantity

    if delta == 0:
        return booking

    current = (
        SpaceBooking.objects.filter(space_type=space_type)
        .aggregate(total=Sum("quantity"))
        .get("total")
        or 0
    )

    if delta > 0 and current - old_quantity + new_quantity > space_type.total_quantity:
        raise ValueError("Not enough inventory for selected space type.")

    booking.quantity = new_quantity
    booking.save(update_fields=["quantity"])

    if delta > 0:
        _create_space_ledger_charge(
            event=booking.event,
            vendor=booking.vendor,
            space_type=space_type,
            quantity=delta,
            amount=space_type.price * delta,
        )
    else:
        _create_space_ledger_reversal(
            event=booking.event,
            vendor=booking.vendor,
            space_type=space_type,
            quantity=abs(delta),
            amount=booking.unit_price_snapshot * abs(delta),
        )

    return booking
