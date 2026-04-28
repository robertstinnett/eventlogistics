from django.db import models
from apps.accounts.models import Account


class Plan(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    max_active_events = models.PositiveIntegerField(default=1)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class AccountSubscriptionState(models.Model):
    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="subscription_state")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account.name} -> {self.plan.code}"
