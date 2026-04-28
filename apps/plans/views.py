from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.services import get_primary_account_for_user
from apps.plans.forms import SubscriptionChangeForm
from apps.plans.services import (
    active_upcoming_event_count,
    change_subscription_plan,
    ensure_default_plans,
)


@login_required
def subscription_overview_view(request):
    ensure_default_plans()

    account = get_primary_account_for_user(request.user)
    if not account:
        messages.error(request, "No account found for your user.")
        return redirect("home")

    if request.method == "POST":
        if account.owner_id != request.user.id:
            messages.error(request, "Only account owners can update billing plan.")
            return redirect("billing-overview")

        form = SubscriptionChangeForm(request.POST)
        if form.is_valid():
            result = change_subscription_plan(
                account=account,
                target_plan=form.cleaned_data["plan"],
                billing_cycle=form.cleaned_data["billing_cycle"],
                actor=request.user,
            )
            if result["ok"]:
                messages.success(request, "Subscription updated.")
                return redirect("billing-overview")

            form.add_error(None, result["error"])
    else:
        form = SubscriptionChangeForm(
            initial={
                "plan": account.subscription_state.plan,
                "billing_cycle": account.subscription_state.billing_cycle,
            }
        )

    return render(
        request,
        "plans/subscription_overview.html",
        {
            "account": account,
            "subscription": account.subscription_state,
            "active_event_count": active_upcoming_event_count(account),
            "form": form,
            "can_change": account.owner_id == request.user.id,
        },
    )
