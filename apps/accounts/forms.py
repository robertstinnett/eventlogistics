from django import forms

from apps.accounts.models import AccountInvitation, AccountMembership


class AccountInvitationForm(forms.ModelForm):
    class Meta:
        model = AccountInvitation
        fields = ["email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (AccountMembership.Role.MANAGER, "Manager"),
            (AccountMembership.Role.VIEWER, "Viewer"),
        ]


class MembershipRoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=[
            (AccountMembership.Role.MANAGER, "Manager"),
            (AccountMembership.Role.VIEWER, "Viewer"),
        ]
    )
