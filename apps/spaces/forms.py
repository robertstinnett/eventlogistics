import json

from django import forms

from apps.participants.models import Vendor
from apps.spaces.models import SpaceBooking, SpaceType
from apps.spaces.services import book_space, update_space_booking_quantity


class SpaceTypeForm(forms.ModelForm):
    attributes = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = SpaceType
        fields = ["name", "price", "fee_percent", "total_quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attributes"].initial = json.dumps(self._normalize_attributes(self.instance.attributes))

    def _normalize_attributes(self, value):
        if isinstance(value, list):
            source = value
        elif isinstance(value, dict):
            source = value.get("items", value.keys())
        else:
            source = []
        cleaned = []
        for item in source:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    def clean_attributes(self):
        raw = self.cleaned_data.get("attributes") or "[]"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Attributes must be valid JSON.") from exc

        if not isinstance(payload, list):
            raise forms.ValidationError("Attributes must be a list.")

        cleaned = []
        for item in payload:
            if not isinstance(item, str):
                raise forms.ValidationError("Each attribute must be text.")
            text = item.strip()
            if text:
                cleaned.append(text)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.attributes = self.cleaned_data.get("attributes", [])
        if commit:
            instance.save()
        return instance


class SpaceBookingForm(forms.Form):
    vendor = forms.ModelChoiceField(queryset=Vendor.objects.none())
    space_type = forms.ModelChoiceField(queryset=SpaceType.objects.none())
    quantity = forms.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        event = kwargs.pop("event")
        self.fixed_vendor = kwargs.pop("fixed_vendor", None)
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["vendor"].queryset = Vendor.objects.filter(event=event).order_by("name")
        self.fields["space_type"].queryset = SpaceType.objects.filter(event=event).order_by("name")
        if self.fixed_vendor is not None:
            self.fields["vendor"].queryset = Vendor.objects.filter(id=self.fixed_vendor.id)
            self.fields["vendor"].initial = self.fixed_vendor
            self.fields["vendor"].widget = forms.HiddenInput()

    def clean_vendor(self):
        if self.fixed_vendor is not None:
            return self.fixed_vendor
        return self.cleaned_data["vendor"]

    def save(self):
        try:
            return book_space(
                event=self.event,
                space_type_id=self.cleaned_data["space_type"].id,
                vendor=self.cleaned_data["vendor"],
                quantity=self.cleaned_data["quantity"],
            )
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


class SpaceBookingQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        self.booking = kwargs.pop("booking")
        super().__init__(*args, **kwargs)
        self.fields["quantity"].initial = self.booking.quantity

    def save(self):
        try:
            return update_space_booking_quantity(
                booking=self.booking,
                new_quantity=self.cleaned_data["quantity"],
            )
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc