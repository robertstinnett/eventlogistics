from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services import provision_account_for_user
from apps.events.models import Event
from apps.users.models import User


class FreeTierEventLimitTests(TestCase):
    def test_free_tier_blocks_second_active_or_upcoming_event(self):
        user = User.objects.create_user(email="owner@example.com", password="pass12345")
        account = provision_account_for_user(user, "Owner Org")

        now = timezone.now()
        Event.objects.create(
            account=account,
            name="Existing Event",
            description="",
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=2),
            status=Event.Status.DRAFT,
        )

        self.client.force_login(user)
        response = self.client.post(
            reverse("event-create"),
            {
                "name": "Second Event",
                "description": "Should be blocked on free tier",
                "starts_at": (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "ends_at": (now + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": Event.Status.DRAFT,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your tier allows only one active/upcoming event at a time.")
        self.assertEqual(Event.objects.filter(account=account).count(), 1)