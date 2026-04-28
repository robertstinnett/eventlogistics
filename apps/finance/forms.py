from django import forms

from apps.finance.models import VendorLedgerEntry
from apps.participants.models import Vendor


class VendorLedgerEntryForm(forms.ModelForm):
    class Meta:
        model = VendorLedgerEntry
        fields = ["vendor", "entry_type", "amount", "note"]

    def __init__(self, *args, **kwargs):
        event = kwargs.pop("event")
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.filter(event=event).order_by("name")
