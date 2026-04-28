from django.db import models
from django.utils import timezone
from apps.accounts.models import Account


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="events")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]

    @property
    def is_active_or_upcoming(self):
        return self.status in {self.Status.DRAFT, self.Status.PUBLISHED} and self.ends_at >= timezone.now()


class EventDateRange(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="date_ranges")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
