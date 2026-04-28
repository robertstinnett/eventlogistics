from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import AccountMembership
from apps.accounts.services import provision_account_for_user
from apps.auditlog.models import AuditLogEntry
from apps.users.models import User


class AuditLogViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.owner, "Owner Org")
        self.manager = User.objects.create_user(email="manager@example.com", password="pass12345")
        AccountMembership.objects.create(
            account=self.account,
            user=self.manager,
            role=AccountMembership.Role.MANAGER,
        )

    def test_manager_can_view_account_audit_log(self):
        AuditLogEntry.objects.create(
            account=self.account,
            actor=self.owner,
            action="test.action",
            message="Audit visibility check",
        )

        self.client.force_login(self.manager)
        response = self.client.get(reverse("account-audit-log"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test.action")

    def test_outsider_cannot_view_other_account_audit_log(self):
        AuditLogEntry.objects.create(
            account=self.account,
            actor=self.owner,
            action="sensitive.action",
            message="Owner account only",
        )
        outsider = User.objects.create_user(email="outsider@example.com", password="pass12345")
        provision_account_for_user(outsider, "Outsider Org")

        self.client.force_login(outsider)
        response = self.client.get(reverse("account-audit-log"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "sensitive.action")
