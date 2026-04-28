from django.test import TestCase
from django.urls import reverse

from apps.auditlog.models import AuditLogEntry
from apps.accounts.models import AccountInvitation, AccountMembership
from apps.accounts.services import provision_account_for_user
from apps.users.models import User


class TeamManagementTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.account = provision_account_for_user(self.owner, "Owner Org")

    def test_manager_can_create_invitation(self):
        manager = User.objects.create_user(email="manager@example.com", password="pass12345")
        AccountMembership.objects.create(
            account=self.account,
            user=manager,
            role=AccountMembership.Role.MANAGER,
        )

        self.client.force_login(manager)
        response = self.client.post(
            reverse("team-invitation-create"),
            {"email": "invitee@example.com", "role": AccountMembership.Role.VIEWER},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AccountInvitation.objects.filter(account=self.account).count(), 1)
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="team.invitation.created").exists()
        )

    def test_user_can_accept_invitation_for_matching_email(self):
        invitee = User.objects.create_user(email="invitee@example.com", password="pass12345")
        invitation = AccountInvitation.objects.create(
            account=self.account,
            email="invitee@example.com",
            role=AccountMembership.Role.MANAGER,
        )

        self.client.force_login(invitee)
        response = self.client.get(reverse("team-invitation-accept", kwargs={"token": invitation.token}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AccountMembership.objects.filter(
                account=self.account,
                user=invitee,
                role=AccountMembership.Role.MANAGER,
            ).exists()
        )
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="team.invitation.accepted").exists()
        )

    def test_only_owner_can_update_membership_role(self):
        member = User.objects.create_user(email="member@example.com", password="pass12345")
        manager = User.objects.create_user(email="manager@example.com", password="pass12345")

        membership = AccountMembership.objects.create(
            account=self.account,
            user=member,
            role=AccountMembership.Role.VIEWER,
        )
        AccountMembership.objects.create(
            account=self.account,
            user=manager,
            role=AccountMembership.Role.MANAGER,
        )

        self.client.force_login(manager)
        response = self.client.post(
            reverse("team-membership-role-update", kwargs={"membership_id": membership.id}),
            {"role": AccountMembership.Role.MANAGER},
        )
        self.assertEqual(response.status_code, 403)

        membership.refresh_from_db()
        self.assertEqual(membership.role, AccountMembership.Role.VIEWER)

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("team-membership-role-update", kwargs={"membership_id": membership.id}),
            {"role": AccountMembership.Role.MANAGER},
        )
        self.assertEqual(response.status_code, 302)

        membership.refresh_from_db()
        self.assertEqual(membership.role, AccountMembership.Role.MANAGER)
        self.assertTrue(
            AuditLogEntry.objects.filter(account=self.account, action="team.membership.role_changed").exists()
        )
