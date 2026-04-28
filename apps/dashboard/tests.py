from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.services import provision_account_for_user
from apps.dashboard.services import event_dashboard_summary
from apps.events.models import Event
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Exhibitor, Performer, Vendor
from apps.spaces.models import SpaceBooking, SpaceType
from apps.users.models import User


class DashboardSummaryTests(TestCase):
    def test_event_dashboard_summary_aggregates_expected_metrics(self):
        user = User.objects.create_user(email="owner@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Main Event",
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=4),
            status=Event.Status.PUBLISHED,
        )

        vendor = Vendor.objects.create(event=event, name="Vendor One")
        Performer.objects.create(event=event, name="Performer One")
        Exhibitor.objects.create(event=event, name="Exhibitor One")

        space_type = SpaceType.objects.create(
            event=event,
            name="Booth",
            price=Decimal("150.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=10,
        )
        SpaceBooking.objects.create(
            event=event,
            space_type=space_type,
            vendor=vendor,
            quantity=3,
            unit_price_snapshot=Decimal("150.00"),
            fee_percent_snapshot=Decimal("5.00"),
        )

        VendorLedgerEntry.objects.create(
            event=event,
            vendor=vendor,
            entry_type=VendorLedgerEntry.EntryType.CHARGE,
            amount=Decimal("600.00"),
        )
        VendorLedgerEntry.objects.create(
            event=event,
            vendor=vendor,
            entry_type=VendorLedgerEntry.EntryType.PAYMENT,
            amount=Decimal("200.00"),
        )

        summary = event_dashboard_summary(event)

        self.assertEqual(summary["vendors"], 1)
        self.assertEqual(summary["performers"], 1)
        self.assertEqual(summary["exhibitors"], 1)
        self.assertEqual(summary["total_spaces"], 10)
        self.assertEqual(summary["booked_spaces"], 3)
        self.assertEqual(summary["occupancy_rate"], 30.0)
        self.assertEqual(summary["total_billed"], Decimal("600.00"))
        self.assertEqual(summary["total_paid"], Decimal("200.00"))
        self.assertEqual(summary["outstanding_balance"], Decimal("400.00"))
        self.assertGreaterEqual(summary["days_until_event"], 0)