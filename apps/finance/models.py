from django.db import models
from apps.events.models import Event
from apps.participants.models import Vendor


class VendorLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CHARGE = "charge", "Charge"
        PAYMENT = "payment", "Payment"
        ADJUSTMENT = "adjustment", "Adjustment"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ledger_entries")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="ledger_entries")
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
