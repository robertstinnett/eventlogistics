from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services import provision_account_for_user
from apps.events.models import Event
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Exhibitor, Performer, Vendor
from apps.spaces.models import SpaceBooking, SpaceType
from apps.users.models import User


class ParticipantEditViewsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.owner, "Owner Org")
        now = timezone.now()
        self.event = Event.objects.create(
            account=self.account,
            name="Participants Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        self.vendor = Vendor.objects.create(event=self.event, name="Vendor One", email="old-v@example.com")
        self.performer = Performer.objects.create(event=self.event, name="Performer One", genre="Rock")
        self.exhibitor = Exhibitor.objects.create(event=self.event, name="Exhibitor One", category="Art")
        self.space_type = SpaceType.objects.create(
            event=self.event,
            name="Premium Booth",
            price="200.00",
            fee_percent="5.00",
            total_quantity=5,
        )

    def test_vendor_edit_updates_entry(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vendor-update", kwargs={"event_id": self.event.id, "vendor_id": self.vendor.id}),
            {
                "name": "Vendor Updated",
                "email": "new-v@example.com",
                "phone": "",
                "address": "",
                "tax_id": "",
                "vendor_type": "",
                "website": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.name, "Vendor Updated")
        self.assertEqual(self.vendor.email, "new-v@example.com")

    def test_performer_edit_updates_entry(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("performer-update", kwargs={"event_id": self.event.id, "performer_id": self.performer.id}),
            {
                "name": "Performer Updated",
                "email": "",
                "phone": "",
                "genre": "Jazz",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.performer.refresh_from_db()
        self.assertEqual(self.performer.name, "Performer Updated")
        self.assertEqual(self.performer.genre, "Jazz")

    def test_exhibitor_edit_updates_entry(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("exhibitor-update", kwargs={"event_id": self.event.id, "exhibitor_id": self.exhibitor.id}),
            {
                "name": "Exhibitor Updated",
                "email": "",
                "phone": "",
                "category": "Food",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.exhibitor.refresh_from_db()
        self.assertEqual(self.exhibitor.name, "Exhibitor Updated")
        self.assertEqual(self.exhibitor.category, "Food")

    def test_vendor_edit_shows_assigned_spaces(self):
        SpaceBooking.objects.create(
            event=self.event,
            space_type=self.space_type,
            vendor=self.vendor,
            quantity=2,
            unit_price_snapshot="200.00",
            fee_percent_snapshot="5.00",
        )

        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("vendor-update", kwargs={"event_id": self.event.id, "vendor_id": self.vendor.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned spaces")
        self.assertContains(response, "Premium Booth x 2")

    def test_vendor_edit_shows_empty_assigned_spaces_state(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("vendor-update", kwargs={"event_id": self.event.id, "vendor_id": self.vendor.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned spaces")
        self.assertContains(response, "No spaces assigned yet.")

    def test_vendor_edit_can_assign_space(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vendor-update", kwargs={"event_id": self.event.id, "vendor_id": self.vendor.id}),
            {
                "assign_space": "1",
                "vendor": self.vendor.id,
                "space_type": self.space_type.id,
                "quantity": 2,
            },
        )

        self.assertEqual(response.status_code, 302)
        booking = SpaceBooking.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(booking.space_type, self.space_type)
        self.assertEqual(booking.quantity, 2)
        entry = VendorLedgerEntry.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(str(entry.amount), "400.00")

    def test_vendor_edit_can_delete_space(self):
        booking = SpaceBooking.objects.create(
            event=self.event,
            space_type=self.space_type,
            vendor=self.vendor,
            quantity=2,
            unit_price_snapshot="200.00",
            fee_percent_snapshot="5.00",
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vendor-update", kwargs={"event_id": self.event.id, "vendor_id": self.vendor.id}),
            {
                "delete_space_booking": "1",
                "booking_id": booking.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpaceBooking.objects.filter(id=booking.id).exists())
        entry = VendorLedgerEntry.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(str(entry.amount), "-400.00")
