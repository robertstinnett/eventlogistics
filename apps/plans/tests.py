from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccountMembership
from apps.accounts.services import provision_account_for_user
from apps.auditlog.models import AuditLogEntry
from apps.events.models import Event
from apps.plans.models import Plan
from apps.users.models import User


class BillingWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.owner, "Owner Org")
        Plan.objects.get_or_create(
            code="pro",
            defaults={
                "name": "Pro Tier",
                "max_active_events": 5,
                "monthly_price": 49,
                "yearly_price": 490,
                "is_active": True,
            },
        )

    def test_owner_can_upgrade_subscription(self):
        self.client.force_login(self.owner)
        pro_plan = Plan.objects.get(code="pro")

        response = self.client.post(
            reverse("billing-overview"),
            {"plan": pro_plan.id, "billing_cycle": "yearly"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.account.subscription_state.refresh_from_db()
        self.assertEqual(self.account.subscription_state.plan_id, pro_plan.id)
        self.assertEqual(self.account.subscription_state.billing_cycle, "yearly")
        self.assertContains(response, "Subscription updated.")
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="billing.plan.changed").exists()
        )

    def test_manager_cannot_change_subscription(self):
        manager = User.objects.create_user(email="manager@example.com", password="pass12345")
        AccountMembership.objects.create(account=self.account, user=manager, role=AccountMembership.Role.MANAGER)
        pro_plan = Plan.objects.get(code="pro")

        self.client.force_login(manager)
        response = self.client.post(
            reverse("billing-overview"),
            {"plan": pro_plan.id, "billing_cycle": "monthly"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.account.subscription_state.refresh_from_db()
        self.assertEqual(self.account.subscription_state.plan.code, "free")
        self.assertContains(response, "Only account owners can update billing plan.")

    def test_downgrade_blocked_if_active_events_exceed_limit(self):
        pro_plan = Plan.objects.get(code="pro")
        self.account.subscription_state.plan = pro_plan
        self.account.subscription_state.save(update_fields=["plan"])

        now = timezone.now()
        for idx in range(2):
            Event.objects.create(
                account=self.account,
                name=f"Event {idx}",
                starts_at=now + timedelta(days=idx + 1),
                ends_at=now + timedelta(days=idx + 2),
                status=Event.Status.PUBLISHED,
            )

        self.client.force_login(self.owner)
        free_plan = Plan.objects.get(code="free")
        response = self.client.post(
            reverse("billing-overview"),
            {"plan": free_plan.id, "billing_cycle": "monthly"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.account.subscription_state.refresh_from_db()
        self.assertEqual(self.account.subscription_state.plan.code, "pro")
        self.assertContains(response, "Cannot move to Free Tier")
