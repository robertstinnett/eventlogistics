from django.core.exceptions import ValidationError
from django.db import models
from apps.events.models import Event
from apps.participants.models import Vendor


class SpaceType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="space_types")
    name = models.CharField(max_length=120)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("event", "name")

    def __str__(self):
        return self.name

    @property
    def booked_quantity(self):
        return sum(self.bookings.values_list("quantity", flat=True))

    @property
    def available_quantity(self):
        return max(self.total_quantity - self.booked_quantity, 0)


class SpaceBooking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="space_bookings")
    space_type = models.ForeignKey(SpaceType, on_delete=models.CASCADE, related_name="bookings")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="space_bookings")
    quantity = models.PositiveIntegerField(default=1)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    fee_percent_snapshot = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["space_type", "vendor"], name="uniq_space_type_vendor"),
        ]

    def clean(self):
        if self.space_type.event_id != self.event_id:
            raise ValidationError("Space type must belong to the same event.")
        if self.vendor.event_id != self.event_id:
            raise ValidationError("Vendor must belong to the same event.")
