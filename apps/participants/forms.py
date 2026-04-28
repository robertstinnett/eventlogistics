from django import forms

from apps.participants.models import Exhibitor, Performer, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "email", "phone", "address", "tax_id", "vendor_type", "website"]


class PerformerForm(forms.ModelForm):
    class Meta:
        model = Performer
        fields = ["name", "email", "phone", "genre"]


class ExhibitorForm(forms.ModelForm):
    class Meta:
        model = Exhibitor
        fields = ["name", "email", "phone", "category"]