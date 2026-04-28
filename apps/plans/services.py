from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.auditlog.services import log_account_action
from apps.plans.models import AccountSubscriptionState, Plan
from apps.events.models import Event


def can_create_active_event(account, plan):
    active_count = active_upcoming_event_count(account)
    return active_count < plan.max_active_events


def active_upcoming_event_count(account):
    return Event.objects.filter(
        account=account,
        status__in=[Event.Status.DRAFT, Event.Status.PUBLISHED],
        ends_at__gte=timezone.now(),
    ).count()


def ensure_default_plans():
    defaults = [
        {
            "code": "free",
            "name": "Free Tier",
            "max_active_events": 1,
            "monthly_price": 0,
            "yearly_price": 0,
        },
        {
            "code": "pro",
            "name": "Pro Tier",
            "max_active_events": 5,
            "monthly_price": 49,
            "yearly_price": 490,
        },
        {
            "code": "enterprise",
            "name": "Enterprise Tier",
            "max_active_events": 25,
            "monthly_price": 199,
            "yearly_price": 1990,
        },
    ]

    plans = []
    for item in defaults:
        plan, _ = Plan.objects.get_or_create(
            code=item["code"],
            defaults={
                "name": item["name"],
                "max_active_events": item["max_active_events"],
                "monthly_price": item["monthly_price"],
                "yearly_price": item["yearly_price"],
                "is_active": True,
            },
        )
        plans.append(plan)
    return plans


@transaction.atomic
def change_subscription_plan(account, target_plan, billing_cycle, actor=None):
    active_count = active_upcoming_event_count(account)
    if target_plan.max_active_events < active_count:
        return {
            "ok": False,
            "error": (
                f"Cannot move to {target_plan.name}: {active_count} active/upcoming events exceed "
                f"its limit of {target_plan.max_active_events}."
            ),
        }

    subscription = account.subscription_state
    previous_plan_code = subscription.plan.code
    previous_cycle = subscription.billing_cycle
    subscription.plan = target_plan
    subscription.billing_cycle = billing_cycle
    subscription.current_period_end = timezone.now() + timedelta(
        days=30 if billing_cycle == AccountSubscriptionState.BillingCycle.MONTHLY else 365
    )
    subscription.save(update_fields=["plan", "billing_cycle", "current_period_end"])
    log_account_action(
        account=account,
        actor=actor,
        action="billing.plan.changed",
        target=subscription,
        message=f"Plan changed from {previous_plan_code} ({previous_cycle}) to {target_plan.code} ({billing_cycle}).",
        metadata={
            "from_plan": previous_plan_code,
            "to_plan": target_plan.code,
            "from_cycle": previous_cycle,
            "to_cycle": billing_cycle,
        },
    )
    return {"ok": True, "subscription": subscription}
