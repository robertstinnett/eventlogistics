from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services import provision_account_for_user
from apps.auditlog.models import AuditLogEntry
from apps.events.models import Event
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Vendor
from apps.users.models import User


class FinanceLedgerViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.owner, "Owner Org")
        now = timezone.now()

        self.event = Event.objects.create(
            account=self.account,
            name="Finance Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        self.vendor = Vendor.objects.create(event=self.event, name="Vendor One")

    def test_owner_can_create_ledger_entry(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("ledger-entry-create", kwargs={"event_id": self.event.id}),
            {
                "vendor": self.vendor.id,
                "entry_type": VendorLedgerEntry.EntryType.CHARGE,
                "amount": "150.00",
                "note": "Booth fee",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(VendorLedgerEntry.objects.filter(event=self.event).count(), 1)
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="finance.ledger_entry.created").exists()
        )

    def test_unauthorized_user_gets_404_on_ledger_page(self):
        outsider = User.objects.create_user(email="outsider@example.com", password="pass12345")
        provision_account_for_user(outsider, "Outsider Org")

        self.client.force_login(outsider)
        response = self.client.get(reverse("ledger-list", kwargs={"event_id": self.event.id}))

        self.assertEqual(response.status_code, 404)

    def test_ledger_totals_render_correctly(self):
        VendorLedgerEntry.objects.create(
            event=self.event,
            vendor=self.vendor,
            entry_type=VendorLedgerEntry.EntryType.CHARGE,
            amount=Decimal("300.00"),
            note="Charge",
        )
        VendorLedgerEntry.objects.create(
            event=self.event,
            vendor=self.vendor,
            entry_type=VendorLedgerEntry.EntryType.PAYMENT,
            amount=Decimal("125.00"),
            note="Payment",
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("ledger-list", kwargs={"event_id": self.event.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "300.00")
        self.assertContains(response, "125.00")
        self.assertContains(response, "175.00")

    def test_event_ledger_csv_export_contains_expected_rows(self):
        VendorLedgerEntry.objects.create(
            event=self.event,
            vendor=self.vendor,
            entry_type=VendorLedgerEntry.EntryType.CHARGE,
            amount=Decimal("300.00"),
            note="Charge",
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("event-ledger-export-csv", kwargs={"event_id": self.event.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("event_", response["Content-Disposition"])
        body = response.content.decode("utf-8")
        self.assertIn("event_id,event_name,vendor_id,vendor_name,entry_type,amount,note,created_at", body)
        self.assertIn("Finance Event", body)
        self.assertIn("Vendor One", body)
        self.assertIn("charge", body)

    def test_account_ledger_csv_export_includes_account_events_only(self):
        other_owner = User.objects.create_user(email="other@example.com", password="pass12345")
        other_account = provision_account_for_user(other_owner, "Other Org")

        now = timezone.now()
        other_event = Event.objects.create(
            account=other_account,
            name="Other Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        other_vendor = Vendor.objects.create(event=other_event, name="Other Vendor")

        VendorLedgerEntry.objects.create(
            event=self.event,
            vendor=self.vendor,
            entry_type=VendorLedgerEntry.EntryType.PAYMENT,
            amount=Decimal("25.00"),
            note="Mine",
        )
        VendorLedgerEntry.objects.create(
            event=other_event,
            vendor=other_vendor,
            entry_type=VendorLedgerEntry.EntryType.CHARGE,
            amount=Decimal("100.00"),
            note="Other",
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("account-ledger-export-csv"))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("Finance Event", body)
        self.assertNotIn("Other Event", body)

    def test_outsider_cannot_export_other_event_csv_but_can_export_own_account_csv(self):
        outsider = User.objects.create_user(email="outsider2@example.com", password="pass12345")
        provision_account_for_user(outsider, "Outsider Org")

        self.client.force_login(outsider)
        event_response = self.client.get(reverse("event-ledger-export-csv", kwargs={"event_id": self.event.id}))
        account_response = self.client.get(reverse("account-ledger-export-csv"))

        self.assertEqual(event_response.status_code, 404)
        self.assertEqual(account_response.status_code, 200)
