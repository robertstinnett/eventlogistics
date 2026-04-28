from django.db.models import Sum
from django.utils import timezone
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Vendor, Performer, Exhibitor
from apps.spaces.models import SpaceType, SpaceBooking


def event_dashboard_summary(event):
    total_spaces = SpaceType.objects.filter(event=event).aggregate(total=Sum("total_quantity")).get("total") or 0
    booked_spaces = SpaceBooking.objects.filter(event=event).aggregate(total=Sum("quantity")).get("total") or 0

    charges = (
        VendorLedgerEntry.objects.filter(event=event, entry_type=VendorLedgerEntry.EntryType.CHARGE)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )
    payments = (
        VendorLedgerEntry.objects.filter(event=event, entry_type=VendorLedgerEntry.EntryType.PAYMENT)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )

    return {
        "total_spaces": total_spaces,
        "booked_spaces": booked_spaces,
        "occupancy_rate": float((booked_spaces / total_spaces) * 100) if total_spaces else 0,
        "vendors": Vendor.objects.filter(event=event).count(),
        "performers": Performer.objects.filter(event=event).count(),
        "exhibitors": Exhibitor.objects.filter(event=event).count(),
        "total_billed": charges,
        "total_paid": payments,
        "outstanding_balance": charges - payments,
        "days_until_event": max((event.starts_at - timezone.now()).days, 0),
    }
