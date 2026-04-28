import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.services import provision_account_for_user
from apps.auditlog.models import AuditLogEntry
from apps.events.models import Event
from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Vendor
from apps.spaces.models import SpaceBooking, SpaceType
from apps.users.models import User


class SpaceBookingApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.user, "Owner Org")
        now = timezone.now()

        self.event = Event.objects.create(
            account=self.account,
            name="Festival",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )
        self.vendor = Vendor.objects.create(event=self.event, name="Vendor One")
        self.space_type = SpaceType.objects.create(
            event=self.event,
            name="Premium Booth",
            price=Decimal("400.00"),
            fee_percent=Decimal("8.50"),
            total_quantity=5,
        )

    def test_space_booking_api_requires_authentication(self):
        payload = {
            "event_id": self.event.id,
            "space_type_id": self.space_type.id,
            "vendor_id": self.vendor.id,
            "quantity": 1,
        }

        response = self.client.post(
            reverse("api-space-bookings"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(SpaceBooking.objects.count(), 0)

    def test_space_booking_api_creates_booking_for_authenticated_manager(self):
        payload = {
            "event_id": self.event.id,
            "space_type_id": self.space_type.id,
            "vendor_id": self.vendor.id,
            "quantity": 2,
        }
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("api-space-bookings"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SpaceBooking.objects.count(), 1)

        booking = SpaceBooking.objects.get()
        self.assertEqual(booking.quantity, 2)
        self.assertEqual(booking.unit_price_snapshot, self.space_type.price)
        self.assertEqual(booking.fee_percent_snapshot, self.space_type.fee_percent)
        entry = VendorLedgerEntry.objects.get(event=self.event, vendor=self.vendor)
        self.assertEqual(entry.entry_type, VendorLedgerEntry.EntryType.CHARGE)
        self.assertEqual(entry.amount, Decimal("800.00"))
        self.assertEqual(entry.note, "Space assignment: Premium Booth x 2")

    def test_space_booking_api_forbids_authenticated_user_from_other_account(self):
        outsider = User.objects.create_user(email="outsider@example.com", password="pass12345")
        provision_account_for_user(outsider, "Outsider Org")

        payload = {
            "event_id": self.event.id,
            "space_type_id": self.space_type.id,
            "vendor_id": self.vendor.id,
            "quantity": 1,
        }

        self.client.force_login(outsider)
        response = self.client.post(
            reverse("api-space-bookings"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SpaceBooking.objects.count(), 0)


class HealthEndpointTests(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_readyz_returns_database_available(self):
        response = self.client.get(reverse("readyz"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok", "database": "available"})


class EventApiPlanEnforcementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="api-owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.user, "API Owner Org")

    def test_event_api_blocks_creation_when_free_tier_limit_reached(self):
        now = timezone.now()
        Event.objects.create(
            account=self.account,
            name="Existing",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )

        self.client.force_login(self.user)
        payload = {
            "name": "Blocked Event",
            "description": "",
            "starts_at": (now + timedelta(days=3)).isoformat(),
            "ends_at": (now + timedelta(days=4)).isoformat(),
            "status": Event.Status.DRAFT,
        }
        response = self.client.post(
            reverse("api-events-list"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {"detail": "Plan limit reached for active/upcoming events."})

    def test_event_api_creates_event_when_under_limit(self):
        now = timezone.now()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("api-events-list"),
            data=json.dumps(
                {
                    "name": "Launch Event",
                    "description": "",
                    "starts_at": (now + timedelta(days=1)).isoformat(),
                    "ends_at": (now + timedelta(days=2)).isoformat(),
                    "status": Event.Status.DRAFT,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.filter(account=self.account).count(), 1)


class ApiTokenAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="token-owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.user, "Token Org")
        now = timezone.now()
        self.event = Event.objects.create(
            account=self.account,
            name="Token Event",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.PUBLISHED,
        )

    def test_authenticated_user_can_issue_integration_token(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("api-token"))

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["token_type"], "Token")
        self.assertEqual(body["user"], self.user.email)
        self.assertTrue(Token.objects.filter(user=self.user, key=body["token"]).exists())

    def test_post_rotates_integration_token(self):
        original = Token.objects.create(user=self.user)
        self.client.force_login(self.user)

        response = self.client.post(reverse("api-token"))

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertNotEqual(body["token"], original.key)
        self.assertFalse(Token.objects.filter(key=original.key).exists())
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="api.token.rotated").exists()
        )

    def test_token_auth_can_access_event_api(self):
        token = Token.objects.create(user=self.user)

        response = self.client.get(
            reverse("api-events-list"),
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["name"], "Token Event")