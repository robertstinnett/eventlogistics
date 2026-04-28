from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountMembership
from apps.accounts.services import provision_account_for_user
from apps.events.models import Event
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Vendor
from apps.spaces.models import SpaceBooking, SpaceType
from apps.spaces.services import book_space, unassign_space_booking, update_space_booking_quantity
from apps.users.models import User


class NoOverbookingTests(TestCase):
    def test_book_space_raises_when_inventory_is_exceeded(self):
        user = User.objects.create_user(email="owner@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor_one = Vendor.objects.create(event=event, name="Vendor One")
        vendor_two = Vendor.objects.create(event=event, name="Vendor Two")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=2,
        )

        booking = book_space(event=event, space_type_id=space_type.id, vendor=vendor_one, quantity=2)
        self.assertEqual(booking.quantity, 2)

        with self.assertRaisesMessage(ValueError, "Not enough inventory for selected space type."):
            book_space(event=event, space_type_id=space_type.id, vendor=vendor_two, quantity=1)

        self.assertEqual(SpaceBooking.objects.filter(space_type=space_type).count(), 1)
        self.assertEqual(space_type.available_quantity, 0)

    def test_book_space_creates_charge_ledger_entry_for_added_quantity(self):
        user = User.objects.create_user(email="owner3@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor = Vendor.objects.create(event=event, name="Vendor One")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=5,
        )

        book_space(event=event, space_type_id=space_type.id, vendor=vendor, quantity=2)

        entry = VendorLedgerEntry.objects.get(event=event, vendor=vendor)
        self.assertEqual(entry.entry_type, VendorLedgerEntry.EntryType.CHARGE)
        self.assertEqual(entry.amount, Decimal("500.00"))
        self.assertEqual(entry.note, "Space assignment: 10x10 Booth x 2")

    def test_book_space_existing_booking_charges_only_incremental_quantity(self):
        user = User.objects.create_user(email="owner4@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor = Vendor.objects.create(event=event, name="Vendor One")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=5,
        )

        book_space(event=event, space_type_id=space_type.id, vendor=vendor, quantity=1)
        book_space(event=event, space_type_id=space_type.id, vendor=vendor, quantity=2)

        booking = SpaceBooking.objects.get(event=event, vendor=vendor, space_type=space_type)
        self.assertEqual(booking.quantity, 3)
        self.assertEqual(VendorLedgerEntry.objects.filter(event=event, vendor=vendor).count(), 2)
        total_charged = sum(
            VendorLedgerEntry.objects.filter(event=event, vendor=vendor).values_list("amount", flat=True)
        )
        self.assertEqual(total_charged, Decimal("750.00"))

    def test_unassign_space_booking_creates_negative_charge_and_deletes_booking(self):
        user = User.objects.create_user(email="owner5@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor = Vendor.objects.create(event=event, name="Vendor One")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=5,
        )
        booking = SpaceBooking.objects.create(
            event=event,
            space_type=space_type,
            vendor=vendor,
            quantity=2,
            unit_price_snapshot=Decimal("250.00"),
            fee_percent_snapshot=Decimal("5.00"),
        )

        unassign_space_booking(booking)

        self.assertFalse(SpaceBooking.objects.filter(event=event, vendor=vendor).exists())
        entry = VendorLedgerEntry.objects.get(event=event, vendor=vendor)
        self.assertEqual(entry.entry_type, VendorLedgerEntry.EntryType.CHARGE)
        self.assertEqual(entry.amount, Decimal("-500.00"))
        self.assertEqual(entry.note, "Space removal: 10x10 Booth x 2")

    def test_update_space_booking_quantity_reduces_and_creates_negative_charge(self):
        user = User.objects.create_user(email="owner6@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor = Vendor.objects.create(event=event, name="Vendor One")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=5,
        )
        booking = SpaceBooking.objects.create(
            event=event,
            space_type=space_type,
            vendor=vendor,
            quantity=4,
            unit_price_snapshot=Decimal("250.00"),
            fee_percent_snapshot=Decimal("5.00"),
        )

        updated = update_space_booking_quantity(booking=booking, new_quantity=2)

        self.assertEqual(updated.quantity, 2)
        entry = VendorLedgerEntry.objects.get(event=event, vendor=vendor)
        self.assertEqual(entry.amount, Decimal("-500.00"))
        self.assertEqual(entry.note, "Space removal: 10x10 Booth x 2")

    def test_update_space_booking_quantity_increases_and_creates_charge(self):
        user = User.objects.create_user(email="owner7@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        now = timezone.now()

        event = Event.objects.create(
            account=account,
            name="Expo",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        vendor = Vendor.objects.create(event=event, name="Vendor One")
        space_type = SpaceType.objects.create(
            event=event,
            name="10x10 Booth",
            price=Decimal("250.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=5,
        )
        booking = SpaceBooking.objects.create(
            event=event,
            space_type=space_type,
            vendor=vendor,
            quantity=1,
            unit_price_snapshot=Decimal("250.00"),
            fee_percent_snapshot=Decimal("5.00"),
        )

        updated = update_space_booking_quantity(booking=booking, new_quantity=3)

        self.assertEqual(updated.quantity, 3)
        entry = VendorLedgerEntry.objects.get(event=event, vendor=vendor)
        self.assertEqual(entry.amount, Decimal("500.00"))
        self.assertEqual(entry.note, "Space assignment: 10x10 Booth x 2")


class SpaceTypeAttributesFormTests(TestCase):
    def test_space_type_create_persists_attributes_as_list(self):
        user = User.objects.create_user(email="owner2@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")
        AccountMembership.objects.filter(account=account, user=user).update(role=AccountMembership.Role.MANAGER)

        now = timezone.now()
        event = Event.objects.create(
            account=account,
            name="Attribute Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )

        self.client.force_login(user)
        response = self.client.post(
            reverse("space-type-create", kwargs={"event_id": event.id}),
            {
                "name": "Premium Booth",
                "attributes": '["Electric","Corner"]',
                "price": "250.00",
                "fee_percent": "5.00",
                "total_quantity": "10",
            },
        )

        self.assertEqual(response.status_code, 302)
        space_type = SpaceType.objects.get(event=event, name="Premium Booth")
        self.assertEqual(space_type.attributes, ["Electric", "Corner"])


class SpaceTypeEditDeleteTests(TestCase):
    """Tests for space type update and delete views, including the re-assign guard."""

    def setUp(self):
        self.user = User.objects.create_user(email="mgr@example.com", password="pass12345")
        self.account = provision_account_for_user(self.user, "Test Org")
        AccountMembership.objects.filter(account=self.account, user=self.user).update(
            role=AccountMembership.Role.MANAGER
        )
        now = timezone.now()
        self.event = Event.objects.create(
            account=self.account,
            name="Space Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        self.st = SpaceType.objects.create(
            event=self.event, name="Booth A", price=Decimal("100.00"),
            fee_percent=Decimal("5.00"), total_quantity=10,
        )
        self.st2 = SpaceType.objects.create(
            event=self.event, name="Booth B", price=Decimal("200.00"),
            fee_percent=Decimal("5.00"), total_quantity=10,
        )
        self.vendor = Vendor.objects.create(event=self.event, name="Alpha Vendor")

    def test_edit_space_type_updates_name(self):
        self.client.force_login(self.user)
        url = reverse("space-type-update", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url, {
            "name": "Updated Booth A",
            "attributes": "[]",
            "price": "150.00",
            "fee_percent": "5.00",
            "total_quantity": "10",
        })
        self.assertEqual(response.status_code, 302)
        self.st.refresh_from_db()
        self.assertEqual(self.st.name, "Updated Booth A")
        self.assertEqual(self.st.price, Decimal("150.00"))

    def test_delete_space_type_with_no_bookings(self):
        self.client.force_login(self.user)
        url = reverse("space-type-delete", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpaceType.objects.filter(id=self.st.id).exists())

    def test_delete_blocked_without_replacement_when_bookings_exist(self):
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st, vendor=self.vendor,
            quantity=2, unit_price_snapshot=Decimal("100.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        self.client.force_login(self.user)
        url = reverse("space-type-delete", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SpaceType.objects.filter(id=self.st.id).exists())
        self.assertContains(response, "must choose a replacement")

    def test_delete_with_bookings_reassigns_and_deletes(self):
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st, vendor=self.vendor,
            quantity=2, unit_price_snapshot=Decimal("100.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        self.client.force_login(self.user)
        url = reverse("space-type-delete", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url, {"replacement_space_type": self.st2.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpaceType.objects.filter(id=self.st.id).exists())
        booking = SpaceBooking.objects.get(vendor=self.vendor)
        self.assertEqual(booking.space_type, self.st2)

    def test_delete_blocked_when_vendor_already_booked_replacement(self):
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st, vendor=self.vendor,
            quantity=1, unit_price_snapshot=Decimal("100.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        # Vendor also has a booking for the replacement type
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st2, vendor=self.vendor,
            quantity=1, unit_price_snapshot=Decimal("200.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        self.client.force_login(self.user)
        url = reverse("space-type-delete", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url, {"replacement_space_type": self.st2.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SpaceType.objects.filter(id=self.st.id).exists())
        self.assertContains(response, "already have a booking")

    def test_delete_blocked_when_replacement_lacks_capacity(self):
        # Use up all of st2's capacity
        vendor2 = Vendor.objects.create(event=self.event, name="Beta Vendor")
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st2, vendor=vendor2,
            quantity=10, unit_price_snapshot=Decimal("200.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        SpaceBooking.objects.create(
            event=self.event, space_type=self.st, vendor=self.vendor,
            quantity=3, unit_price_snapshot=Decimal("100.00"), fee_percent_snapshot=Decimal("5.00"),
        )
        self.client.force_login(self.user)
        url = reverse("space-type-delete", kwargs={"event_id": self.event.id, "space_type_id": self.st.id})
        response = self.client.post(url, {"replacement_space_type": self.st2.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SpaceType.objects.filter(id=self.st.id).exists())
        self.assertContains(response, "available")


class SpaceBookingDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="mgr-delete@example.com", password="pass12345")
        self.account = provision_account_for_user(self.user, "Delete Org")
        AccountMembership.objects.filter(account=self.account, user=self.user).update(
            role=AccountMembership.Role.MANAGER
        )
        now = timezone.now()
        self.event = Event.objects.create(
            account=self.account,
            name="Booking Delete Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        self.vendor = Vendor.objects.create(event=self.event, name="Delete Vendor")
        self.space_type = SpaceType.objects.create(
            event=self.event,
            name="Premium Booth",
            price=Decimal("300.00"),
            fee_percent=Decimal("5.00"),
            total_quantity=4,
        )
        self.booking = SpaceBooking.objects.create(
            event=self.event,
            space_type=self.space_type,
            vendor=self.vendor,
            quantity=2,
            unit_price_snapshot=Decimal("300.00"),
            fee_percent_snapshot=Decimal("5.00"),
        )

    def test_manager_can_unassign_booking_and_create_reversal_entry(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("space-booking-delete", kwargs={"event_id": self.event.id, "booking_id": self.booking.id})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SpaceBooking.objects.filter(id=self.booking.id).exists())
        entry = VendorLedgerEntry.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(entry.amount, Decimal("-600.00"))
        self.assertEqual(entry.note, "Space removal: Premium Booth x 2")

    def test_manager_can_reduce_booking_quantity_and_create_credit_entry(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("space-booking-update", kwargs={"event_id": self.event.id, "booking_id": self.booking.id}),
            {"quantity": 1},
        )

        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.quantity, 1)
        entry = VendorLedgerEntry.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(entry.amount, Decimal("-300.00"))
        self.assertEqual(entry.note, "Space removal: Premium Booth x 1")