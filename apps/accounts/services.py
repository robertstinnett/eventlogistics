from django.db import transaction

from apps.accounts.models import Account, AccountMembership
from apps.plans.models import AccountSubscriptionState
from apps.plans.services import ensure_default_plans


@transaction.atomic
def provision_account_for_user(user, account_name):
    account = Account.objects.create(name=account_name, owner=user)
    AccountMembership.objects.create(
        account=account,
        user=user,
        role=AccountMembership.Role.OWNER,
    )

    plans = ensure_default_plans()
    free_plan = next(plan for plan in plans if plan.code == "free")
    AccountSubscriptionState.objects.create(account=account, plan=free_plan)
    return account


def get_primary_account_for_user(user):
    if hasattr(user, "owned_accounts"):
        owned = user.owned_accounts.order_by("id").first()
        if owned:
            return owned

    membership = user.account_memberships.select_related("account").order_by("id").first()
    return membership.account if membership else None


def can_manage_account(user, account):
    if account.owner_id == user.id:
        return True

    return AccountMembership.objects.filter(
        account=account,
        user=user,
        role__in=[AccountMembership.Role.OWNER, AccountMembership.Role.MANAGER],
    ).exists()