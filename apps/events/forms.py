from django import forms

from apps.events.models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "description", "starts_at", "ends_at", "status"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }