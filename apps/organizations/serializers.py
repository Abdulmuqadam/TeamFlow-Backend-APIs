from rest_framework import serializers

from .models import Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization

        fields = (
            "id",
            "name",
            "slug",
            "created_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
        )


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Membership

        fields = (
            "id",
            "user",
            "user_email",
            "role",
            "joined_at",
        )

        read_only_fields = (
            "id",
            "joined_at",
        )
