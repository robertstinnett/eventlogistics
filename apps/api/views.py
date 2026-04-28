from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.services import can_manage_account, get_primary_account_for_user
from apps.auditlog.services import log_account_action
from apps.events.models import Event
from apps.participants.models import Exhibitor, Performer, Vendor
from apps.plans.services import can_create_active_event
from apps.spaces.models import SpaceType
from apps.spaces.services import book_space

from .serializers import (
    EventSerializer,
    ExhibitorSerializer,
    PerformerSerializer,
    SpaceBookingCreateSerializer,
    SpaceTypeSerializer,
    VendorSerializer,
)


class ManagedAccountScopeMixin:
    permission_classes = [permissions.IsAuthenticated]

    def _managed_events(self):
        return Event.objects.filter(
            Q(account__memberships__user=self.request.user) | Q(account__owner=self.request.user)
        ).distinct()


class EventViewSet(ManagedAccountScopeMixin, viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        return self._managed_events().distinct()

    def perform_create(self, serializer):
        account = get_primary_account_for_user(self.request.user)
        if not account:
            raise ValidationError({"detail": "No account found for user."})

        plan = account.subscription_state.plan
        if not can_create_active_event(account, plan):
            raise ValidationError({"detail": "Plan limit reached for active/upcoming events."})

        event = serializer.save(account=account)
        log_account_action(
            account=account,
            actor=self.request.user,
            action="event.created",
            event=event,
            target=event,
            message=f"Event created via API: {event.name}.",
            metadata={"source": "api"},
        )


class VendorViewSet(ManagedAccountScopeMixin, viewsets.ModelViewSet):
    serializer_class = VendorSerializer

    def get_queryset(self):
        return Vendor.objects.filter(event__in=self._managed_events().distinct())


class PerformerViewSet(ManagedAccountScopeMixin, viewsets.ModelViewSet):
    serializer_class = PerformerSerializer

    def get_queryset(self):
        return Performer.objects.filter(event__in=self._managed_events().distinct())


class ExhibitorViewSet(ManagedAccountScopeMixin, viewsets.ModelViewSet):
    serializer_class = ExhibitorSerializer

    def get_queryset(self):
        return Exhibitor.objects.filter(event__in=self._managed_events().distinct())


class SpaceTypeViewSet(ManagedAccountScopeMixin, viewsets.ModelViewSet):
    serializer_class = SpaceTypeSerializer

    def get_queryset(self):
        return SpaceType.objects.filter(event__in=self._managed_events().distinct())


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_space_booking(request):
    serializer = SpaceBookingCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    event = get_object_or_404(Event, id=serializer.validated_data["event_id"])
    if not can_manage_account(request.user, event.account):
        return Response({"detail": "Forbidden"}, status=403)

    vendor = get_object_or_404(Vendor, id=serializer.validated_data["vendor_id"], event=event)
    booking = book_space(
        event=event,
        space_type_id=serializer.validated_data["space_type_id"],
        vendor=vendor,
        quantity=serializer.validated_data["quantity"],
    )
    log_account_action(
        account=event.account,
        actor=request.user,
        action="space.booking.created",
        event=event,
        target=booking,
        message=f"Space booked via API for vendor {vendor.id} (quantity {booking.quantity}).",
        metadata={"source": "api"},
    )
    return Response(
        {
            "id": booking.id,
            "event": booking.event_id,
            "space_type": booking.space_type_id,
            "vendor": booking.vendor_id,
            "quantity": booking.quantity,
        },
        status=201,
    )


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def integration_token_view(request):
    account = get_primary_account_for_user(request.user)
    action = "api.token.issued"
    if request.method == "POST":
        Token.objects.filter(user=request.user).delete()
        action = "api.token.rotated"

    token, created = Token.objects.get_or_create(user=request.user)
    if request.method == "GET" and not created:
        action = "api.token.fetched"

    log_account_action(
        account=account,
        actor=request.user,
        action=action,
        message=f"Integration token action via API: {action}.",
        metadata={"method": request.method},
    )
    return Response(
        {
            "token": token.key,
            "token_type": "Token",
            "user": request.user.email,
        }
    )