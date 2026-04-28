from django.db import models
from apps.events.models import Event


class BaseParticipant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Vendor(BaseParticipant):
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    vendor_type = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)


class Performer(BaseParticipant):
    genre = models.CharField(max_length=120, blank=True)


class Exhibitor(BaseParticipant):
    category = models.CharField(max_length=120, blank=True)
