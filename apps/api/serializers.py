from rest_framework import serializers

from apps.events.models import Event
from apps.participants.models import Exhibitor, Performer, Vendor
from apps.spaces.models import SpaceBooking, SpaceType


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "account", "name", "description", "starts_at", "ends_at", "status"]
        read_only_fields = ["account"]


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "event", "name", "email", "phone", "address", "tax_id", "vendor_type", "website"]


class PerformerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Performer
        fields = ["id", "event", "name", "email", "phone", "genre"]


class ExhibitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exhibitor
        fields = ["id", "event", "name", "email", "phone", "category"]


class SpaceTypeSerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = SpaceType
        fields = [
            "id",
            "event",
            "name",
            "attributes",
            "price",
            "fee_percent",
            "total_quantity",
            "available_quantity",
        ]


class SpaceBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpaceBooking
        fields = [
            "id",
            "event",
            "space_type",
            "vendor",
            "quantity",
            "unit_price_snapshot",
            "fee_percent_snapshot",
            "created_at",
        ]
        read_only_fields = ["unit_price_snapshot", "fee_percent_snapshot", "created_at"]


class SpaceBookingCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    space_type_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)