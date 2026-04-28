from django.urls import path

from apps.accounts.views import (
    invitation_accept_view,
    invitation_create_view,
    membership_role_update_view,
    team_overview_view,
)

urlpatterns = [
    path("", team_overview_view, name="team-overview"),
    path("invitations/new/", invitation_create_view, name="team-invitation-create"),
    path("invitations/accept/<uuid:token>/", invitation_accept_view, name="team-invitation-accept"),
    path("members/<int:membership_id>/role/", membership_role_update_view, name="team-membership-role-update"),
]
