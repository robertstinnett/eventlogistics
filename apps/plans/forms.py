from django import forms

from apps.plans.models import AccountSubscriptionState, Plan
from apps.plans.services import ensure_default_plans


class SubscriptionChangeForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), empty_label=None)
    billing_cycle = forms.ChoiceField(choices=AccountSubscriptionState.BillingCycle.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ensure_default_plans()
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True).order_by("monthly_price", "id")
