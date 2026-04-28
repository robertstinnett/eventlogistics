from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auditlog.services import log_account_action
from apps.accounts.forms import AccountInvitationForm, MembershipRoleForm
from apps.accounts.models import AccountInvitation, AccountMembership
from apps.accounts.services import can_manage_account, get_primary_account_for_user


def _manageable_account_or_redirect(request):
    account = get_primary_account_for_user(request.user)
    if not account or not can_manage_account(request.user, account):
        messages.error(request, "No manageable account found.")
        return None
    return account


@login_required
def team_overview_view(request):
    account = _manageable_account_or_redirect(request)
    if not account:
        return redirect("home")

    memberships = account.memberships.select_related("user").order_by("created_at", "id")
    invitations = account.invitations.filter(accepted_at__isnull=True).order_by("created_at", "id")

    return render(
        request,
        "accounts/team_overview.html",
        {
            "account": account,
            "memberships": memberships,
            "invitations": invitations,
            "is_owner": account.owner_id == request.user.id,
        },
    )


@login_required
def invitation_create_view(request):
    account = _manageable_account_or_redirect(request)
    if not account:
        return redirect("home")

    if request.method == "POST":
        form = AccountInvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.account = account
            invitation.save()
            log_account_action(
                account=account,
                actor=request.user,
                action="team.invitation.created",
                target=invitation,
                message=f"Invitation sent to {invitation.email} as {invitation.role}.",
                metadata={"email": invitation.email, "role": invitation.role},
            )
            messages.success(
                request,
                f"Invitation created. Acceptance URL: /team/invitations/accept/{invitation.token}/",
            )
            return redirect("team-overview")
    else:
        form = AccountInvitationForm()

    return render(request, "accounts/invitation_form.html", {"form": form, "account": account})


@login_required
def invitation_accept_view(request, token):
    invitation = get_object_or_404(AccountInvitation, token=token)

    if invitation.accepted_at:
        messages.info(request, "Invitation has already been accepted.")
        return redirect("team-overview")

    if request.user.email.lower() != invitation.email.lower():
        raise PermissionDenied("This invitation is for a different email address.")

    with transaction.atomic():
        membership, created = AccountMembership.objects.get_or_create(
            account=invitation.account,
            user=request.user,
            defaults={"role": invitation.role},
        )
        if not created and membership.role != invitation.role:
            membership.role = invitation.role
            membership.save(update_fields=["role"])

        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])

        log_account_action(
            account=invitation.account,
            actor=request.user,
            action="team.invitation.accepted",
            target=membership,
            message=f"{request.user.email} joined as {membership.role}.",
            metadata={"invitation_id": invitation.id, "role": membership.role},
        )

    messages.success(request, f"You joined {invitation.account.name}.")
    return redirect("team-overview")


@login_required
def membership_role_update_view(request, membership_id):
    membership = get_object_or_404(AccountMembership.objects.select_related("account", "user"), id=membership_id)
    account = membership.account

    if account.owner_id != request.user.id:
        raise PermissionDenied("Only account owners can change member roles.")

    if membership.user_id == account.owner_id:
        raise PermissionDenied("Owner role cannot be changed here.")

    if request.method == "POST":
        form = MembershipRoleForm(request.POST)
        if form.is_valid():
            previous_role = membership.role
            membership.role = form.cleaned_data["role"]
            membership.save(update_fields=["role"])
            log_account_action(
                account=account,
                actor=request.user,
                action="team.membership.role_changed",
                target=membership,
                message=f"Role changed for {membership.user.email}: {previous_role} -> {membership.role}.",
                metadata={"from": previous_role, "to": membership.role},
            )
            messages.success(request, "Member role updated.")
            return redirect("team-overview")
    else:
        form = MembershipRoleForm(initial={"role": membership.role})

    return render(
        request,
        "accounts/membership_role_form.html",
        {"form": form, "membership": membership, "account": account},
    )
